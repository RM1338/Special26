"""Typed queries over special26.db (06)."""
import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from special26.claims.models import Claim
from special26.errors import BudgetExhausted


def now() -> datetime:
    return datetime.now(UTC)


def iso(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


class Repo:
    def __init__(self, conn: sqlite3.Connection, replay: sqlite3.Connection | None = None,
                 record: sqlite3.Connection | None = None):
        self.db, self.replay, self.record = conn, replay, record

    # ---- serp_cache -------------------------------------------------------------
    def cache_get(self, key: str, ttl_hours: int) -> dict | None:
        cutoff = iso(now() - timedelta(hours=ttl_hours))
        row = self.db.execute("SELECT response_json FROM serp_cache WHERE cache_key = ? AND fetched_at >= ?",
                              (key, cutoff)).fetchone()
        return json.loads(row[0]) if row else None

    def cache_put(self, key: str, engine: str, params: dict, data: dict) -> None:
        _put(self.db, key, engine, params, data)

    def demo_get(self, key: str) -> dict | None:
        if self.replay is None:
            return None
        row = self.replay.execute("SELECT response_json FROM serp_cache WHERE cache_key = ?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def record_put(self, key: str, engine: str, params: dict, data: dict) -> None:
        if self.record is not None:
            _put(self.record, key, engine, params, data)

    # ---- credit_ledger (D-06) ---------------------------------------------------
    def budget_reserve(self, check_id: str | None, engine: str, per_check: int, daily: int) -> int:
        """Reserve one uncached credit atomically; returns ledger row id. FR-23."""
        day, ts = iso(now())[:10], iso(now())
        self.db.execute("BEGIN IMMEDIATE")
        try:
            if check_id is not None:
                used = self.db.execute(
                    "SELECT COUNT(*) FROM credit_ledger WHERE check_id = ? AND cached = 0 AND status != 'refunded'",
                    (check_id,)).fetchone()[0]
                if used >= per_check:
                    raise BudgetExhausted("per-check budget reached", {"budget": per_check})
            today = self.db.execute(
                "SELECT COUNT(*) FROM credit_ledger WHERE day_utc = ? AND cached = 0 AND status != 'refunded'",
                (day,)).fetchone()[0]
            if today >= daily:
                raise BudgetExhausted("daily credit cap reached", {"cap": daily})
            cur = self.db.execute(
                "INSERT INTO credit_ledger (check_id, engine, cached, status, day_utc, created_at)"
                " VALUES (?, ?, 0, 'reserved', ?, ?)", (check_id, engine, day, ts))
            self.db.execute("COMMIT")
            return cur.lastrowid
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def ledger_settle(self, row_id: int, cache_key: str | None, spent: bool) -> None:
        self.db.execute("UPDATE credit_ledger SET status = ?, cache_key = ? WHERE id = ?",
                        ("spent" if spent else "refunded", cache_key, row_id))

    def ledger_cache_hit(self, check_id: str | None, engine: str, cache_key: str) -> None:
        ts = iso(now())
        self.db.execute("INSERT INTO credit_ledger (check_id, engine, cache_key, cached, status, day_utc, created_at)"
                        " VALUES (?, ?, ?, 1, 'spent', ?, ?)", (check_id, engine, cache_key, ts[:10], ts))

    def credits_today(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM credit_ledger WHERE day_utc = ? AND cached = 0"
                               " AND status != 'refunded'", (iso(now())[:10],)).fetchone()[0]


    # ---- checks -----------------------------------------------------------------
    def create_check(self, check_id: str, mode: str, ip_hash: str | None, raw_text: str, redacted_text: str,
                     auto_run: bool, warnings: list[str], created: datetime | None = None) -> None:
        import hashlib
        created = created or now()
        self.db.execute(
            "INSERT INTO checks (id, created_at, updated_at, status, mode, client_ip_hash, raw_text, redacted_text,"
            " text_sha256, auto_run, warnings_json, purge_after) VALUES (?, ?, ?, 'received', ?, ?, ?, ?, ?, ?, ?, ?)",
            (check_id, iso(created), iso(created), mode, ip_hash, raw_text, redacted_text,
             hashlib.sha256(redacted_text.encode()).hexdigest(), int(auto_run), json.dumps(warnings),
             iso(created + timedelta(days=30))))

    def update_check(self, check_id: str, **fields) -> None:
        if "warnings" in fields:
            fields["warnings_json"] = json.dumps(fields.pop("warnings"))
        cols = ", ".join(f"{k} = ?" for k in fields)
        self.db.execute(f"UPDATE checks SET {cols}, updated_at = ? WHERE id = ?",
                        (*fields.values(), iso(now()), check_id))

    def get_check(self, check_id: str) -> dict | None:
        row = self.db.execute("SELECT * FROM checks WHERE id = ?", (check_id,)).fetchone()
        if row is None:
            return None
        d = dict(row)
        d["warnings"] = json.loads(d.pop("warnings_json"))
        return d

    def count_checks_from_ip(self, ip_hash: str, since: datetime) -> tuple[int, str | None]:
        """(count in window, oldest created_at in window) for rate limiting."""
        row = self.db.execute("SELECT COUNT(*), MIN(created_at) FROM checks WHERE client_ip_hash = ? AND created_at >= ?",
                              (ip_hash, iso(since))).fetchone()
        return row[0], row[1]

    def add_artifact(self, check_id: str, role: str, mime: str, nbytes: int, sha256: str, path: str | None,
                     phash: str | None = None, width: int | None = None, height: int | None = None,
                     derived_from: int | None = None) -> int:
        cur = self.db.execute(
            "INSERT INTO artifacts (check_id, role, mime, bytes, sha256, storage_path, phash, width, height,"
            " derived_from, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (check_id, role, mime, nbytes, sha256, path, phash, width, height, derived_from, iso(now())))
        return cur.lastrowid

    def artifacts(self, check_id: str) -> list[dict]:
        return [dict(r) for r in self.db.execute("SELECT * FROM artifacts WHERE check_id = ? ORDER BY id", (check_id,))]

    # ---- claims -----------------------------------------------------------------
    def save_claims(self, check_id: str, claims: list[Claim], confirmed: bool = False) -> None:
        self.db.execute("BEGIN")
        self.db.execute("DELETE FROM claims WHERE check_id = ?", (check_id,))
        for c in claims:
            self.db.execute(
                "INSERT INTO claims (id, check_id, type, value_json, raw, span_start, span_end, source, confidence,"
                " confirmed) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (c.id, check_id, c.type.value, json.dumps(c.value, ensure_ascii=False), c.raw,
                 c.span[0] if c.span else None, c.span[1] if c.span else None, c.source, c.confidence, int(confirmed)))
        self.db.execute("COMMIT")

    def claims(self, check_id: str) -> list[Claim]:
        rows = self.db.execute("SELECT * FROM claims WHERE check_id = ? AND deleted = 0 ORDER BY rowid", (check_id,))
        return [Claim(id=r["id"], type=r["type"], value=json.loads(r["value_json"]), raw=r["raw"],
                      span=(r["span_start"], r["span_end"]) if r["span_start"] is not None else None,
                      source=r["source"], confidence=r["confidence"]) for r in rows]

    # ---- probe runs and findings -----------------------------------------------
    def save_probe_result(self, check_id: str, res) -> None:
        """Insert the probe run and its findings; sets finding.id (reasons cite it)."""
        self.db.execute("BEGIN")
        cur = self.db.execute(
            "INSERT OR REPLACE INTO probe_runs (check_id, probe_id, status, credits_used, cache_hits, duration_ms,"
            " outputs_json, finished_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (check_id, res.probe_id, res.status, res.credits_used, res.cache_hits, res.duration_ms,
             json.dumps(res.outputs, ensure_ascii=False), iso(now())))
        for f in res.findings:
            fc = self.db.execute(
                "INSERT INTO findings (probe_run_id, check_id, code, family, weight, decisive_flag, message,"
                " claim_ids_json, receipt_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (cur.lastrowid, check_id, f.code, f.family, f.weight, f.decisive_flag, f.message,
                 json.dumps(f.claim_ids), f.receipt.model_dump_json()))
            f.id = fc.lastrowid
        self.db.execute("COMMIT")

    def set_effective(self, pairs: list[tuple[int, float]]) -> None:
        self.db.executemany("UPDATE findings SET effective_weight = ? WHERE id = ?", [(w, i) for i, w in pairs])

    def probe_runs(self, check_id: str) -> list[dict]:
        rows = self.db.execute("SELECT * FROM probe_runs WHERE check_id = ? ORDER BY id", (check_id,))
        return [{**dict(r), "outputs": json.loads(r["outputs_json"])} for r in rows]

    def findings(self, check_id: str) -> list[dict]:
        out = []
        for r in self.db.execute("SELECT f.*, p.probe_id FROM findings f JOIN probe_runs p ON p.id = f.probe_run_id"
                                 " WHERE f.check_id = ? ORDER BY f.id", (check_id,)):
            d = dict(r)
            d["claim_ids"], d["receipt"] = json.loads(d.pop("claim_ids_json")), json.loads(d.pop("receipt_json"))
            out.append(d)
        return out

    # ---- verdicts ---------------------------------------------------------------
    def save_verdict(self, check_id: str, v, official_contacts: list[dict]) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO verdicts (check_id, tier, red_kind, score, family_scores_json, decisive_json,"
            " coverage, reasons_json, official_contacts_json, ruleset_version, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (check_id, v.tier, v.red_kind, v.score, json.dumps(v.family_scores), json.dumps(v.decisive), v.coverage,
             json.dumps([r.model_dump() for r in v.reasons], ensure_ascii=False),
             json.dumps(official_contacts, ensure_ascii=False), v.ruleset_version, iso(now())))

    def verdict(self, check_id: str) -> dict | None:
        r = self.db.execute("SELECT * FROM verdicts WHERE check_id = ?", (check_id,)).fetchone()
        if r is None:
            return None
        d = dict(r)
        for k in ("family_scores", "decisive", "reasons", "official_contacts"):
            d[k] = json.loads(d.pop(f"{k}_json"))
        return d

    # ---- events (SSE replay log) ------------------------------------------------
    def add_event(self, check_id: str, type_: str, data: dict) -> int:
        seq = self.db.execute("SELECT COALESCE(MAX(seq), 0) + 1 FROM check_events WHERE check_id = ?",
                              (check_id,)).fetchone()[0]
        self.db.execute("INSERT INTO check_events (check_id, seq, type, data_json, created_at) VALUES (?, ?, ?, ?, ?)",
                        (check_id, seq, type_, json.dumps(data, ensure_ascii=False), iso(now())))
        return seq

    def events_after(self, check_id: str, seq: int) -> list[tuple[int, str, dict]]:
        rows = self.db.execute("SELECT seq, type, data_json FROM check_events WHERE check_id = ? AND seq > ? ORDER BY seq",
                               (check_id, seq))
        return [(r[0], r[1], json.loads(r[2])) for r in rows]

    # ---- credits and privacy ----------------------------------------------------
    def credits_for_check(self, check_id: str) -> tuple[int, int]:
        rows = dict(self.db.execute("SELECT cached, COUNT(*) FROM credit_ledger WHERE check_id = ? AND status != "
                                    "'refunded' GROUP BY cached", (check_id,)).fetchall())
        return rows.get(0, 0), rows.get(1, 0)

    def purge_raw(self, check_id: str) -> None:
        """NFR-06: raw text and files go when a check is terminal."""
        for a in self.artifacts(check_id):
            if a["storage_path"]:
                Path(a["storage_path"]).unlink(missing_ok=True)
        self.db.execute("UPDATE artifacts SET storage_path = NULL WHERE check_id = ?", (check_id,))
        self.db.execute("UPDATE checks SET raw_text = NULL WHERE id = ?", (check_id,))


def _put(conn: sqlite3.Connection, key: str, engine: str, params: dict, data: dict) -> None:
    body = json.dumps(data, ensure_ascii=False)
    conn.execute("INSERT OR REPLACE INTO serp_cache (cache_key, engine, params_json, response_json, fetched_at, bytes)"
                 " VALUES (?, ?, ?, ?, ?, ?)",
                 (key, engine, json.dumps(params, sort_keys=True, ensure_ascii=False), body, iso(now()), len(body)))
