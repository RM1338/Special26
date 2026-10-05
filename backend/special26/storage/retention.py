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
