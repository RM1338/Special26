"""T4.2: run golden cases live and record every SerpApi/RDAP response used into data/demo.db.

Spends SerpApi credits (about 8 per case, fewer when cached). Reuses the local cache in data/special26.db.
Usage: .venv/bin/python scripts/record_demo.py [--note "..."]
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "backend/tests/golden")]
from fastapi.testclient import TestClient
from golden_run import EXPECTED, check_invariants, run_all, summary

from special26.config import Settings
from special26.main import create_app
from special26.storage.db import connect_replay

ap = argparse.ArgumentParser()
ap.add_argument("--note", default="golden cases G1, G2, G4, G5, G6a, G6b")
args = ap.parse_args()

tmp = Path(tempfile.mkdtemp(prefix="s26rec-"))
if (ROOT / "data/special26.db").exists():
    shutil.copy(ROOT / "data/special26.db", tmp / "run.db")      # cache-first: reuse earlier live responses
demo = ROOT / "data/demo.db"
s = Settings(_env_file=ROOT / ".env", mode="live", db_path=str(tmp / "run.db"), record_to=str(demo),
             uploads_dir=str(tmp / "up"), demo_db=str(demo))
with TestClient(create_app(s)) as client:
    res = run_all(client)
    used = client.get("/api/health").json()["credits_today"]
snap = {n: summary(b) for n, b in res.items()}
print(json.dumps(snap, indent=1))
try:
    check_invariants(res)
except AssertionError as e:
    print("INVARIANT FAILED, expected.json NOT written:", e)
    sys.exit(1)
EXPECTED.write_text(json.dumps(snap, indent=1) + "\n")
sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT, check=False).stdout.strip()
conn = connect_replay(str(demo))
conn.execute("INSERT INTO recording VALUES (?, ?, ?)", (datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), sha,
                                                         args.note))
print(f"recorded into {demo}; credits used today (local ledger): {used}")
