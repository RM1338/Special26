"""G1..G6 in replay from data/demo.db with the socket guard (11 §9, T4.1). Fails if any verdict changes."""
import json
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from golden_run import EXPECTED, check_invariants, run_all, summary

from special26.config import Settings
from special26.main import create_app

DEMO = Path(__file__).resolve().parents[3] / "data/demo.db"


def recorded() -> bool:
    try:
        return bool(sqlite3.connect(DEMO).execute("SELECT COUNT(*) FROM recording").fetchone()[0])
    except sqlite3.Error:
        return False


pytestmark = pytest.mark.skipif(not recorded() or not EXPECTED.exists(),
                                reason="data/demo.db not recorded yet (scripts/record_demo.py)")


@pytest.fixture(scope="module")
def results(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("golden")
    s = Settings(_env_file=None, mode="replay", demo_db=str(DEMO), db_path=str(tmp / "g.db"),
                 uploads_dir=str(tmp / "up"), share_salt="golden")
    with TestClient(create_app(s)) as client:
        yield run_all(client)


def test_golden_invariants(results):
    check_invariants(results)


def test_golden_frozen(results):
    assert {n: summary(b) for n, b in results.items()} == json.loads(EXPECTED.read_text())


@pytest.mark.xfail(reason="G3 needs a consented real offer .eml with dkim=pass (D-14)", strict=True)
def test_g3_genuine_dkim():
    raise AssertionError("no consented .eml yet")
