"""07 endpoints and every 07 §9 error code. FR-01..03, FR-14, FR-15, FR-40, NFR-07."""
import json
from pathlib import Path

INTAKE = Path(__file__).parents[1] / "fixtures/intake"


def err(r):
    return r.status_code, r.json()["error"]["code"]


def test_create_returns_claims_awaiting_confirmation(client, post_g1):  # FR-14
    r = post_g1(client)
    assert r.status_code == 201 and r.headers["X-Request-Id"].startswith("req_")
    b = r.json()
    assert b["status"] == "awaiting_confirmation" and b["mode"] == "replay" and b["check_id"].startswith("chk_")
    assert len(b["check_id"]) == 16 and b["links"]["events"].endswith("/events")
    types = {c["type"] for c in b["claims"]}
    assert {"org", "sender_email", "amount", "upi_id", "role"} <= types


def test_errors_400_422(client):
    assert err(client.post("/api/checks", data={"text": "  "})) == (400, "BAD_REQUEST")
    r = client.post("/api/checks", data={"text": "x" * 20001})                                   # FR-01
    assert err(r) == (422, "VALIDATION_ERROR") and r.json()["error"]["details"] == {"field": "text", "max": 20000}
    assert r.json()["request_id"].startswith("req_")
    assert err(client.post("/api/checks", data={"text": "hi", "file_roles": "{bad"})) == (422, "VALIDATION_ERROR")


def test_errors_413_415(client):
    docx = ("offer.docx", b"PK\x03\x04 word", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    assert err(client.post("/api/checks", files=[("files", docx)])) == (415, "UNSUPPORTED_MEDIA")      # FR-02
    big = ("big.pdf", b"%PDF" + b"0" * (5 * 1024 * 1024), "application/pdf")
    assert err(client.post("/api/checks", files=[("files", big)])) == (413, "PAYLOAD_TOO_LARGE")
    small = ("a.pdf", (INTAKE / "tm_offer.pdf").read_bytes(), "application/pdf")
    assert err(client.post("/api/checks", files=[("files", small)] * 5)) == (413, "PAYLOAD_TOO_LARGE")


def test_files_roles_default_and_eml(client):  # FR-03, FR-04, FR-06
    files = [("files", ("tm.pdf", (INTAKE / "tm_offer.pdf").read_bytes(), "application/pdf")),
             ("files", ("g.eml", (INTAKE / "genuine_dkim.eml").read_bytes(), "application/octet-stream"))]
    r = client.post("/api/checks", files=files)
    assert r.status_code == 201
    st = client.app.state.s26
    roles = [a["role"] for a in st.repo.artifacts(r.json()["check_id"])]
    assert roles == ["offer_pdf", "offer_image", "eml"]
    claims = {c["type"]: c for c in r.json()["claims"]}
    assert claims["sender_email"]["source"] == "eml_header" and claims["org"]["value"]["name"] == "Tech Mahindra"


def test_put_claims_edit_add_delete_mine(client, post_g1):  # FR-15, D-09
    b = post_g1(client).json()
    cid = b["check_id"]
    by = {c["type"]: c for c in b["claims"]}
    body = {"claims": [{"id": by["org"]["id"], "type": "org", "value": {"name": "Tech Mahindra"}},
                       {"id": by["sender_email"]["id"], "type": "sender_email",
                        "value": {"address": "Talent@TechMahindra-Careers.in"}},
                       {"id": by["phone"]["id"], "type": "phone", "value": {}},
                       {"id": None, "type": "address", "value": {"raw": "Plot 45, Sector 62, Noida 201309"}}],
            "mine": {"phones": ["+91 98765 43210"], "emails": []}, "org_unknown": False}
    r = client.put(f"/api/checks/{cid}/claims", json=body)
    assert r.status_code == 200
    got = {c["type"]: c for c in r.json()["claims"]}
    assert set(got) == {"org", "sender_email", "phone", "address"}                  # omitted claims deleted
    assert got["org"]["source"] == "dictionary" and got["org"]["id"] == by["org"]["id"]  # unchanged keeps source
    assert got["sender_email"]["source"] == "user" and got["sender_email"]["value"]["address"] == \
        "talent@techmahindra-careers.in"
    assert got["sender_email"]["value"]["registrable_domain"] == "techmahindra-careers.in"
    assert got["phone"]["value"]["role"] == "recipient" and got["address"]["source"] == "user"
    check = client.app.state.s26.repo.get_check(cid)
    assert "98765 43210" not in check["redacted_text"] and "<RECIPIENT_PHONE>" in check["redacted_text"]


def test_put_claims_org_unknown_and_errors(client, post_g1):
    cid = post_g1(client).json()["check_id"]
    r = client.put(f"/api/checks/{cid}/claims", json={"claims": [], "org_unknown": True})
    assert r.json()["warnings"] == ["ORG_UNKNOWN"]
    assert err(client.put(f"/api/checks/{cid}/claims", json={"claims": [{"id": "c_nope", "type": "org",
                                                                          "value": {}}]})) == (422, "VALIDATION_ERROR")
    assert err(client.put(f"/api/checks/{cid}/claims", json={"claims": [{"type": "bogus", "value": {}}]}))[0] == 422
    assert err(client.put("/api/checks/chk_000000000000/claims", json={"claims": []})) == (404, "NOT_FOUND")


def test_run_g1_end_to_end_replay(client, post_g1, done):
    cid = post_g1(client).json()["check_id"]
    r = client.post(f"/api/checks/{cid}/run")
    assert r.status_code == 202 and r.json() == {"check_id": cid, "status": "running"}
    assert err(client.post(f"/api/checks/{cid}/run")) == (409, "CONFLICT_STATE")
    assert err(client.put(f"/api/checks/{cid}/claims", json={"claims": []})) == (409, "CONFLICT_STATE")
    b = done(client, cid)
    v = b["verdict"]
    assert (b["status"], v["tier"], v["red_kind"]) == ("done", "red", "impersonation")
    assert v["decisive"] == ["D1_FEE_VS_NOTICE", "D3_LOOKALIKE_PLUS_FEE"]
    assert v["headline"] == "Strong signs of impersonation. Do not pay."
    assert v["reasons"][0]["message"].startswith("Tech Mahindra's own recruitment fraud notice")
    ids = {f["id"] for f in b["findings"]}
    assert all(set(r["finding_ids"]) <= ids for r in v["reasons"])                      # reasons cite real findings
    assert all(f["effective_weight"] is not None for f in b["findings"])
    assert {"do_not_pay", "verify_official", "call_1930", "report_cybercrime", "report_chakshu",
            "tell_placement_cell"} == set(v["next_steps"])
    assert any(c["kind"] == "careers_url" for c in v["official_contacts"])
    assert b["credits"] == {"used": 0, "cache_hits": 0, "budget": 14}                # replay spends nothing
    st = {p["probe_id"]: p["status"] for p in b["probes"]}
    assert st["P01_ENTITY"] == st["P04_FRAUD_NOTICE"] == "ok"
    assert client.app.state.s26.repo.get_check(cid)["raw_text"] is None                # NFR-06


def test_sse_replay_and_last_event_id(client, post_g1, done):  # FR-40
    cid = post_g1(client).json()["check_id"]
    client.post(f"/api/checks/{cid}/run")
    done(client, cid)
    with client.stream("GET", f"/api/checks/{cid}/events") as r:
        text = "".join(r.iter_text())
    events = [ln.split(": ", 1)[1] for ln in text.splitlines() if ln.startswith("event:")]
    assert events[0] == "check.extracting" and events[-1] == "verdict.ready" and "probe.finished" in events
    ids = [int(ln.split(": ")[1]) for ln in text.splitlines() if ln.startswith("id:")]
    assert ids == list(range(1, len(ids) + 1))
    with client.stream("GET", f"/api/checks/{cid}/events", headers={"Last-Event-ID": str(ids[-2])}) as r:
        tail = "".join(r.iter_text())
    assert [ln for ln in tail.splitlines() if ln.startswith("event:")] == ["event: verdict.ready"]
    data = json.loads(next(ln[6:] for ln in tail.splitlines() if ln.startswith("data:")))
    assert data == {"tier": "red", "red_kind": "impersonation", "campaign_id": None}


def test_expired_410(client, post_g1):
    cid = post_g1(client).json()["check_id"]
    client.app.state.s26.repo.db.execute("UPDATE checks SET updated_at = '2026-01-01T00:00:00Z' WHERE id = ?", (cid,))
    assert err(client.put(f"/api/checks/{cid}/claims", json={"claims": []})) == (410, "EXPIRED")
    assert err(client.post(f"/api/checks/{cid}/run")) == (410, "EXPIRED")


def test_rate_limited_429_live_only(make_client):  # NFR-07
    c = make_client(mode="live", rate_limit_per_hour=1)
    assert c.post("/api/checks", data={"text": "hello offer"}).status_code == 201
    r = c.post("/api/checks", data={"text": "hello offer"})
    assert err(r) == (429, "RATE_LIMITED") and int(r.headers["Retry-After"]) > 0


def test_budget_exhausted_429_before_start(make_client):
    c = make_client(mode="live", daily_credit_cap=0)
    cid = c.post("/api/checks", data={"text": "hello offer"}).json()["check_id"]
    assert err(c.post(f"/api/checks/{cid}/run")) == (429, "BUDGET_EXHAUSTED")


def test_404_and_health(client):
    assert err(client.get("/api/checks/chk_000000000000")) == (404, "NOT_FOUND")
    h = client.get("/api/health").json()
    assert h["status"] == "ok" and h["mode"] == "replay" and h["db"] == "ok" and h["ruleset_version"] == "2026.10.1"
    assert h["credits_today"] == {"used": 0, "cap": 200}


def test_public_img_token(client):  # NFR-07, D-25
    from special26.api.public_img import sign
    photo = (Path(__file__).parents[1] / "golden/inputs/g5_hr_photo.jpg").read_bytes()
    r = client.post("/api/checks", files=[("files", ("hr.jpg", photo, "image/jpeg"))], data={"file_roles": '["hr_photo"]'})
    st = client.app.state.s26
    art = st.repo.artifacts(r.json()["check_id"])[0]
    assert art["role"] == "hr_photo" and art["storage_path"].startswith(st.settings.uploads_dir)
    ok = client.get(f"/public/img/{sign(st.settings.share_salt, art['sha256'])}")
    assert ok.status_code == 200 and ok.headers["content-type"] == "image/jpeg"
    assert err(client.get("/public/img/garbage")) == (404, "NOT_FOUND")
