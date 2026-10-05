"""FR-20: one test per finding code for P01, P02, P11."""
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from special26.claims.extract import extract_claims
from special26.claims.redact import redact
from special26.probes.base import ProbeContext, ProbeResult
from special26.probes.p01_entity import P01Entity
from special26.probes.p02_sender import P02Sender
from special26.probes.p11_policy import P11Policy

FIX = Path(__file__).parents[1] / "fixtures/serp"
GOLDEN = Path(__file__).parents[1] / "golden/inputs"


class FakeSerp:
    def __init__(self, by_q: dict | None = None):
        self.by_q, self.calls = by_q or {}, []

    async def search(self, check_id, params):
        self.calls.append(params)
        return self.by_q.get(params["q"], {"organic_results": []}), f"key{len(self.calls)}", False


def ctx(text, official=(), serp=None, upstream=None):
    red, _ = redact(text)
    up = dict(upstream or {})
    if official is not None:
        up.setdefault("P01_ENTITY", ProbeResult(probe_id="P01_ENTITY", status="ok",
                                                outputs={"official_domains": list(official)}))
    return ProbeContext(check_id=None, claims=extract_claims(red), created_at=datetime(2026, 10, 7, tzinfo=UTC),
                        upstream=up, serp=serp, redacted_text=red)


def codes(res):
    return [f.code for f in res.findings]


# ---- P01 -------------------------------------------------------------------------------------------------------
async def test_p01_official_found_on_live_fixture():
    data = json.loads((FIX / "google_entity_techmahindra.json").read_text())
    serp = FakeSerp({'"Tech Mahindra"': data})
    c = ctx("Welcome to Tech Mahindra", official=None, serp=serp)
    res = await P01Entity().run(c)
    assert codes(res) == ["P01_OFFICIAL_FOUND"]
    assert res.outputs["official_domains"][0] == "techmahindra.com"
    assert res.findings[0].receipt.extra["source"] == "knowledge_graph.website"
    assert res.findings[0].message == "Google Search shows Tech Mahindra's official website is techmahindra.com."
    kinds = {x["kind"]: x["value"] for x in res.outputs["official_contacts"]}
    assert kinds["careers_url"].startswith("https://careers.techmahindra.com/")
    assert len(serp.calls) == 1 and res.credits_used == 1


async def test_p01_no_presence_runs_q2():
    serp = FakeSerp()
    c = ctx("We at Nimbleleaf Analytics Pvt Ltd liked your resume.", official=None, serp=serp)
    res = await P01Entity().run(c)
    assert codes(res) == ["P01_NO_PRESENCE"] and res.outputs["official_domains"] == []
    assert [p["q"] for p in serp.calls] == ['"Nimbleleaf Analytics"', '"Nimbleleaf Analytics" careers']


async def test_p01_seed_domains_skip_q2():  # D-32
    serp = FakeSerp()
    res = await P01Entity().run(ctx("Offer from Infosys Limited", official=None, serp=serp))
    assert res.outputs["official_domains"] == ["infosys.com"] and len(serp.calls) == 1
    assert codes(res) == ["P01_OFFICIAL_FOUND"]


def test_p01_skipped_without_org():
    assert P01Entity().applicable(ctx("hello there", official=None)) == "skipped_no_input"


# ---- P02 -------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("text,official,expected", [
    ("Tech Mahindra\nRegards\nhr@careers.techmahindra.com", ["techmahindra.com"], ["P02_SENDER_OFFICIAL"]),
    ("Infosys\nRegards\nhr@lnfosys.com", ["infosys.com"], ["P02_HOMOGLYPH"]),
    ("Tech Mahindra\nRegards\nhr@tecmahindra.com", ["techmahindra.com"], ["P02_TYPOSQUAT"]),
    ("Tech Mahindra\nRegards\nhr@techmahindra-careers.in", ["techmahindra.com"], ["P02_COMBOSQUAT"]),
    ("Tech Mahindra\nRegards\nhr@techmahindra.co.in", ["techmahindra.com"], ["P02_TLD_SWAP"]),
    ("Wipro\nRegards\nwipro.hr@gmail.com", ["wipro.com"], ["P02_FREEMAIL"]),
    ("Acme Widgets\nRegards\nacme.hr@gmail.com", [], ["P02_FREEMAIL_NO_PRESENCE"]),
    ("TCS\nRegards\nhr@hiringdesk-global.com", ["tcs.com"], ["P02_UNRELATED"]),
    ("TCS\nRegards\nhr@tcs.com\nPlease reply to tcs.desk@gmail.com", ["tcs.com"],
     ["P02_SENDER_OFFICIAL", "P02_REPLY_DIVERTED"]),
])
async def test_p02_codes(text, official, expected):
    res = await P02Sender().run(ctx(text, official=official))
    assert sorted(codes(res)) == sorted(expected)


async def test_p02_link_domain_and_message():
    c = ctx("Tech Mahindra. Apply at https://techmahindra-jobs.in/apply now", official=["techmahindra.com"])
    res = await P02Sender().run(c)
    assert codes(res) == ["P02_COMBOSQUAT"]
    assert res.findings[0].message == ("The link domain techmahindra-jobs.in is not Tech Mahindra's. Tech Mahindra "
                                       "uses techmahindra.com.")


async def test_p02_reply_diverted_replaced_by_p03():
    p03 = ProbeResult(probe_id="P03_HEADERS", status="ok")
    p03.findings = (await P02Sender().run(ctx("TCS\nRegards\nhr@tcs.com\nPlease reply to t.d@gmail.com",
                                              official=["tcs.com"]))).findings
    for f in p03.findings:
        f.code = "P03_REPLY_DIVERTED" if f.code == "P02_REPLY_DIVERTED" else f.code
    res = await P02Sender().run(ctx("TCS\nRegards\nhr@tcs.com\nPlease reply to t.d@gmail.com", official=["tcs.com"],
                                    upstream={"P03_HEADERS": p03}))
    assert codes(res) == ["P02_SENDER_OFFICIAL"]


def test_p02_skipped_without_inputs():
    assert P02Sender().applicable(ctx("Infosys offer", official=["infosys.com"])) == "skipped_no_input"


async def test_p02_g1():
    res = await P02Sender().run(ctx((GOLDEN / "g1.txt").read_text(), official=["techmahindra.com"]))
    assert codes(res) == ["P02_COMBOSQUAT"]


# ---- P11 -------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("text,code", [
    ("Please pay Rs 2,000 for police verification.", "P11_CANDIDATE_PAYS"),
    ("Pay a refundable security deposit of Rs 5,000 via UPI.", "P11_REFUNDABLE_BAIT"),
    ("Pay to techm.hr@ybl", "P11_PERSONAL_UPI"),
    ("Kindly scan the QR to complete onboarding", "P11_PERSONAL_UPI"),
    ("PM Internship Scheme. Apply: https://forms.gle/abc", "P11_SCHEME_OFF_PORTAL"),
    ("Apply here https://forms.gle/abc", "P11_FORM_OR_SHORTLINK"),
    ("Confirm within 24 hours", "P11_URGENCY"),
    ("You are selected without interview", "P11_NO_INTERVIEW"),
    ("Your interview on WhatsApp is at 5", "P11_CHAT_INTERVIEW"),
])
async def test_p11_codes(text, code):
    assert code in codes(await P11Policy().run(ctx(text)))


@pytest.mark.parametrize("text", [
    "Stipend Rs 15,000 per month.",                                  # employer pays
    "Registration fee Rs 499 (non-refundable) to x@paytm",           # D-23: no refundable bait
    "PM Internship Scheme. Apply at https://pminternship.mca.gov.in/apply",   # on portal
    "Apply at https://www.infosys.com/careers",
])
async def test_p11_negatives(text):
    got = codes(await P11Policy().run(ctx(text)))
    assert not {"P11_REFUNDABLE_BAIT", "P11_SCHEME_OFF_PORTAL", "P11_FORM_OR_SHORTLINK"} & set(got)
    if "Stipend" in text:
        assert got == []


async def test_p11_g1_messages():
    res = await P11Policy().run(ctx((GOLDEN / "g1.txt").read_text()))
    assert codes(res) == ["P11_CANDIDATE_PAYS", "P11_PERSONAL_UPI", "P11_URGENCY", "P11_NO_INTERVIEW"]
    msg = {f.code: f.message for f in res.findings}
    assert msg["P11_PERSONAL_UPI"] == "You are asked to pay a personal UPI ID (te****@ybl) within 24 hours."  # D-07
    assert msg["P11_CANDIDATE_PAYS"].startswith("The offer asks you to pay ₹2,000 for verification.")
    assert all(f.receipt.kind == "rule" and f.receipt.rule_id for f in res.findings)    # FR-27


async def test_p11_g2_scheme():
    res = await P11Policy().run(ctx((GOLDEN / "g2.txt").read_text()))
    assert {"P11_SCHEME_OFF_PORTAL", "P11_FORM_OR_SHORTLINK", "P11_CANDIDATE_PAYS", "P11_PERSONAL_UPI",
            "P11_URGENCY"} == set(codes(res))
