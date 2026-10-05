"""Scorer: family caps -> decisive rules -> tiers -> reasons + coverage (08 §5, §6). Pure. FR-30 to FR-36."""
from urllib.parse import urlparse

from pydantic import BaseModel

from special26.domains.classify import reg
from special26.probes.base import Finding, ProbeResult, code_order, rules
from special26.scoring.copy import DECISIVE_COPY, render

FAMILY_CAPS = {"identity": (-3.5, 4.0), "process": (0.0, 4.0), "reputation": (-1.5, 4.0),
               "artifact": (-1.5, 4.0), "existence": (-2.0, 2.0)}
COVERAGE_W = {"P01_ENTITY": 3, "P02_SENDER": 2, "P03_HEADERS": 1, "P04_FRAUD_NOTICE": 2, "P05_CHATTER": 1,
              "P06_IDENTIFIER_TRACE": 2, "P07_ROLE": 1, "P08_OFFICE": 1, "P09_IMAGE": 1.5, "P10_TEMPLATE": 1,
              "P11_POLICY": 2, "P12_DOMAIN_AGE": 0.5}
LOOKALIKE = ("P02_HOMOGLYPH", "P02_TYPOSQUAT", "P02_COMBOSQUAT", "P02_TLD_SWAP")
P06_CAP = 4.0
RED_AT, GREEN_AT, GREY_COVERAGE = 3.0, -2.0, 0.40      # thresholds: the only values tunable on dev (11 §2.3)
GREEN_SUPPORT = {"P07_ROLE_LISTED", "P08_OFFICE_MATCH", "P09_PHOTO_OFFICIAL"}


class Reason(BaseModel):
    rank: int
    code: str
    message: str
    finding_ids: list[int]


class Verdict(BaseModel):
    tier: str
    red_kind: str | None
    score: float
    family_scores: dict[str, float]
    decisive: list[str]
    coverage: float
    reasons: list[Reason]
    effective: list[float]          # per finding, same order as the flat findings list (findings.effective_weight)
    ruleset_version: str


def flatten(results: dict[str, ProbeResult]) -> list[Finding]:
    """Deterministic order: probes by id, findings in emission order."""
    return [f for pid in sorted(results) for f in results[pid].findings]


def effective_weights(findings: list[Finding]) -> list[float]:
    """0.25x for all but the largest lookalike code; P06_ID_REPORTED scaled to its +4.0 probe cap."""
    looks = sorted((f for f in findings if f.code in LOOKALIKE), key=lambda f: (-f.weight, LOOKALIKE.index(f.code)))
    keep = looks[0].code if looks else None
    eff = [f.weight * (0.25 if f.code in LOOKALIKE and f.code != keep else 1.0) for f in findings]
    rep = [i for i, f in enumerate(findings) if f.code == "P06_ID_REPORTED"]
    total = sum(eff[i] for i in rep)
    if total > P06_CAP:
        for i in rep:
            eff[i] *= P06_CAP / total
    return eff


def coverage(results: dict[str, ProbeResult]) -> float:
    applicable = covered = 0.0
    for pid, r in results.items():
        if r.status in ("skipped_no_input", "unsupported"):
            continue
        applicable += COVERAGE_W.get(pid, 0)
        covered += COVERAGE_W.get(pid, 0) if r.status == "ok" else 0
    return covered / applicable if applicable else 0.0


def score(results: dict[str, ProbeResult]) -> Verdict:
    findings = flatten(results)
    fid = [f.id if f.id is not None else i for i, f in enumerate(findings)]
    eff = effective_weights(findings)

    fam = {k: 0.0 for k in FAMILY_CAPS}
    for f, w in zip(findings, eff):
        fam[f.family] += w
    fam = {k: round(min(max(v, FAMILY_CAPS[k][0]), FAMILY_CAPS[k][1]), 4) for k, v in fam.items()}
    S = round(sum(fam.values()), 4)

    by_code: dict[str, list[int]] = {}
    for i, f in enumerate(findings):
        by_code.setdefault(f.code, []).append(i)
    codes = set(by_code)
    flagged = [i for i, f in enumerate(findings) if f.decisive_flag == "P04_NOTICE_NO_FEE"]

    decisive: list[tuple[str, list[int], str]] = []          # (rule, finding indexes, message)
    pays = by_code.get("P11_CANDIDATE_PAYS", [])
    if pays and flagged:
        n, p = findings[flagged[0]], findings[pays[0]]
        decisive.append(("D1_FEE_VS_NOTICE", [flagged[0], pays[0]],
                         render(DECISIVE_COPY["D1_FEE_VS_NOTICE"], org=n.vars["org"], amount=p.vars["amount"])))
    off = by_code.get("P11_SCHEME_OFF_PORTAL", [])
    form = by_code.get("P11_FORM_OR_SHORTLINK", [])
    if off and (pays or form):
        o = findings[off[0]]
        ask = f" and asks for {findings[pays[0]].vars['amount']}" if pays else ""
        decisive.append(("D2_SCHEME_IMPERSONATION", [off[0], *(pays[:1] or form[:1])],
                         render(DECISIVE_COPY["D2_SCHEME_IMPERSONATION"], scheme=o.vars["scheme"],
                                portal=o.vars["portal"], where=o.vars["where"], ask=ask)))
    looks = [i for c in LOOKALIKE for i in by_code.get(c, [])]
    if looks and pays:
        top = max(looks, key=lambda i: (eff[i], -LOOKALIKE.index(findings[i].code)))
        decisive.append(("D3_LOOKALIKE_PLUS_FEE", [top, pays[0]],
                         render(DECISIVE_COPY["D3_LOOKALIKE_PLUS_FEE"], lookalike_message=findings[top].message)))
    reported = by_code.get("P06_ID_REPORTED", [])
    sources = {reg(urlparse(findings[i].receipt.link or "").netloc) for i in reported} - {""}
    if len(sources) >= 2:                                        # D-22: registrable source domains
        decisive.append(("D4_IDENTIFIER_REPORTED", reported,
                         render(DECISIVE_COPY["D4_IDENTIFIER_REPORTED"],
                                identifier=findings[reported[0]].vars["identifier"], n=len(sources))))

    cov = coverage(results)
    green_anchor = "P03_DKIM_ALIGNED_OFFICIAL" in codes or ("P02_SENDER_OFFICIAL" in codes and GREEN_SUPPORT & codes)
    strong_identity = any(f.family == "identity" and f.weight >= 2.5 for f in findings)
    if decisive:
        tier = "red"
    elif cov < GREY_COVERAGE and S < RED_AT:
        tier = "grey"
    elif S >= RED_AT:
        tier = "red"
    elif S <= GREEN_AT and not pays and not strong_identity and green_anchor:
        tier = "green"
    else:
        tier = "amber"
    red_kind = None
    if tier == "red":
        red_kind = "impersonation" if (decisive or fam["identity"] >= 2.5 or fam["artifact"] >= 2.5) else "fee_risk"

    # Reasons: decisive first; then remaining findings by |effective| desc, probe_id, 08 table order (D-05)
    reasons = [Reason(rank=0, code=r, message=m, finding_ids=[fid[i] for i in idx]) for r, idx, m in decisive]
    used = {i for _, idx, _ in decisive for i in idx}
    order = code_order()
    # D-44: "Why" first lists evidence pointing the verdict's way (red/amber: toward fraud; green: toward genuine)
    sign = {"red": 1, "amber": 1, "green": -1}.get(tier, 0)
    rest = sorted((i for i, f in enumerate(findings) if i not in used and eff[i] != 0),
                  key=lambda i: (sign != 0 and (eff[i] > 0) != (sign > 0), -abs(eff[i]), findings[i].probe_id,
                                 order[findings[i].code]))
    reasons += [Reason(rank=0, code=findings[i].code, message=findings[i].message, finding_ids=[fid[i]]) for i in rest]
    reasons = [r.model_copy(update={"rank": n}) for n, r in enumerate(reasons[:3], 1)]

    return Verdict(tier=tier, red_kind=red_kind, score=S, family_scores=fam, decisive=[d[0] for d in decisive],
                   coverage=round(cov, 3), reasons=reasons, effective=[round(w, 4) for w in eff],
                   ruleset_version=rules()["ruleset_version"])


def strength(score: float) -> float:
    return round(min(max((score + 8.5) / 26.5, 0.0), 1.0), 2)
