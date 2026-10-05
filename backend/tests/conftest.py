import socket

import pytest

from special26.config import Settings
from special26.storage.db import connect, connect_replay, migrate
from special26.storage.repo import Repo


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Socket guard: tests never touch the network (FR-26, credits)."""
    def guard(*a, **k):
        raise RuntimeError("network access in tests")
    monkeypatch.setattr(socket.socket, "connect", guard)
    monkeypatch.setattr(socket, "create_connection", guard)


@pytest.fixture
def settings(tmp_path):
    return Settings(_env_file=None, db_path=str(tmp_path / "t.db"), demo_db=str(tmp_path / "demo.db"),
                    share_salt="test-salt", serpapi_api_key="SECRET-KEY-123")


@pytest.fixture
def db(settings):
    conn = connect(settings.db_path)
    migrate(conn)
    return conn


@pytest.fixture
def repo(db, settings):
    return Repo(db, replay=connect_replay(settings.demo_db))


@pytest.fixture
def check_id(db):
    check_id, mode = "chk_test00000001", "live"
    ts = "2026-10-07T10:15:30Z"
    db.execute("INSERT INTO checks (id, created_at, updated_at, status, mode, purge_after)"
               " VALUES (?, ?, ?, 'running', ?, ?)", (check_id, ts, ts, mode, "2026-11-06T10:15:30Z"))
    return check_id
