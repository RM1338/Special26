"""P02_SENDER: is the sender the employer? Local, uses P01 (and P03 for reply-to) (08 §4)."""
from special26.claims.models import ClaimType as T
from special26.domains.classify import classify, reg
from special26.probes.base import Probe, ProbeContext, ProbeResult, Receipt, rule_receipt
from special26.scoring.mask import mask_email

LOOKALIKE = {"homoglyph": "P02_HOMOGLYPH", "typosquat": "P02_TYPOSQUAT", "combosquat": "P02_COMBOSQUAT",
             "tld_swap": "P02_TLD_SWAP"}


class P02Sender(Probe):
    id = "P02_SENDER"
    depends_on = ("P01_ENTITY", "P03_HEADERS")

    def _inputs(self, ctx: ProbeContext):
        out = []
        if s := ctx.claims.first(T.sender_email):
            out.append(("sender domain", s.value["address"].split("@")[1], s))
        if r := ctx.claims.first(T.reply_to):
            out.append(("reply-to domain", r.value["address"].split("@")[1], r))
        for u in ctx.claims.all(T.url):
            if u.value.get("kind") in ("other", "document") and u.value.get("host"):
                out.append(("link domain", u.value["host"], u))
        return out

    def applicable(self, ctx: ProbeContext):
        return None if self._inputs(ctx) else "skipped_no_input"

    async def run(self, ctx: ProbeContext) -> ProbeResult:
        official = set(ctx.official)
        p01 = ctx.upstream.get("P01_ENTITY")
        receipts = p01.outputs.get("receipts", {}) if p01 else {}
        org = ctx.claims.org_name or "the claimed employer"

        def receipt_for(o):
            return Receipt(**receipts[o]) if o in receipts else rule_receipt("P02_SENDER")

        findings, seen = [], set()
        classes = {}
        for what, domain, claim in self._inputs(ctx):
            cls, matched = classify(domain, official)
            classes[claim.id] = cls
            code = LOOKALIKE.get(cls)
            if code and code not in seen:
                seen.add(code)
                findings.append(self.finding(code, receipt_for(matched), [claim.id], what=what, domain=reg(domain),
                                             org=org, official=matched))

        sender = ctx.claims.first(T.sender_email)
        if sender:
            cls = classes[sender.id]
            domain = sender.value["address"].split("@")[1]
            first = ctx.official[0] if ctx.official else None
            if cls in ("official", "official_subdomain"):
                findings.append(self.finding("P02_SENDER_OFFICIAL", receipt_for(reg(domain)), [sender.id], org=org,
                                             domain=reg(domain)))
            elif cls == "freemail" and official:
                findings.append(self.finding("P02_FREEMAIL", receipt_for(first), [sender.id], provider=reg(domain),
                                             org=org, official=first))
            elif cls == "freemail":
                findings.append(self.finding("P02_FREEMAIL_NO_PRESENCE", rule_receipt("P02_SENDER"), [sender.id],
                                             provider=reg(domain), org=org))
            elif cls == "unrelated":
                findings.append(self.finding("P02_UNRELATED", rule_receipt("P02_SENDER"), [sender.id],
                                             domain=reg(domain), org=org))

        reply = ctx.claims.first(T.reply_to)
        p03 = ctx.upstream.get("P03_HEADERS")
        p03_diverted = p03 and any(f.code == "P03_REPLY_DIVERTED" for f in p03.findings)
        if sender and reply and not p03_diverted:          # P03_REPLY_DIVERTED replaces it, never both
            r_dom = reply.value["address"].split("@")[1]
            if reg(r_dom) != reg(sender.value["address"].split("@")[1]) and classes[reply.id] in ("freemail",
                                                                                                    "unrelated"):
                findings.append(self.finding("P02_REPLY_DIVERTED", rule_receipt("P02_SENDER"), [reply.id, sender.id],
                                             reply=mask_email(reply.value["address"])))
        return self.result(findings, {"classes": classes})
