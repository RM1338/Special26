"""P08_OFFICE: is the office real? Google Maps, 1 call (08 §4, D-37)."""
from urllib.parse import quote_plus, urlparse

from rapidfuzz import fuzz

from special26 import seeds
from special26.claims.models import ClaimType as T
from special26.claims.regexes import has_scam_word
from special26.domains.classify import reg
from special26.probes.base import Probe, ProbeContext, ProbeResult, serp_receipt


def place_types(p: dict) -> list[str]:
    return [t for t in ([p.get("type")] + list(p.get("types") or [])) if t]


def has_type(p: dict, wanted: list[str]) -> str | None:
    for t in place_types(p):
        for w in wanted:
            if w.lower() == t.lower() or (len(w) > 3 and w.lower() in t.lower()):
                return t
    return None


def review_texts(p: dict) -> list[str]:
    """Only review text already in the search response (D-28)."""
    out = [p.get("user_review") or ""]
    ur = p.get("user_reviews") or {}
    for group in ("most_relevant", "summary"):
        out += [r.get("description") or r.get("snippet") or "" for r in ur.get(group, []) if isinstance(r, dict)]
    return [t for t in out if t]


def place_receipt(q: str, key: str, i: int, p: dict):
    link = (f"https://www.google.com/maps/search/?api=1&query={quote_plus(p.get('title', ''))}"
            f"&query_place_id={p['place_id']}") if p.get("place_id") else p.get("website")
    return serp_receipt("google_maps", q, key, {"position": i + 1, "title": p.get("title"), "link": link,
                                                "snippet": " · ".join(x for x in (p.get("address"), p.get("type")) if x)})


class P08Office(Probe):
    id = "P08_OFFICE"
    engine = "google_maps"
    depends_on = ("P01_ENTITY",)
    max_calls = 1
    timeout_s = 25.0

    def _query(self, ctx: ProbeContext) -> tuple[str, bool] | None:
        addr, org = ctx.claims.first(T.address), ctx.claims.org_name
        if addr:
            raw, city = addr.value.get("raw") or "", addr.value.get("city")
            if addr.value.get("pincode") or "," in raw:     # a street part or a PIN makes it an address
                return raw, True
            if org and city:                               # a bare city is not an address (D-37)
                return f"{org} office {city}", False
        return None

    def applicable(self, ctx: ProbeContext):
        return None if self._query(ctx) else "skipped_no_input"

    async def run(self, ctx: ProbeContext) -> ProbeResult:
        q, is_address = self._query(ctx)
        lex = seeds.lexicons()
        data, key = await self.search(ctx, {"engine": "google_maps", "type": "search", "q": q})
        places = [data["place_results"]] if data.get("place_results") else data.get("local_results", [])[:3]
        org = ctx.claims.org_name or ""
        official = set(ctx.official)
        ids = [c.id for c in (ctx.claims.first(T.address), ctx.claims.first(T.org)) if c]
        f = []
        if not places:
            if is_address:
                f.append(self.finding("P08_NOT_FOUND", serp_receipt("google_maps", q, key), ids))
            return self.result(f)
        match = next(((i, p) for i, p in enumerate(places) if org and fuzz.token_set_ratio(p.get("title", ""), org) >= 80
                      and (reg(urlparse(p.get("website") or "").netloc) in official or has_type(p, lex["office_types"]))),
                     None)
        if match:
            i, p = match
            f.append(self.finding("P08_OFFICE_MATCH", place_receipt(q, key, i, p), ids, org=org))
            if any(has_scam_word(t) for t in review_texts(p)):
                f.append(self.finding("P08_REVIEWS_SCAM", place_receipt(q, key, i, p), ids))
        top = places[0]
        if is_address and (t := has_type(top, lex["residential_types"])):
            f.append(self.finding("P08_RESIDENTIAL", place_receipt(q, key, 0, top), ids, place_type=t.lower()))
        if t := has_type(top, lex["coworking_types"]):
            f.append(self.finding("P08_COWORKING", place_receipt(q, key, 0, top), ids, place_type=t.lower()))
        return self.result(f, {"places": len(places)})
