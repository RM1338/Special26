"""Official contacts, next steps, headline and sub line (09 S4, S6; D-08, D-17). FR-41."""
from special26.claims.models import ClaimSet
from special26.claims.models import ClaimType as T
from special26.probes.base import ProbeResult
from special26.scoring.copy import HEADLINES, SUBLINES


def official_contacts(results: dict[str, ProbeResult]) -> list[dict]:
    """Only from P01/P04 receipts, never from the offer itself (09 S6)."""
    out = []
    p01 = results.get("P01_ENTITY")
    if p01 and p01.findings and p01.findings[0].code == "P01_OFFICIAL_FOUND":
        fid = p01.findings[0].id
        out += [{"kind": c["kind"], "value": c["value"], "finding_id": fid} for c in p01.outputs.get("official_contacts", [])]
        hosts = p01.outputs.get("official_hosts") or p01.outputs.get("official_domains")
        if not any(c["kind"] == "careers_url" for c in out) and hosts:          # G2: pminternship.mca.gov.in
            out.append({"kind": "website", "value": f"https://{hosts[0]}", "finding_id": fid})
    p04 = results.get("P04_FRAUD_NOTICE")
    if p04 and p04.findings and p04.findings[0].receipt.link:
        out.append({"kind": "fraud_notice", "value": p04.findings[0].receipt.link, "finding_id": p04.findings[0].id})
    return out


def next_steps(tier: str, claims: ClaimSet, contacts: list[dict]) -> list[str]:
    steps = []
    if tier in ("red", "amber", "grey"):
        steps.append("do_not_pay")
    if contacts:
        steps.append("verify_official")
    if tier in ("red", "amber"):
        steps.append("call_1930")
    if tier == "red":
        steps.append("report_cybercrime")
        if any(c.value.get("role") != "recipient" for c in claims.all(T.phone)):
            steps.append("report_chakshu")
    if tier in ("red", "amber"):
        steps.append("tell_placement_cell")
    return steps


def _contact_text(contacts: list[dict]) -> str:
    c = next((c for c in contacts if c["kind"] in ("careers_url", "website")), None)
    return c["value"] if c else "the company's official website"


def headline(tier: str, red_kind: str | None, org: str | None, contacts: list[dict]) -> tuple[str, str]:
    key = (tier, red_kind if tier == "red" else None)
    vars_ = {"org": org or "the employer", "official_contact": _contact_text(contacts)}
    return HEADLINES[key].format(**vars_), SUBLINES[key].format(**vars_)
