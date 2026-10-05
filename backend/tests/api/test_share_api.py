"""07 §6, FR-42, D-18."""
import json

import pytest

from special26.api import web


def done_g1(client, post_g1, done):
    cid = post_g1(client).json()["check_id"]
    client.post(f"/api/checks/{cid}/run")
    done(client, cid)
    return cid


def test_share_flow_and_masking(client, post_g1, done):
    cid = post_g1(client).json()["check_id"]
    assert client.post(f"/api/checks/{cid}/share").status_code == 409            # not done yet
    client.post(f"/api/checks/{cid}/run")
    done(client, cid)
    a = client.post(f"/api/checks/{cid}/share").json()
    assert len(a["token"]) == 22 and a["url"] == f"/s/{a['token']}"
    assert client.post(f"/api/checks/{cid}/share").json() == a                  # idempotent
    v = client.get(f"/api/share/{a['token']}").json()
    body = json.dumps(v)
    assert "check_id" not in v and "credits" not in v and "warnings" not in v
    assert all("outputs" not in p for p in v["probes"]) and all("raw" not in c for c in v["claims"])
    phone = next(c for c in v["claims"] if c["type"] == "phone")["value"]["e164"]
    assert phone == "+91 ******3210"                                              # FR-42 acceptance
    assert "techm.hr@ybl" not in body and "te****@ybl" in body
    assert "hr.onboarding@" not in body and "techmahindra-careers.in" in body     # domains stay in full
    assert v["verdict"]["tier"] == "red" and v["shared_on"]
    client.get(f"/api/share/{a['token']}")
    assert client.app.state.s26.repo.share(a["token"])["view_count"] == 2


def test_share_404_410(client, post_g1, done):
    assert client.get("/api/share/nope").status_code == 404
    cid = done_g1(client, post_g1, done)
    tok = client.post(f"/api/checks/{cid}/share").json()["token"]
    client.app.state.s26.repo.db.execute("UPDATE share_tokens SET expires_at = '2026-01-01T00:00:00Z'")
    r = client.get(f"/api/share/{tok}")
    assert r.status_code == 410 and r.json()["error"]["code"] == "EXPIRED"


@pytest.mark.skipif(not (web.STATIC / "index.html").exists(), reason="frontend not built")
def test_share_page_og_tags(client, post_g1, done):
    cid = done_g1(client, post_g1, done)
    tok = client.post(f"/api/checks/{cid}/share").json()["token"]
    html = client.get(f"/s/{tok}").text
    assert '<meta property="og:title" content="Strong signs of impersonation. Do not pay." />' in html
    assert "og:description" in html and "recruitment fraud notice" in html
    assert client.app.state.s26.repo.share(tok)["view_count"] == 0               # crawler preview is not a view
