"""Retention (06 §5, D-13). Run at startup and hourly. NFR-06."""
from pathlib import Path

TERMINAL = "('done','failed','expired')"
NOW = "strftime('%Y-%m-%dT%H:%M:%SZ','now')"


def run_retention(conn) -> None:
    for (path,) in conn.execute(f"SELECT storage_path FROM artifacts WHERE storage_path IS NOT NULL AND check_id IN "
                                f"(SELECT id FROM checks WHERE status IN {TERMINAL})").fetchall():
        Path(path).unlink(missing_ok=True)
    conn.executescript(f"""
UPDATE checks SET raw_text = NULL WHERE status IN {TERMINAL} AND raw_text IS NOT NULL;
UPDATE artifacts SET storage_path = NULL WHERE check_id IN (SELECT id FROM checks WHERE status IN {TERMINAL});
UPDATE checks SET status = 'expired', raw_text = NULL WHERE status = 'awaiting_confirmation'
  AND updated_at < strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '-30 minutes');
DELETE FROM checks WHERE purge_after < {NOW} AND id NOT IN (SELECT check_id FROM verdicts WHERE tier = 'red');
UPDATE checks SET redacted_text = NULL WHERE purge_after < {NOW};
DELETE FROM templates WHERE check_id NOT LIKE 'seed:%' AND check_id NOT IN (SELECT id FROM checks);
DELETE FROM serp_cache WHERE fetched_at < strftime('%Y-%m-%dT%H:%M:%SZ','now','-30 days');
""")


def seed_known_entities(conn) -> None:
    """Load data/seeds/known_entities.json into known_entities (ids = file order, 06 §4)."""
    import json

    from special26 import seeds
    if conn.execute("SELECT COUNT(*) FROM known_entities").fetchone()[0]:
        return
    for e in seeds.entities():
        conn.execute("INSERT INTO known_entities (id, kind, name, aliases_json, official_domains_json, careers_url,"
                     " fraud_notice_url, source_url, verified_on) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     (e["entity_id"], e["kind"], e["name"], json.dumps(e.get("aliases", [])),
                      json.dumps(e["official_domains"]), e.get("careers_url"), e.get("fraud_notice_url"),
                      e.get("source_url", ""), e.get("verified_on", "")))


def seed_templates(repo) -> int:
    """Load data/seeds/scam_templates/*.txt as label 'scam' (08 §7.5). First line: '# source: <url>'."""
    from special26 import seeds
    from special26.template.minhash import signature
    from special26.template.normalize import tokens
    n = 0
    for f in sorted((seeds.DIR / "scam_templates").glob("*.txt")):
        head, body = seed_header(f)
        src = head.get("source")
        toks = tokens(body)
        if sig := signature(toks):
            repo.save_template(f"seed:{f.name}", "scam", sig, len(toks), src)
            n += 1
    return n


def seed_header(path) -> tuple[dict, str]:
    """'# key: value' lines at the top of a seed template, then the body."""
    head, lines = {}, path.read_text().splitlines()
    while lines and lines[0].startswith("# ") and ":" in lines[0]:
        k, v = lines.pop(0)[2:].split(":", 1)
        head[k.strip()] = v.strip()
    return head, "\n".join(lines)


def seed_provenance(check_id: str) -> str | None:
    from special26 import seeds
    f = seeds.DIR / "scam_templates" / check_id.removeprefix("seed:")
    return seed_header(f)[0].get("provenance") if check_id.startswith("seed:") and f.is_file() else None
