"""Typed queries over special26.db (06)."""
import json
import sqlite3
from datetime import UTC, datetime, timedelta

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


def _put(conn: sqlite3.Connection, key: str, engine: str, params: dict, data: dict) -> None:
    body = json.dumps(data, ensure_ascii=False)
    conn.execute("INSERT OR REPLACE INTO serp_cache (cache_key, engine, params_json, response_json, fetched_at, bytes)"
                 " VALUES (?, ?, ?, ?, ?, ?)",
                 (key, engine, json.dumps(params, sort_keys=True, ensure_ascii=False), body, iso(now()), len(body)))
