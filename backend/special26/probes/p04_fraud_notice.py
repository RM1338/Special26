"""P04_FRAUD_NOTICE: has the employer warned about this? Google Search, 1 call (08 §4, D-34)."""
import re
from urllib.parse import urlparse

from special26 import seeds
from special26.claims.models import ClaimType as T
from special26.domains.classify import reg
from special26.probes.base import Probe, ProbeContext, ProbeResult, Receipt, serp_receipt

TERMS = '(fraud OR fraudulent OR "fake job" OR "fake offer" OR scam OR "recruitment fraud")'
NOTICE = re.compile(r"(recruit|job|offer|hiring|employment).{0,40}(fraud|scam|fake)|"
                    r"(fraud|scam|fake).{0,40}(recruit|job|offer|hiring|employment)", re.IGNORECASE | re.DOTALL)
NO_FEE = re.compile(r"(never|not|do not|does not)\s+(ask|charge|collect|seek|request|demand).{0,40}"
                    r"(fee|money|payment|deposit|amount)", re.IGNORECASE | re.DOTALL)


def query(official: list[str]) -> str:
    sites = " OR ".join(f"site:{o}" for o in official[:2])
    return f"({sites}) {TERMS}"


def seed_notice(entity_id: int | None) -> Receipt | None:
    """The employer's own notice verified at seed time (D-34): used only when search returns none on-site."""
    e = next((e for e in seeds.entities() if e["entity_id"] == entity_id), None)
    if not e or not e.get("fraud_notice_url") or not e.get("fraud_notice_quote"):
        return None
    return Receipt(kind="rule", rule_id="known_entities.fraud_notice", title=f"{e['name']} recruitment fraud notice",
                   link=e["fraud_notice_url"], snippet=e["fraud_notice_quote"],
                   extra={"verified_on": e.get("fraud_notice_verified_on"), "source": "employer_notice_seed"})


class P04FraudNotice(Probe):
    id = "P04_FRAUD_NOTICE"
    engine = "google"
    depends_on = ("P01_ENTITY",)
    max_calls = 1
    timeout_s = 25.0          # D-34

    def applicable(self, ctx: ProbeContext):
        if not ctx.claims.org_name:
            return "skipped_no_input"
        return None if ctx.official else "skipped_no_official_domain"

    async def run(self, ctx: ProbeContext) -> ProbeResult:
        org = ctx.claims.first(T.org)
        official = set(ctx.official)
        q = query(ctx.official)
        data, key = await self.search(ctx, {"engine": "google", "q": q, "num": 10})
        # D-34: Google may ignore site:, so only results on the employer's own domains count as its notice
        notices = [r for r in data.get("organic_results", [])
                   if reg(urlparse(r.get("link", "")).netloc) in official
                   and NOTICE.search(f"{r.get('title', '')} {r.get('snippet', '')}")]
        no_fee = [r for r in notices if NO_FEE.search(r.get("snippet", ""))]
        if notices:
            best, flag = (no_fee or notices)[0], bool(no_fee)
            receipt = serp_receipt("google", q, key, best)
        elif receipt := seed_notice(org.value.get("entity_id")):
            flag = bool(NO_FEE.search(receipt.snippet or ""))
        else:
            return self.result([], {"notices": []})
        f = self.finding("P04_NOTICE_FOUND", receipt, [org.id], decisive_flag="P04_NOTICE_NO_FEE" if flag else None,
                         org=org.value["name"])
        return self.result([f], {"notices": [{"link": receipt.link, "no_fee": flag}]})
