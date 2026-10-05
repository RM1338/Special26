"""FR-20 for P07, P08 (and later M3 probes): one test per finding code."""
import json
from pathlib import Path

import pytest
from test_probes_core import FakeSerp, codes, ctx

from special26.errors import UpstreamError
from special26.probes.p07_role import P07Role
from special26.probes.p08_office import P08Office

FIX = Path(__file__).parents[1] / "fixtures/serp"
G1_ROLE = "selected for the position of Data Analyst Intern at Tech Mahindra"


class AnySerp(FakeSerp):
    """Returns one canned response for every call (records params)."""
    def __init__(self, data):
        super().__init__()
        self.data = data

    async def search(self, check_id, params):
        self.calls.append(params)
        if isinstance(self.data, Exception):
            err, self.data = self.data, {"jobs_results": []}
            raise err
        return self.data, f"k{len(self.calls)}", False


# ---- P07 -------------------------------------------------------------------------------------------------------
async def test_p07_role_listed_live_fixture():
    data = json.loads((FIX / "google_jobs_techmahindra.json").read_text())
    serp = AnySerp(data)
    res = await P07Role().run(ctx(G1_ROLE, official=["techmahindra.com"], serp=serp))
    assert codes(res) == ["P07_ROLE_LISTED"]
    f = res.findings[0]
    assert f.message == "Google Jobs lists a Data Analyst Intern role at Tech Mahindra."
    assert f.receipt.engine == "google_jobs" and f.receipt.title.startswith("Data Analyst Intern at Tech Mahindra")
    assert serp.calls[0]["location"] == "India"


async def test_p07_other_roles_and_none():
    data = {"jobs_results": [{"title": "Senior Java Architect", "company_name": "Tech Mahindra Ltd"}]}
    assert codes(await P07Role().run(ctx(G1_ROLE, serp=AnySerp(data)))) == ["P07_COMPANY_LISTS_OTHER_ROLES"]
    other = {"jobs_results": [{"title": "Data Analyst Intern", "company_name": "Some Other Co"}]}
    assert codes(await P07Role().run(ctx(G1_ROLE, serp=AnySerp(other)))) == []


async def test_p07_city_location_falls_back_to_india():  # D-37
    serp = AnySerp(UpstreamError("Unsupported `Noida, India` location - location parameter."))
    await P07Role().run(ctx(G1_ROLE + ", Noida", serp=serp))
    assert [c["location"] for c in serp.calls] == ["Noida, India", "India"]


def test_p07_needs_role_and_org():
    assert P07Role().applicable(ctx("Welcome to Infosys")) == "skipped_no_input"


# ---- P08 -------------------------------------------------------------------------------------------------------
async def test_p08_office_match_live_fixture():
    data = json.loads((FIX / "google_maps_techmahindra.json").read_text())
    c = ctx("Welcome to Tech Mahindra Limited, Noida.", official=["techmahindra.com"], serp=AnySerp(data))
    res = await P08Office().run(c)
    assert codes(res) == ["P08_OFFICE_MATCH"]
    assert res.findings[0].receipt.link.startswith("https://www.google.com/maps/search/?api=1&query=Tech+Mahindra")


def place(title="Shanti Apartments", type_="Apartment building", review=""):
    return {"local_results": [{"title": title, "type": type_, "types": [type_], "user_review": review,
                               "place_id": "x"}]}


@pytest.mark.parametrize("data,code", [
    (place(), "P08_RESIDENTIAL"),
    (place("Hostel Sunrise", "Hostel"), "P08_RESIDENTIAL"),
    (place("WeWork Galaxy", "Coworking space"), "P08_COWORKING"),
    ({"local_results": []}, "P08_NOT_FOUND"),
    (place("Acme Widgets", "Corporate office", "They took money for a fake offer letter"), "P08_REVIEWS_SCAM"),
])
async def test_p08_codes(data, code):
    text = "Welcome to Acme Widgets. Office: Plot 9, Sector 18, Noida 201301"
    assert code in codes(await P08Office().run(ctx(text, official=["acmewidgets.in"], serp=AnySerp(data))))


async def test_p08_bare_city_uses_org_office_query():  # D-37
    serp = AnySerp({"local_results": []})
    res = await P08Office().run(ctx("Greetings from Wipro Limited! Join our Bengaluru campus.", serp=serp))
    assert serp.calls[0]["q"] == "Wipro office Bengaluru" and codes(res) == []        # NOT_FOUND only for addresses


def test_p08_skipped_without_address_or_city():
    assert P08Office().applicable(ctx("Welcome to Infosys")) == "skipped_no_input"


# ---- P09 (D-27, D-38) ------------------------------------------------------------------------------------------
from types import SimpleNamespace

from special26.api.public_img import sign, verify
from special26.probes.p09_image import P09Image


class LensSerp(FakeSerp):
    def __init__(self, by_type: dict, upload_ok=True):
        super().__init__()
        self.by_type, self.upload_ok, self.uploads = by_type, upload_ok, 0

    async def upload_image(self, jpeg):
        self.uploads += 1
        if not self.upload_ok:
            raise UpstreamError("upload down")
        return "img123"

    async def search(self, check_id, params):
        self.calls.append(params)
        return self.by_type.get(params["type"], {}), f"k{len(self.calls)}", False


def lens_ctx(tmp_path, serp, roles=("hr_photo",), hr="Neha Kapoor", public=None, reserved=0, mode="live"):
    img = tmp_path / "a.jpg"
    img.write_bytes((Path(__file__).parents[1] / "golden/inputs/g5_hr_photo.jpg").read_bytes())
    arts = [{"id": i + 1, "sha256": f"sha{i}", "storage_path": str(img), "role": r} for i, r in enumerate(roles)]
    c = ctx(f"Regards,\n{hr}\nHR Manager" if hr else "Hello", serp=serp)
    from special26.claims.models import Claim, ClaimType
    c.claims.claims += [Claim.make(ClaimType.image, {"artifact_id": a["id"], "role": a["role"]}, a["role"], "regex", 1.0)
                        for a in arts]
    c.repo = SimpleNamespace(artifacts=lambda _cid: arts)
    c.settings = SimpleNamespace(mode=mode, public_base_url=public, share_salt="s", credit_budget_per_check=14)
    c.check_id, c.reserved_calls = "chk_x", reserved
    return c


async def test_p09_stock_photo_from_upload_fixture(tmp_path):
    data = json.loads((FIX / "google_lens_g5_upload.json").read_text())
    serp = LensSerp({"exact_matches": data})
    res = await P09Image().run(lens_ctx(tmp_path, serp))
    assert "P09_STOCK_PHOTO" in codes(res) and serp.uploads == 1
    stock = next(f for f in res.findings if f.code == "P09_STOCK_PHOTO")
    assert stock.message == "Google Lens finds the HR photo on the stock photo site pexels.com."
    assert serp.calls[0]["image_id"] == "img123" and serp.calls[0]["image_sha256"] == "sha0"


async def test_p09_other_names_and_official(tmp_path):
    ms = [{"position": i, "title": f"Meet Arjun Verma {i}", "link": f"https://site{i}.com/p"} for i in range(3)]
    ms.append({"position": 9, "title": "Neha Kapoor - HR Manager", "link": "https://www.linkedin.com/in/nehak"})
    res = await P09Image().run(lens_ctx(tmp_path, LensSerp({"exact_matches": {"exact_matches": ms}})))
    assert set(codes(res)) == {"P09_PHOTO_OTHER_NAMES", "P09_PHOTO_OFFICIAL"}


async def test_p09_letter_reported_respects_budget(tmp_path):
    vis = {"visual_matches": [{"position": 1, "title": "Beware: fake offer letter", "link": "https://x.in/a"}]}
    res = await P09Image().run(lens_ctx(tmp_path, LensSerp({"visual_matches": vis}), roles=("offer_image",)))
    assert codes(res) == ["P09_LETTER_REPORTED"]
    serp = LensSerp({"visual_matches": vis})
    res = await P09Image().run(lens_ctx(tmp_path, serp, roles=("offer_image",), reserved=12))
    assert codes(res) == [] and serp.calls == []                       # 14 - 12 < 3: no letter call


async def test_p09_fallbacks(tmp_path):
    serp = LensSerp({}, upload_ok=False)
    res = await P09Image().run(lens_ctx(tmp_path, serp))
    assert res.status == "skipped_no_public_url" and serp.calls == []
    serp = LensSerp({}, upload_ok=False)
    await P09Image().run(lens_ctx(tmp_path, serp, public="https://s26.example"))
    assert serp.calls[0]["url"].startswith("https://s26.example/public/img/")
    serp = LensSerp({})
    await P09Image().run(lens_ctx(tmp_path, serp, mode="replay"))
    assert serp.uploads == 0 and serp.calls[0]["image_id"] == "replay"


def test_p09_skipped_without_images():
    assert P09Image().applicable(ctx("hello")) == "skipped_no_input"


def test_image_token_sign_verify():  # D-25
    t = sign("salt", "abc", now=1000)
    assert verify("salt", t, now=1500) == "abc"
    assert verify("salt", t, now=1000 + 601) is None                  # 10 minute expiry
    assert verify("other", t, now=1500) is None and verify("salt", t[:-2] + "xx", now=1500) is None


# ---- P03 (D-39) ------------------------------------------------------------------------------------------------
from special26.intake.eml import parse_eml as _parse
from special26.probes.p03_headers import P03Headers

INTAKE = Path(__file__).parents[1] / "fixtures/intake"


def eml_ctx(name, official):
    raw = (INTAKE / name).read_bytes()
    from special26.claims.extract import extract_claims
    from special26.claims.redact import redact
    e = _parse(raw)
    c = ctx("x", official=official)
    c.claims = extract_claims(redact(e["body"])[0], eml=e)
    c.repo = SimpleNamespace(artifacts=lambda _cid: [{"role": "eml", "storage_path": str(INTAKE / name)}])
    c.check_id = "chk_x"
    return c


async def test_p03_dkim_aligned_official():
    res = await P03Headers().run(eml_ctx("genuine_dkim.eml", ["acme-example.com"]))
    assert codes(res) == ["P03_DKIM_ALIGNED_OFFICIAL"] and res.outputs["auth"]["dmarc"] == "pass"
    assert "dkim=pass" in res.findings[0].receipt.extra["header"]


async def test_p03_not_aligned_when_not_official():
    assert codes(await P03Headers().run(eml_ctx("genuine_dkim.eml", ["other.com"]))) == []


async def test_p03_auth_fail_and_reply_diverted():
    res = await P03Headers().run(eml_ctx("auth_fail.eml", ["techmahindra.com"]))
    assert codes(res) == ["P03_AUTH_FAIL", "P03_REPLY_DIVERTED"]
    assert "DMARC fail" in res.findings[0].message and "t***@gmail.com" in res.findings[1].message


async def test_p03_forwarded_skipped():
    assert (await P03Headers().run(eml_ctx("forwarded.eml", ["techmahindra.com"]))).status == "skipped_forwarded"


def test_p03_skipped_without_eml():
    c = ctx("hello")
    c.repo, c.check_id = SimpleNamespace(artifacts=lambda _cid: []), "chk_x"
    assert P03Headers().applicable(c) == "skipped_no_input"


# ---- P06 (D-41) ------------------------------------------------------------------------------------------------
from special26.errors import ReplayMiss
from special26.probes.p06_identifier_trace import P06IdentifierTrace

G1_TEXT = (Path(__file__).parents[1] / "golden/inputs/g1.txt").read_text()


async def test_p06_reported_per_source_and_query_order():
    data = {"organic_results": [
        {"position": 1, "title": "Fraud alert: techm.hr@ybl", "snippet": "students cheated", "link": "https://a.in/x"},
        {"position": 2, "title": "Scam warning", "snippet": "pay to techm.hr@ybl", "link": "https://www.a.in/y"},
        {"position": 3, "title": "Beware fake offers", "snippet": "call 98765 43210", "link": "https://b.com/z"},
        {"position": 4, "title": "Jobs portal", "snippet": "techm.hr@ybl", "link": "https://c.com/z"}]}
    serp = AnySerp(data)
    res = await P06IdentifierTrace().run(ctx(G1_TEXT, official=["techmahindra.com"], serp=serp))
    assert codes(res) == ["P06_ID_REPORTED", "P06_ID_REPORTED"]               # a.in once, b.com once, c.com no scam word
    assert serp.calls[0]["q"] == '"techm.hr@ybl" OR "9876543210" OR "techmahindra-careers.in" OR ' \
                                 '"hr.onboarding@techmahindra-careers.in"'
    assert res.findings[0].message == "The UPI ID te****@ybl from this offer appears in a public warning on a.in."


async def test_p06_on_official():
    data = {"organic_results": [{"position": 1, "title": "Contact us", "snippet": "HR helpline 98765 43210",
                                 "link": "https://www.techmahindra.com/contact"}]}
    res = await P06IdentifierTrace().run(ctx(G1_TEXT, official=["techmahindra.com"], serp=AnySerp(data)))
    assert codes(res) == ["P06_ID_ON_OFFICIAL"] and "+91 ******3210" in res.findings[0].message


async def test_p06_search_failure_keeps_status():
    res = await P06IdentifierTrace().run(ctx(G1_TEXT, official=["techmahindra.com"], serp=AnySerp(ReplayMiss())))
    assert res.status == "skipped_replay_miss" and res.findings == []


def test_p06_freemail_only_is_not_applicable():
    assert P06IdentifierTrace().applicable(ctx("Regards\nme.hr@gmail.com", official=[])) == "skipped_no_input"


# ---- P05 (D-42) ------------------------------------------------------------------------------------------------
from datetime import UTC, datetime

from special26.probes.p05_chatter import P05Chatter, result_date


class EngineSerp(FakeSerp):
    def __init__(self, by_engine: dict):
        super().__init__()
        self.by_engine = by_engine

    async def search(self, check_id, params):
        self.calls.append(params)
        v = self.by_engine.get(params["engine"], {})
        if isinstance(v, Exception):
            raise v
        return v, f"k{len(self.calls)}", False


def complaint(i, title="Tech Mahindra fake job offer scam warning", snippet="students cheated", date="1 year ago",
              link=None):
    return {"position": i, "title": title, "snippet": snippet, "link": link or f"https://forum{i}.in/t",
            "displayed_meta": date}


async def test_p05_general_names_sender_and_live_fixtures():
    forums = json.loads((FIX / "google_forums_techmahindra.json").read_text())
    forums["organic_results"] += [complaint(90 + i) for i in range(3)]
    forums["organic_results"].append(complaint(99, snippet="mail from hr.onboarding@techmahindra-careers.in asked fee"))
    serp = EngineSerp({"google_news": json.loads((FIX / "google_news_techmahindra.json").read_text()),
                       "google_forums": forums, "google": {"organic_results": []}})
    res = await P05Chatter().run(ctx(G1_TEXT, official=["techmahindra.com"], serp=serp))
    assert codes(res) == ["P05_COMPLAINTS_GENERAL", "P05_COMPLAINT_NAMES_SENDER"]
    assert "techmahindra-careers.in" in res.findings[1].message
    assert serp.calls[0]["q"].endswith("-site:techmahindra.com") and len(serp.calls) == 3


async def test_p05_old_complaints_ignored_and_forums_optional():
    serp = EngineSerp({"google": {"organic_results": [complaint(i, date="5 years ago") for i in range(4)]},
                       "google_news": {"news_results": []}, "google_forums": UpstreamError("down")})
    res = await P05Chatter().run(ctx(G1_TEXT, official=["techmahindra.com"], serp=serp))
    assert res.status == "ok" and codes(res) == [] and res.outputs["complaints"] == 0


async def test_p05_pib_factcheck_and_both_core_calls_failing():
    g2 = (Path(__file__).parents[1] / "golden/inputs/g2.txt").read_text()
    serp = EngineSerp({"google_news": {"news_results": [
        {"title": "PIB Fact Check: Fake PM Internship registration form", "link": "https://www.pib.gov.in/x"}]}})
    assert codes(await P05Chatter().run(ctx(g2, official=["mca.gov.in"], serp=serp))) == ["P05_PIB_FACTCHECK"]
    down = EngineSerp({"google": UpstreamError("x"), "google_news": UpstreamError("y")})
    with pytest.raises(UpstreamError):
        await P05Chatter().run(ctx(G1_TEXT, official=[], serp=down))


def test_result_dates():
    now = datetime(2026, 10, 7, tzinfo=UTC)
    assert result_date({"iso_date": "2026-03-09T07:00:00Z"}, now).year == 2026
    assert (now - result_date({"displayed_meta": "10+ comments · 2 years ago"}, now)).days == 730
    assert result_date({"date": "Mar 3, 2024"}, now).month == 3 and result_date({}, now) is None
