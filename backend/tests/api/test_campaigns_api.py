"""G6: two brands, one UPI ID -> one campaign (14 §3 G6, FR-43, FR-44)."""


def run_text(client, done, text):
    cid = client.post("/api/checks", data={"text": text}).json()["check_id"]
    client.post(f"/api/checks/{cid}/run")
    return done(client, cid)


def test_g6_campaign(client, done, golden):
    a = run_text(client, done, (golden / "g6a.txt").read_text())
    b = run_text(client, done, (golden / "g6b.txt").read_text())
    assert a["verdict"]["tier"] == b["verdict"]["tier"] == "red"
    assert "P06_ID_SEEN_LOCALLY" in {f["code"] for f in b["findings"]}
    seen = next(f for f in b["findings"] if f["code"] == "P06_ID_SEEN_LOCALLY")
    assert seen["message"] == "The UPI ID hr****@ybl appeared in 1 earlier check marked high risk."
    p06 = next(p for p in b["probes"] if p["probe_id"] == "P06_IDENTIFIER_TRACE")
    assert p06["status"] == "skipped_replay_miss"                    # search not recorded, local memory kept (D-41)
    assert b["campaign"] and a["campaign"] is None                  # G6a had no neighbour when it finished
    camp = client.get(f"/api/campaigns/{b['campaign']['campaign_id']}").json()
    assert camp["member_count"] == 2 and camp["orgs"] == ["Infosys", "HCLTech"]
    assert camp["edge_counts"]["upi"] >= 1 and camp["tier_counts"] == {"red": 2}
    assert {"kind": "upi", "masked": "hr****@ybl", "checks": 2} in camp["shared_identifiers"]
    assert all(m["share_token"] is None for m in camp["members"])


def test_campaign_404_and_merge_redirect(client):
    assert client.get("/api/campaigns/999").status_code == 404
    repo = client.app.state.s26.repo
    a, b = repo.create_campaign(), repo.create_campaign()
    repo.merge_campaign(src=b, dst=a)
    r = client.get(f"/api/campaigns/{b}", follow_redirects=False)
    assert r.status_code == 301 and r.headers["location"] == f"/api/campaigns/{a}"
