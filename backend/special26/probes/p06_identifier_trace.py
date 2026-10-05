"""P06_IDENTIFIER_TRACE: has this UPI ID, phone or domain been reported? Google 1 to 2 calls + local memory (08 §4)."""
import re
from urllib.parse import urlparse

from special26.campaign.identifiers import display, hard_identifiers
from special26.claims.regexes import has_scam_word
from special26.domains.classify import reg
from special26.errors import BudgetExhausted, ReplayMiss, UpstreamError
from special26.probes.base import Probe, ProbeContext, ProbeResult, Receipt, serp_receipt

PER_CALL, MAX_CALLS = 4, 2


def present(kind: str, value: str, text: str) -> bool:
    if kind == "phone":
        return value in re.sub(r"\D", "", text)
    return value.lower() in text.lower()


class P06IdentifierTrace(Probe):
    id = "P06_IDENTIFIER_TRACE"
    engine = "google"
    depends_on = ("P01_ENTITY",)                 # domain classes need the official set (D-03)
    max_calls = 2
    timeout_s = 30.0

    def _ids(self, ctx: ProbeContext) -> list[dict]:
        return hard_identifiers(ctx.claims, set(ctx.official))

    def applicable(self, ctx: ProbeContext):
        return None if self._ids(ctx) else "skipped_no_input"

    async def run(self, ctx: ProbeContext) -> ProbeResult:
        ids = self._ids(ctx)
        f, status = [], "ok"
        try:
            await self._search(ctx, ids, f)
        except (ReplayMiss, BudgetExhausted, UpstreamError) as e:      # keep local memory evidence (D-41)
            status = {ReplayMiss: "skipped_replay_miss", BudgetExhausted: "skipped_budget"}.get(type(e), "error")
        self._local(ctx, ids, f)
        out = self.result(f, {"identifiers": [{"kind": i["kind"], "domain_class": i["domain_class"]} for i in ids]})
        return out.model_copy(update={"status": status})

    async def _search(self, ctx: ProbeContext, ids: list[dict], f: list) -> None:
        official, reported_sources, on_official = set(ctx.official), set(), set()
        for n in range(min(MAX_CALLS, -(-len(ids) // PER_CALL))):
            batch = ids[n * PER_CALL:(n + 1) * PER_CALL]
            q = " OR ".join(f'"{i["value"]}"' for i in batch)
            data, key = await self.search(ctx, {"engine": "google", "q": q, "num": 10})
            for r in data.get("organic_results", []):
                text = f"{r.get('title', '')} {r.get('snippet', '')} {r.get('link', '')}"
                src = reg(urlparse(r.get("link", "")).netloc)
                for i in batch:
                    if not present(i["kind"], i["value"], text):
                        continue
                    if src in official and i["kind"] in ("phone", "email") and i["value"] not in on_official:
                        on_official.add(i["value"])
                        f.append(self.finding("P06_ID_ON_OFFICIAL", serp_receipt("google", q, key, r), [i["claim_id"]],
                                              identifier=display(i["kind"], i["value"]), org=ctx.claims.org_name or
                                              "the employer"))
                    elif src not in official and src not in reported_sources \
                            and has_scam_word(f"{r.get('title', '')} {r.get('snippet', '')}"):
                        reported_sources.add(src)                     # one finding per distinct source domain
                        f.append(self.finding("P06_ID_REPORTED", serp_receipt("google", q, key, r), [i["claim_id"]],
                                              identifier=display(i["kind"], i["value"]), source=src))

    def _local(self, ctx: ProbeContext, ids: list[dict], f: list) -> None:
        if ctx.repo is not None:                                         # local memory of earlier red checks
            for i in ids:
                earlier = ctx.repo.checks_with_identifier(i["kind"], i["value"], tiers=("red",), exclude=ctx.check_id)
                if earlier:
                    camp = next((c for c in (ctx.repo.campaign_of(e) for e in earlier) if c), None)
                    f.append(self.finding("P06_ID_SEEN_LOCALLY", Receipt(
                        kind="local_memory", title="Earlier checks on Special26",
                        link=f"/campaign/{camp}" if camp else None,
                        extra={"count": len(earlier), "campaign_id": camp, "kind": i["kind"]}),
                        [i["claim_id"]], identifier=display(i["kind"], i["value"]),
                        count_text=f"{len(earlier)} earlier check{'s' if len(earlier) > 1 else ''}"))
