"""SQLite connection factory with the 06 pragmas, and migrations."""
import sqlite3
from pathlib import Path

MIGRATIONS = Path(__file__).parent / "migrations"

# demo.db / eval.db: serp_cache (same DDL as 06) plus a recording table.
REPLAY_DDL = """
CREATE TABLE IF NOT EXISTS serp_cache (
  cache_key TEXT PRIMARY KEY, engine TEXT NOT NULL, params_json TEXT NOT NULL,
  response_json TEXT NOT NULL, fetched_at TEXT NOT NULL, bytes INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS recording (recorded_at TEXT, git_sha TEXT, note TEXT);
"""


def connect(path: str) -> sqlite3.Connection:
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def migrate(conn: sqlite3.Connection) -> None:
    has = conn.execute("SELECT 1 FROM sqlite_master WHERE name = 'schema_version'").fetchone()
    current = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] if has else 0
    for f in sorted(MIGRATIONS.glob("*.sql")):
        if int(f.name.split("_")[0]) > current:
            conn.executescript(f.read_text())


def connect_replay(path: str) -> sqlite3.Connection:
    conn = connect(path)
    conn.executescript(REPLAY_DDL)
    return conn
