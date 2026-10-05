"""P03_HEADERS: is the email authenticated? Local, .eml only (08 §4, D-39)."""
from pathlib import Path

from special26.claims.models import ClaimType as T
from special26.domains.classify import classify, reg
from special26.intake.eml import parse_eml
from special26.probes.base import Probe, ProbeContext, ProbeResult, rule_receipt
from special26.scoring.mask import mask_email


class P03Headers(Probe):
    id = "P03_HEADERS"
    depends_on = ("P01_ENTITY",)                 # DKIM alignment needs the official set (D-39)

    def _eml(self, ctx: ProbeContext) -> dict | None:
        if ctx.repo is None or ctx.check_id is None:
            return None
        a = next((a for a in ctx.repo.artifacts(ctx.check_id) if a["role"] == "eml" and a["storage_path"]), None)
        return parse_eml(Path(a["storage_path"]).read_bytes()) if a and Path(a["storage_path"]).is_file() else None

    def applicable(self, ctx: ProbeContext):
        return None if self._eml(ctx) else "skipped_no_input"

    async def run(self, ctx: ProbeContext) -> ProbeResult:
        e = self._eml(ctx)
        sender = ctx.claims.first(T.sender_email)
        own = not (sender and sender.value.get("from_headers"))     # From marked "this is mine" removes the claim
        if e["subject"].strip().lower().startswith(("fwd:", "fw:")) or own or not e["from_address"]:
            return self.result([]).model_copy(update={"status": "skipped_forwarded"})
        official, auth = set(ctx.official), e["auth"]
        header = (e["auth_results"][0] if e["auth_results"] else "")[:400]
        from_reg = reg(e["from_address"].split("@")[1])
        ids = [sender.id]
        f = []
        dkim = auth.get("dkim", {})
        d = (dkim.get("header.d") or dkim.get("header.i", "").lstrip("@").split("@")[-1]) or ""
        if dkim.get("result") == "pass" and d and reg(d) in official and from_reg in official:
            f.append(self.finding("P03_DKIM_ALIGNED_OFFICIAL", rule_receipt("P03_HEADERS", header=header), ids,
                                  org=ctx.claims.org_name or "the employer", domain=reg(d)))
        res = {k: auth.get(k, {}).get("result") for k in ("dkim", "spf", "dmarc")}
        if res["dmarc"] == "fail" or (res["dkim"] in ("fail", "none") and res["spf"] == "fail"):
            detail = ", ".join(f"{k.upper()} {v}" for k, v in res.items() if v)
            f.append(self.finding("P03_AUTH_FAIL", rule_receipt("P03_HEADERS", header=header), ids, detail=detail))
        if e["reply_to"]:
            r_reg = reg(e["reply_to"].split("@")[1])
            if r_reg != from_reg and classify(r_reg, official)[0] in ("freemail", "unrelated"):
                f.append(self.finding("P03_REPLY_DIVERTED", rule_receipt("P03_HEADERS", header=header), ids,
                                      reply=mask_email(e["reply_to"])))
        return self.result(f, {"auth": res})
