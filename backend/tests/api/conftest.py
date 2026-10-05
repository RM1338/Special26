import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from special26.config import Settings
from special26.main import create_app
from special26.probes.p04_fraud_notice import query
from special26.serp.client import cache_key
from special26.storage.db import connect_replay

FIX = Path(__file__).parents[1] / "fixtures/serp"
GOLDEN = Path(__file__).parents[1] / "golden/inputs"


def record(demo_db: str, params: dict, fixture: str) -> None:
    params = {"gl": "in", "hl": "en", **params}
    conn = connect_replay(demo_db)
    conn.execute("INSERT OR REPLACE INTO serp_cache VALUES (?, ?, '{}', ?, '2026-10-05T00:00:00Z', 1)",
                 (cache_key(params), params["engine"], (FIX / fixture).read_text()))


@pytest.fixture
def make_client(tmp_path):
    clients = []

    def make(**overrides):
        kw = {"db_path": str(tmp_path / "t.db"), "demo_db": str(tmp_path / "demo.db"),
              "uploads_dir": str(tmp_path / "uploads"), "share_salt": "salt", "mode": "replay", **overrides}
        s = Settings(_env_file=None, **kw)
        record(s.demo_db, {"engine": "google", "q": '"Tech Mahindra"', "num": 10}, "google_entity_techmahindra.json")
        record(s.demo_db, {"engine": "google", "q": query(["techmahindra.com"]), "num": 10},
               "google_notice_techmahindra.json")
        c = TestClient(create_app(s))
        c.__enter__()
        clients.append(c)
        return c
    yield make
    for c in clients:
        c.__exit__(None, None, None)


@pytest.fixture
def client(make_client):
    return make_client()


def wait_done(client, check_id, timeout=10.0):
    t = time.monotonic()
    while time.monotonic() - t < timeout:
        body = client.get(f"/api/checks/{check_id}").json()
        if body["status"] in ("done", "failed"):
            return body
        time.sleep(0.05)
    raise AssertionError("check did not finish")


def g1(client, **form):
    return client.post("/api/checks", data={"text": (GOLDEN / "g1.txt").read_text(), **form})


def dump(r):
    return json.dumps(r.json(), indent=1)


@pytest.fixture
def done():
    return wait_done


@pytest.fixture
def post_g1():
    return g1


@pytest.fixture
def golden():
    return GOLDEN
