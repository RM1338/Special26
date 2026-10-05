"""Golden cases G1..G6 (14 §3) run through the real API. Shared by tests/golden and scripts/record_demo.py."""
import json
import time
from pathlib import Path

HERE = Path(__file__).parent
INPUTS = HERE / "inputs"
EXPECTED = HERE / "expected.json"
ORDER = ["G1", "G2", "G4", "G5", "G6a", "G6b"]          # G3 needs a consented .eml (D-14)


def _wait(client, cid, timeout=120.0):
    t = time.monotonic()
    while time.monotonic() - t < timeout:
        b = client.get(f"/api/checks/{cid}").json()
        if b["status"] in ("done", "failed"):
            return b
        time.sleep(0.1)
    raise AssertionError(f"{cid} did not finish")


def run_case(client, name: str) -> dict:
    text = (INPUTS / f"{name.lower()}.txt").read_text()
    files, roles = [], []
    if name == "G5":
        files = [("files", ("hr.jpg", (INPUTS / "g5_hr_photo.jpg").read_bytes(), "image/jpeg"))]
        roles = ["hr_photo"]
    r = client.post("/api/checks", data={"text": text, "file_roles": json.dumps(roles)}, files=files or None)
    assert r.status_code == 201, r.text
    cid = r.json()["check_id"]
    assert client.post(f"/api/checks/{cid}/run").status_code == 202
    return _wait(client, cid)


def run_all(client) -> dict[str, dict]:
    return {name: run_case(client, name) for name in ORDER}


def summary(b: dict) -> dict:
    v = b["verdict"]
    return {"tier": v["tier"], "red_kind": v["red_kind"], "decisive": v["decisive"],
            "reason1": v["reasons"][0]["code"] if v["reasons"] else None}


def check_invariants(res: dict[str, dict]) -> None:
    """What 14 §3 requires, independent of the frozen snapshot."""
    codes = {n: {f["code"] for f in b["findings"]} for n, b in res.items()}
    s = {n: summary(b) for n, b in res.items()}
    assert s["G1"] == {"tier": "red", "red_kind": "impersonation",
                       "decisive": ["D1_FEE_VS_NOTICE", "D3_LOOKALIKE_PLUS_FEE"], "reason1": "D1_FEE_VS_NOTICE"}, s["G1"]
    assert s["G2"]["tier"] == "red" and s["G2"]["red_kind"] == "impersonation", s["G2"]
    assert "D2_SCHEME_IMPERSONATION" in s["G2"]["decisive"] and s["G2"]["reason1"] == "D2_SCHEME_IMPERSONATION"
    assert any("pminternship.mca.gov.in" in c["value"] for c in res["G2"]["verdict"]["official_contacts"])
    assert s["G4"]["tier"] == "amber", s["G4"]
    assert {"P01_NO_PRESENCE", "P02_FREEMAIL_NO_PRESENCE", "P11_NO_INTERVIEW"} <= codes["G4"]
    assert s["G5"]["tier"] == "red" and s["G5"]["red_kind"] == "impersonation", s["G5"]
    assert {"P02_FREEMAIL", "P09_STOCK_PHOTO", "P11_CANDIDATE_PAYS"} <= codes["G5"]
    assert s["G6a"]["tier"] == s["G6b"]["tier"] == "red"
    assert "P06_ID_SEEN_LOCALLY" in codes["G6b"]
    camp = res["G6b"]["campaign"]
    assert camp and camp["orgs"] == ["Infosys", "HCLTech"] and camp["member_count"] == 2
