"""FR-30 to FR-36: caps, decisive rules, tiers (green gate, grey), reasons, coverage, determinism."""
import random
import re

import pytest

from special26.probes.base import Finding, ProbeResult, Receipt, validate_ruleset, weights
from special26.scoring.aggregate import coverage, effective_weights, score, strength
from special26.scoring.copy import COPY, DECISIVE_COPY, HEADLINES, RULE_COPY, SUBLINES, inr

PROBE_OF = {"P01": "P01_ENTITY", "P02": "P02_SENDER", "P03": "P03_HEADERS", "P04": "P04_FRAUD_NOTICE",
            "P05": "P05_CHATTER", "P06": "P06_IDENTIFIER_TRACE", "P07": "P07_ROLE", "P08": "P08_OFFICE",
            "P09": "P09_IMAGE", "P10": "P10_TEMPLATE", "P11": "P11_POLICY", "P12": "P12_DOMAIN_AGE"}


def F(code, message=None, flag=None, link=None, **vars):
    w = weights()[code]
    return Finding(probe_id=PROBE_OF[code[:3]], code=code, family=w.family, weight=w.weight, decisive_flag=flag,
                   message=message or code, receipt=Receipt(kind="serp" if link else "rule", link=link), vars=vars)


def results(*findings, statuses=None):
    out = {}
    for f in findings:
        out.setdefault(f.probe_id, ProbeResult(probe_id=f.probe_id, status="ok")).findings.append(f)
    for pid, st in (statuses or {}).items():
        out[pid] = ProbeResult(probe_id=pid, status=st)
    return out


def g1_results():
    """08 §6.1 exactly."""
    return results(
        F("P01_OFFICIAL_FOUND"),
        F("P02_COMBOSQUAT", "The sender domain techmahindra-careers.in is not Tech Mahindra's. Tech Mahindra uses "
                            "techmahindra.com."),
        F("P04_NOTICE_FOUND", flag="P04_NOTICE_NO_FEE", org="Tech Mahindra"),
        F("P05_COMPLAINTS_GENERAL"),
        F("P11_CANDIDATE_PAYS", amount="₹2,000"),
        F("P11_PERSONAL_UPI", "You are asked to pay a personal UPI ID (te****@ybl) within 24 hours."),
        F("P11_URGENCY"),
        F("P11_NO_INTERVIEW"),
    )


def test_worked_example_exact():
    v = score(g1_results())
    assert v.score == 8.0
    assert v.family_scores == {"identity": 3.0, "process": 4.0, "reputation": 1.0, "artifact": 0.0, "existence": 0.0}
    assert v.decisive == ["D1_FEE_VS_NOTICE", "D3_LOOKALIKE_PLUS_FEE"]
    assert (v.tier, v.red_kind) == ("red", "impersonation")
    assert strength(v.score) == 0.62
    assert [r.code for r in v.reasons] == ["D1_FEE_VS_NOTICE", "D3_LOOKALIKE_PLUS_FEE", "P11_PERSONAL_UPI"]  # D-05
    assert [r.message for r in v.reasons] == [
        "Tech Mahindra's own recruitment fraud notice says it never charges candidates. This offer asks for ₹2,000.",
        "The sender domain techmahindra-careers.in is not Tech Mahindra's. Tech Mahindra uses techmahindra.com.",
        "You are asked to pay a personal UPI ID (te****@ybl) within 24 hours.",
    ]
    assert v.ruleset_version == "2026.10.1"


def test_determinism_100_runs():  # FR-35
    base = g1_results()
    first = score(base).model_dump()
    for seed in range(100):
        items = list(base.items())
        random.Random(seed).shuffle(items)                   # dict order must not matter
        assert score(dict(items)).model_dump() == first


def test_lookalike_quarter_rule():
    eff = effective_weights([F("P02_COMBOSQUAT"), F("P02_HOMOGLYPH"), F("P02_TLD_SWAP")])
    assert eff == [0.75, 3.5, 0.625]


def test_p06_probe_cap():
    eff = effective_weights([F("P06_ID_REPORTED", link=f"https://s{i}.com/x") for i in range(3)])
    assert round(sum(eff), 6) == 4.0


def test_family_caps():
    v = score(results(F("P03_DKIM_ALIGNED_OFFICIAL"), F("P02_SENDER_OFFICIAL")))
    assert v.family_scores["identity"] == -3.5


def test_d2_scheme():
    v = score(results(F("P11_SCHEME_OFF_PORTAL", scheme="PM Internship Scheme", portal="pminternship.mca.gov.in",
                        where="a form (forms.gle)"), F("P11_FORM_OR_SHORTLINK")))
    assert v.decisive == ["D2_SCHEME_IMPERSONATION"] and v.tier == "red" and v.red_kind == "impersonation"
    assert v.reasons[0].message == ("PM Internship Scheme runs only on pminternship.mca.gov.in and does not charge. "
                                    "This offer uses a form (forms.gle).")


def test_d4_needs_two_registrable_sources():
    one_site = results(F("P06_ID_REPORTED", link="https://a.example.com/1", identifier="x"),
                       F("P06_ID_REPORTED", link="https://b.example.com/2", identifier="x"))
    assert "D4_IDENTIFIER_REPORTED" not in score(one_site).decisive
    two = results(F("P06_ID_REPORTED", link="https://a.com/1", identifier="te****@ybl"),
                  F("P06_ID_REPORTED", link="https://b.in/2", identifier="te****@ybl"))
    v = score(two)
    assert v.decisive == ["D4_IDENTIFIER_REPORTED"] and "2 different websites" in v.reasons[0].message


def test_d1_needs_flag():
    v = score(results(F("P04_NOTICE_FOUND", org="X"), F("P11_CANDIDATE_PAYS", amount="₹1")))
    assert "D1_FEE_VS_NOTICE" not in v.decisive


def test_red_by_threshold_fee_risk():
    v = score(results(F("P11_CANDIDATE_PAYS"), F("P11_PERSONAL_UPI"), F("P01_OFFICIAL_FOUND")))
    assert (v.score, v.tier, v.red_kind, v.decisive) == (3.5, "red", "fee_risk", [])


def test_green_needs_anchor():  # FR-32 acceptance: S = -4 without an anchor is amber
    no_anchor = score(results(F("P07_ROLE_LISTED"), F("P08_OFFICE_MATCH"), F("P09_PHOTO_OFFICIAL"),
                              F("P06_ID_ON_OFFICIAL")))
    assert no_anchor.score <= -2.0 and no_anchor.tier == "amber"
    anchored = score(results(F("P03_DKIM_ALIGNED_OFFICIAL"), F("P07_ROLE_LISTED")))
    assert (anchored.score, anchored.tier) == (-4.0, "green")
    assert anchored.reasons[0].code == "P03_DKIM_ALIGNED_OFFICIAL"


def test_green_blocked_by_fee_and_strong_identity():
    fee = score(results(F("P03_DKIM_ALIGNED_OFFICIAL"), F("P02_SENDER_OFFICIAL"), F("P07_ROLE_LISTED"),
                        F("P08_OFFICE_MATCH"), F("P11_CANDIDATE_PAYS", amount="₹1")))
    assert fee.tier == "amber"
    sender_anchor = score(results(F("P02_SENDER_OFFICIAL"), F("P07_ROLE_LISTED"), F("P06_ID_ON_OFFICIAL")))
    assert sender_anchor.tier == "green"
    lookalike = score(results(F("P02_SENDER_OFFICIAL"), F("P07_ROLE_LISTED"), F("P03_DKIM_ALIGNED_OFFICIAL"),
                              F("P02_TLD_SWAP")))
    assert lookalike.tier == "amber"


def test_grey_low_coverage():
    r = results(F("P11_NO_INTERVIEW"), statuses={"P01_ENTITY": "error", "P04_FRAUD_NOTICE": "skipped_budget",
                                                   "P06_IDENTIFIER_TRACE": "timeout"})
    assert coverage(r) == pytest.approx(2 / 9) and score(r).tier == "grey"


def test_g4_amber():  # 14 §3: S = 2.8
    v = score(results(F("P01_NO_PRESENCE"), F("P02_FREEMAIL_NO_PRESENCE"), F("P11_NO_INTERVIEW")))
    assert (v.score, v.tier) == (2.8, "amber")


def test_coverage_rules():
    r = results(F("P11_NO_INTERVIEW"), statuses={"P03_HEADERS": "skipped_no_input", "P12_DOMAIN_AGE": "unsupported",
                                                   "P01_ENTITY": "ok", "P09_IMAGE": "skipped_replay_miss"})
    assert coverage(r) == pytest.approx(5 / 6.5)


def test_zero_weight_never_a_reason():
    v = score(results(F("P01_OFFICIAL_FOUND"), F("P11_NO_INTERVIEW")))
    assert [r.code for r in v.reasons] == ["P11_NO_INTERVIEW"]


# ---- ruleset and copy ------------------------------------------------------------------------------------------
TABLE_08 = {"P01_NO_PRESENCE": 1.0, "P02_HOMOGLYPH": 3.5, "P02_TLD_SWAP": 2.5, "P02_FREEMAIL_NO_PRESENCE": 0.8,
            "P03_DKIM_ALIGNED_OFFICIAL": -3.0, "P04_NOTICE_FOUND": 0.3, "P06_ID_ON_OFFICIAL": -1.5,
            "P07_COMPANY_LISTS_OTHER_ROLES": 0.2, "P08_REVIEWS_SCAM": 1.5, "P09_PHOTO_OTHER_NAMES": 2.5,
            "P10_PHRASE_OFFICIAL": -0.5, "P11_SCHEME_OFF_PORTAL": 3.0, "P11_CHAT_INTERVIEW": 0.7, "P12_NEW": 0.7}


def test_ruleset_valid_and_matches_08():
    validate_ruleset()
    assert len(weights()) == 46
    assert {k: weights()[k].weight for k in TABLE_08} == TABLE_08
    assert weights()["P08_REVIEWS_SCAM"].family == "reputation" and weights()["P08_NOT_FOUND"].family == "existence"


ALL_COPY = list(COPY.values()) + list(DECISIVE_COPY.values()) + list(RULE_COPY.values()) + \
    list(HEADLINES.values()) + list(SUBLINES.values())


@pytest.mark.parametrize("text", ALL_COPY)
def test_copy_rules(text):  # 09 §4
    assert not re.search(r"\b(scam|scammer|fraudster|fake company|safe|guaranteed)\b|100%", text, re.IGNORECASE)
    assert "—" not in text


def test_fraud_only_when_quoting_a_notice():
    assert [k for k, v in {**COPY, **DECISIVE_COPY}.items() if "fraud" in v.lower()] == \
        ["P04_NOTICE_FOUND", "D1_FEE_VS_NOTICE"]


def test_inr():
    assert [inr(2000), inr(150000), inr(499), inr(12345678)] == ["₹2,000", "₹1,50,000", "₹499", "₹1,23,45,678"]


def test_reasons_follow_verdict_direction():  # D-44: live G1 has P07/P08 at -1.0 tying PERSONAL_UPI
    r = g1_results()
    r["P07_ROLE"] = ProbeResult(probe_id="P07_ROLE", status="ok", findings=[F("P07_ROLE_LISTED")])
    r["P08_OFFICE"] = ProbeResult(probe_id="P08_OFFICE", status="ok", findings=[F("P08_OFFICE_MATCH")])
    v = score(r)
    assert v.score == 6.0 and [x.code for x in v.reasons] == ["D1_FEE_VS_NOTICE", "D3_LOOKALIKE_PLUS_FEE",
                                                              "P11_PERSONAL_UPI"]
    green = score(results(F("P03_DKIM_ALIGNED_OFFICIAL"), F("P07_ROLE_LISTED"), F("P05_COMPLAINTS_GENERAL")))
    assert green.tier == "green" and [x.code for x in green.reasons][:2] == ["P03_DKIM_ALIGNED_OFFICIAL",
                                                                             "P07_ROLE_LISTED"]


def test_amber_minor_headline():  # D-54
    from special26.scoring.nextsteps import headline
    contacts = [{"kind": "website", "value": "https://quantissphere.com", "finding_id": 1}]
    minor = headline("amber", None, "Quantis Sphere", contacts, [{"weight": 0.5, "effective_weight": 0.5}])
    assert minor[0] == "No serious warning signs, but this offer is not fully confirmed."
    assert "https://quantissphere.com" in minor[1]
    serious = headline("amber", None, "X", [], [{"weight": 1.5, "effective_weight": 1.5}])
    assert serious[0].startswith("Could not verify this offer.")
    assert headline("amber", None, "X", [])[0].startswith("Could not verify")          # no findings info: 09 copy
