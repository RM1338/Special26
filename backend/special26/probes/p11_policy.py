"""P11_POLICY: does the process break known rules? Local (08 §4)."""
import re

from special26 import seeds
from special26.claims import amounts
from special26.claims.models import ClaimType as T
from special26.domains.classify import reg
from special26.probes.base import Probe, ProbeContext, ProbeResult, rule_receipt
from special26.scoring.copy import inr
from special26.scoring.mask import mask_upi

PURPOSE_WORDS = {"verification": "verification", "deposit": "a deposit", "equipment": "a kit or equipment",
                 "training": "training", "registration": "registration", "document": "documents",
                 "other_fee": "a fee", None: "a fee"}
KIND_WORDS = {"form": "form", "shortener": "short link", "messaging": "chat link"}
SCAN_QR = re.compile(r"\bscan (?:the |this |our )?qr\b", re.IGNORECASE)
REFUNDABLE = re.compile(r"(?<!non-)(?<!non )\brefundable\b", re.IGNORECASE)      # D-23


def is_gov(domain: str) -> bool:
    return domain.endswith((".gov.in", ".nic.in"))


class P11Policy(Probe):
    id = "P11_POLICY"

    def applicable(self, ctx: ProbeContext):
        return None if ctx.claims.claims else "skipped_no_input"

    async def run(self, ctx: ProbeContext) -> ProbeResult:
        c, f, text = ctx.claims, [], ctx.redacted_text
        deadline = c.first(T.deadline)
        hours = deadline.value["hours"] if deadline else None
        by_deadline = f" within {hours} hours" if hours else ""

        pays = [a for a in c.all(T.amount) if a.value.get("payer") == "candidate"]
        if pays:
            a = pays[0]
            f.append(self.finding("P11_CANDIDATE_PAYS", rule_receipt("P11_CANDIDATE_PAYS"), [a.id],
                                  amount=inr(a.value["value_inr"]), purpose=PURPOSE_WORDS.get(a.value.get("purpose"),
                                                                                              "a fee")))
            win = amounts.window(text, *a.span) if text and a.span else a.raw.lower()
            if a.value.get("purpose") == "deposit" or REFUNDABLE.search(win):
                f.append(self.finding("P11_REFUNDABLE_BAIT", rule_receipt("P11_REFUNDABLE_BAIT"), [a.id]))

        upi = c.first(T.upi_id)
        pay_url = next((u for u in c.all(T.url) if u.value.get("kind") == "payment"), None)
        if upi or pay_url or SCAN_QR.search(text):
            target = (f"a personal UPI ID ({mask_upi(upi.value['vpa'])})" if upi else
                      f"through a payment link ({pay_url.value.get('host') or 'UPI'})" if pay_url else
                      "by scanning a QR code")
            ids = [x.id for x in (upi, pay_url) if x]
            f.append(self.finding("P11_PERSONAL_UPI", rule_receipt("P11_PERSONAL_UPI"), ids, target=target,
                                  deadline=by_deadline))

        scheme = c.first(T.scheme)
        if scheme:
            ent = next(e for e in seeds.entities() if e.get("scheme_key") == scheme.value["scheme_key"])
            allowed = {reg(d) for d in ent["official_domains"]} | set(ent["official_domains"])
            sender = c.first(T.sender_email)
            places = ([(sender.value["address"].split("@")[1], f"the email address {sender.value['address']}", sender)]
                      if sender else [])
            places += [(u.value["host"], (f"{'a form' if u.value['kind'] == 'form' else 'a link'} "
                        f"({u.value['host']})"), u) for u in c.all(T.url) if u.value.get("host")]
            off = [(d, desc, cl) for d, desc, cl in places
                   if not (is_gov(d) or d in allowed or reg(d) in allowed)]
            if off:
                f.append(self.finding("P11_SCHEME_OFF_PORTAL", rule_receipt("P11_SCHEME_OFF_PORTAL"),
                                      [scheme.id, off[0][2].id], scheme=ent["name"], portal=ent["official_domains"][0],
                                      where=off[0][1]))

        link = next((u for u in c.all(T.url) if u.value.get("kind") in KIND_WORDS), None)
        if link:
            f.append(self.finding("P11_FORM_OR_SHORTLINK", rule_receipt("P11_FORM_OR_SHORTLINK"), [link.id],
                                  kind=KIND_WORDS[link.value["kind"]], host=link.value.get("host")))

        proc = c.first(T.process)
        flags = c.process
        if flags.get("urgent"):
            f.append(self.finding("P11_URGENCY", rule_receipt("P11_URGENCY"), [proc.id],
                                  when=f"within {hours} hours" if hours else "immediately"))
        if flags.get("no_interview"):
            f.append(self.finding("P11_NO_INTERVIEW", rule_receipt("P11_NO_INTERVIEW"), [proc.id]))
        if flags.get("chat_only_interview"):
            f.append(self.finding("P11_CHAT_INTERVIEW", rule_receipt("P11_CHAT_INTERVIEW"), [proc.id]))
        return self.result(f)
