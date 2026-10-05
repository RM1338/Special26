"""P10_TEMPLATE: has this wording been seen in scams? Local MinHash + Google, 1 call (08 §4, §7)."""
from urllib.parse import urlparse

from special26.claims.models import ClaimType as T
from special26.claims.regexes import has_scam_word
from special26.domains.classify import reg
from special26.errors import BudgetExhausted, ReplayMiss, UpstreamError
from special26.probes.base import Probe, ProbeContext, ProbeResult, Receipt, serp_receipt
from special26.storage.retention import seed_provenance
from special26.template.minhash import signature
from special26.template.normalize import tokens
from special26.template.phrase import distinctive_sentence

HIGH, MED = 0.6, 0.4


class P10Template(Probe):
    id = "P10_TEMPLATE"
    engine = "google"
    depends_on = ("P01_ENTITY",)                 # PHRASE_OFFICIAL needs the official set (D-03)
    max_calls = 1
    timeout_s = 25.0

    def applicable(self, ctx: ProbeContext):
        text = ctx.redacted_text
        if not text or (len(tokens(text, ctx.claims)) < 30 and not distinctive_sentence(text, ctx.claims)):
            return "skipped_no_input"
        return None

    async def run(self, ctx: ProbeContext) -> ProbeResult:
        text, f, out = ctx.redacted_text, [], {}
        ids = [c.id for c in ctx.claims.all(T.org)][:1]
        sig = signature(tokens(text, ctx.claims))
        if sig and ctx.repo is not None:                                    # local part (skipped under 30 tokens)
            best = next(iter(ctx.repo.template_candidates(sig, label="scam", exclude=ctx.check_id)), None)
            if best and best["jaccard"] >= MED:
                seed = best["check_id"].startswith("seed:")
                constructed = seed and seed_provenance(best["check_id"]) == "constructed"
                title = ("Matches a fake offer pattern described in a public report" if constructed
                         else "Known fake offer text" if seed else "An earlier check marked high risk")   # D-47
                receipt = Receipt(kind="local_memory", title=title, link=best["source_url"] if seed else None,
                                  extra={"similarity": round(best["jaccard"], 2), "provenance":
                                         seed_provenance(best["check_id"]) if seed else "earlier_check",
                                         "template": best["check_id"] if seed else None})
                code = "P10_TEMPLATE_MATCH_HIGH" if best["jaccard"] >= HIGH else "P10_TEMPLATE_MATCH_MED"
                f.append(self.finding(code, receipt, ids))   # no percentage in reasons (09 §4)
                out["template_jaccard"] = round(best["jaccard"], 3)
        sentence = distinctive_sentence(text, ctx.claims)
        status = "ok"
        if sentence:
            q = f'"{sentence}"'
            try:
                data, key = await self.search(ctx, {"engine": "google", "q": q, "num": 10})
            except (ReplayMiss, BudgetExhausted, UpstreamError) as e:      # keep the local match (D-48)
                status = {ReplayMiss: "skipped_replay_miss", BudgetExhausted: "skipped_budget"}.get(type(e), "error")
                return self.result(f, out).model_copy(update={"status": status})
            results = data.get("organic_results", [])
            official = set(ctx.official)
            rep = next((r for r in results if has_scam_word(f"{r.get('title', '')} {r.get('snippet', '')}")), None)
            if rep:
                f.append(self.finding("P10_PHRASE_REPORTED", serp_receipt("google", q, key, rep), ids,
                                      source=reg(urlparse(rep.get("link", "")).netloc)))
            off = next((r for r in results if reg(urlparse(r.get("link", "")).netloc) in official), None)
            if off:
                f.append(self.finding("P10_PHRASE_OFFICIAL", serp_receipt("google", q, key, off), ids,
                                      org=ctx.claims.org_name or "the employer"))
            out["sentence"] = sentence
        return self.result(f, out)
