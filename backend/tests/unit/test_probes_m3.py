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
