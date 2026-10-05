"""P01_ENTITY: who is the real employer? Google Search, 1 to 2 calls (08 §4)."""
import re
from urllib.parse import urlparse

from rapidfuzz import fuzz

from special26 import seeds
from special26.claims.models import ClaimType as T
from special26.domains.classify import label, reg
from special26.errors import BudgetExhausted, ReplayMiss, UpstreamError
from special26.probes.base import Probe, ProbeContext, ProbeResult, Receipt, serp_receipt

LEGAL = re.compile(r"\b(private limited|pvt\.?\s?ltd\.?|limited|ltd\.?|llp|inc\.?|technologies|solutions|services)\b")


def squash(org: str) -> str:
    return re.sub(r"[^a-z0-9]", "", LEGAL.sub("", org.lower()))


def name_sim(c: str, org: str) -> float:
    return fuzz.partial_ratio(label(c).replace("-", ""), squash(org)) / 100


def candidates(data: dict, org: str) -> list[dict]:
    """Score every registrable domain seen in the knowledge graph and organic results (08 §4 P01)."""
    agg = set(seeds.lines("aggregator_domains.txt"))
    kg_site = (data.get("knowledge_graph") or {}).get("website")
    kg = reg(urlparse(kg_site).netloc or kg_site) if kg_site else None
    scores: dict[str, float] = {}
    if kg and kg not in agg:
        scores[kg] = 3.0
    for r in data.get("organic_results", []):
        c = reg(urlparse(r.get("link", "")).netloc)
        if c and c not in agg and r.get("position"):
            scores[c] = scores.get(c, 0.0) + 1 / r["position"]
    out = []
    for c, s in scores.items():
        sim = name_sim(c, org)
        total = s + 2.0 * sim
        accepted = c == kg or (total >= 2.0 and sim >= 0.6)
        out.append({"domain": c, "score": round(total, 2), "name_sim": round(sim, 2), "kg": c == kg,
                    "accepted": accepted})
    return sorted(out, key=lambda x: (-x["score"], x["domain"]))


def domain_receipt(data: dict, q: str, key: str, domain: str) -> dict:
    kg = data.get("knowledge_graph") or {}
    if kg.get("website") and reg(urlparse(kg["website"]).netloc) == domain:
        return serp_receipt("google", q, key, {"title": f"{kg.get('title', domain)} (knowledge graph)",
                                               "link": kg["website"]}, source="knowledge_graph.website").model_dump()
    r = next((r for r in data.get("organic_results", []) if reg(urlparse(r.get("link", "")).netloc) == domain), None)
    return serp_receipt("google", q, key, r).model_dump()


class P01Entity(Probe):
    id = "P01_ENTITY"
    engine = "google"
    max_calls = 2
    timeout_s = 45.0          # two sequential calls (D-34)

    def applicable(self, ctx: ProbeContext):
        return None if ctx.claims.org_name else "skipped_no_input"

    async def run(self, ctx: ProbeContext) -> ProbeResult:
        org_claim = ctx.claims.first(T.org)
        org = org_claim.value["name"]
        entity = next((e for e in seeds.entities() if e["entity_id"] == org_claim.value.get("entity_id")), None)
        seed_domains = [reg(d) for d in entity["official_domains"]] if entity else []

        q = f'"{org}"'
        status = "ok"
        try:
            data, key = await self.search(ctx, {"engine": "google", "q": q, "num": 10})
        except (ReplayMiss, BudgetExhausted, UpstreamError) as e:
            if not seed_domains:
                raise
            # D-48: search unavailable, but a verified seed still gives the official set; status records the failure
            status = {ReplayMiss: "skipped_replay_miss", BudgetExhausted: "skipped_budget"}.get(type(e), "error")
            data, key = {}, None
        cands = candidates(data, org)
        accepted = [c["domain"] for c in cands if c["accepted"]][:3]
        if not accepted and not seed_domains:                   # Q2 only when nothing is known yet (D-32)
            q = f'"{org}" careers'
            data, key = await self.search(ctx, {"engine": "google", "q": q, "num": 10})
            cands = candidates(data, org)
            accepted = [c["domain"] for c in cands if c["accepted"]][:3]
        official = list(dict.fromkeys(accepted + seed_domains))

        receipts = {d: domain_receipt(data, q, key, d) for d in accepted}
        for d in seed_domains:
            receipts.setdefault(d, {"kind": "rule", "rule_id": "known_entities", "link": entity.get("source_url"),
                                    "title": f"{entity['name']} official domain (verified seed)",
                                    "extra": {"verified_on": entity.get("verified_on")}})
        contacts = []
        kg = data.get("knowledge_graph") or {}
        for r in data.get("organic_results", []):
            u = urlparse(r.get("link", ""))
            on_official = reg(u.netloc) in official
            careers_like = re.search(r"/(careers|jobs)\b", u.path, re.IGNORECASE) or u.netloc.split(".")[0] in ("careers", "jobs")
            if on_official and careers_like:
                contacts.append({"kind": "careers_url", "value": r["link"],
                                 "receipt": serp_receipt("google", q, key, r).model_dump()})
                break
        if kg.get("phone") and official:
            contacts.append({"kind": "phone", "value": kg["phone"],
                             "receipt": serp_receipt("google", q, key, {"title": f"{kg.get('title', org)} "
                                                     "(knowledge graph)"}, source="knowledge_graph.phone").model_dump()})

        claim_ids = [org_claim.id]
        if official:
            first = official[0]
            f = self.finding("P01_OFFICIAL_FOUND", receipt=Receipt(**receipts[first]), claim_ids=claim_ids,
                             org=org, official=first)
        else:
            f = self.finding("P01_NO_PRESENCE", receipt=serp_receipt("google", q, key), claim_ids=claim_ids, org=org)
        out = self.result([f], {"official_domains": official, "candidates": cands[:5], "receipts": receipts,
                                "official_contacts": contacts})
        return out.model_copy(update={"status": status})

