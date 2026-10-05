from special26.config import Settings
from special26.storage.db import migrate

TABLES = {"schema_version", "checks", "artifacts", "claims", "probe_runs", "findings", "verdicts", "check_events",
          "identifiers", "templates", "lsh_bands", "campaigns", "campaign_members", "serp_cache", "credit_ledger",
          "share_tokens", "known_entities", "eval_runs", "eval_results"}


def test_settings_defaults():
    s = Settings(_env_file=None)
    assert (s.mode, s.credit_budget_per_check, s.daily_credit_cap, s.cache_ttl_hours, s.gl, s.hl) == \
        ("live", 14, 200, 72, "in", "en")
    assert s.share_salt  # random fallback


def test_migration_creates_all_tables_and_is_idempotent(db):
    names = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert TABLES <= names
    migrate(db)
    assert db.execute("SELECT COUNT(*) FROM schema_version").fetchone()[0] == 1
    assert db.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
