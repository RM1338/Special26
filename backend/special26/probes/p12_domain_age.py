"""P12_DOMAIN_AGE: how new is the domain? RDAP, optional, no SerpApi credits (08 §4, D-11, D-45). FR-21."""
from datetime import datetime

from special26.claims.models import ClaimType as T
from special26.domains.classify import classify, reg
from special26.probes.base import Probe, ProbeContext, ProbeResult, Receipt

SUSPECT = {"typosquat", "combosquat", "tld_swap", "homoglyph", "unrelated"}
MAX_DOMAINS = 3


def registered_on(rdap: dict) -> datetime | None:
    for e in rdap.get("events", []):
        if e.get("eventAction") == "registration" and e.get("eventDate"):
            return datetime.fromisoformat(e["eventDate"])
    return None


class P12DomainAge(Probe):
    id = "P12_DOMAIN_AGE"
    depends_on = ("P01_ENTITY",)                 # domain class needs the official set (D-03)

    def _domains(self, ctx: ProbeContext) -> list[tuple[str, str]]:
        official, out = set(ctx.official), {}
        inputs = [(c.value["address"].split("@")[-1], c.id) for t in (T.sender_email, T.reply_to)
                  for c in ctx.claims.all(t)]
        inputs += [(c.value["host"], c.id) for c in ctx.claims.all(T.url)
                   if c.value.get("kind") in ("other", "document") and c.value.get("host")]
        for d, cid in inputs:
            if classify(d, official)[0] in SUSPECT:
                out.setdefault(reg(d), cid)
        return list(out.items())[:MAX_DOMAINS]

    def applicable(self, ctx: ProbeContext):
        return None if self._domains(ctx) else "skipped_no_input"

    async def run(self, ctx: ProbeContext) -> ProbeResult:
        ages = []
        for d, cid in self._domains(ctx):
            rdap = await ctx.serp.rdap(d)
            when = registered_on(rdap) if rdap else None      # None: no registration data (unregistered demo domain)
            if when:
                ages.append(((ctx.created_at - when).days, d, cid, when))
        out = {"domains": [{"domain": d, "age_days": a} for a, d, _, _ in ages]}
        if not ages:
            return self.result([], out)
        days, d, cid, when = min(ages)
        code = "P12_VERY_NEW" if days < 90 else "P12_NEW" if days < 365 else None
        if not code:
            return self.result([], out)
        receipt = Receipt(kind="rdap", title=f"RDAP registration record for {d}", link=f"https://rdap.org/domain/{d}",
                          snippet=f"Registered on {when.date().isoformat()}")
        return self.result([self.finding(code, receipt, [cid], domain=d, days=max(days, 0))], out)
