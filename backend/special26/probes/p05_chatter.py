"""P05_CHATTER: are people complaining about this? Google, Google News, Google Forums, 3 calls (08 §4, D-42)."""
import re
from datetime import datetime, timedelta
from urllib.parse import urlparse

from rapidfuzz import fuzz

from special26 import seeds
from special26.campaign.identifiers import SUSPECT
from special26.claims.models import ClaimType as T
from special26.claims.regexes import has_scam_word, word_rx
from special26.domains.classify import classify, reg
from special26.errors import BudgetExhausted, ReplayMiss, UpstreamError
from special26.probes.base import Probe, ProbeContext, ProbeResult, serp_receipt

WINDOW_DAYS = 730                                    # 24 months
REL = re.compile(r"(\d+|an?|one)\s+(year|month|week|day|hour|minute)s?\s+ago", re.IGNORECASE)
UNIT_DAYS = {"year": 365, "month": 30, "week": 7, "day": 1, "hour": 0, "minute": 0}


def result_date(r: dict, now: datetime) -> datetime | None:
    if r.get("iso_date"):
        try:
            return datetime.fromisoformat(r["iso_date"])
        except ValueError:
            pass
    text = f"{r.get('date', '')} {r.get('displayed_meta', '')}"
    if m := REL.search(text):
        n = 1 if m.group(1).lower() in ("a", "an", "one") else int(m.group(1))
        return now - timedelta(days=n * UNIT_DAYS[m.group(2).lower()])
    for fmt in ("%b %d, %Y", "%d %b %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(r.get("date", "").strip(), fmt).replace(tzinfo=now.tzinfo)
        except ValueError:
            continue
    return None


class P05Chatter(Probe):
    id = "P05_CHATTER"
    engine = "google"
    depends_on = ("P01_ENTITY",)
    max_calls = 3
    timeout_s = 40.0

    def applicable(self, ctx: ProbeContext):
        return None if ctx.claims.org_name else "skipped_no_input"

    async def run(self, ctx: ProbeContext) -> ProbeResult:
        org = ctx.claims.org_name
        official = set(ctx.official)
        site = f" -site:{ctx.official[0]}" if ctx.official else ""                # D-26
        calls = [("google", {"engine": "google", "q": f'"{org}" (internship OR "offer letter" OR job) '
                                                      f'(scam OR fraud OR fake){site}', "num": 10}, "organic_results"),
                 ("google_news", {"engine": "google_news", "q": f'"{org}" fake job offer'}, "news_results"),
                 ("google_forums", {"engine": "google_forums", "q": f"{org} offer letter fee scam"}, "organic_results")]
        got, failures = [], []
        for engine, params, field in calls:
            try:
                data, key = await self.search(ctx, params)
            except (UpstreamError, ReplayMiss, BudgetExhausted) as e:
                if engine != "google_forums":                         # forums is optional, skipped quietly
                    failures.append(e)
                continue
            for r in data.get(field, []):
                if reg(urlparse(r.get("link", "")).netloc) not in official:   # -site: may be ignored (D-34)
                    got.append((engine, params["q"], key, r))
        if len(failures) == 2:
            raise failures[0]

        job_rx = word_rx(seeds.lexicons()["job_words"])
        now = ctx.created_at
        complaints = []
        for engine, q, key, r in got:
            text = f"{r.get('title', '')} {r.get('snippet', '')}"
            d = result_date(r, now)
            if (fuzz.partial_ratio(org.lower(), text.lower()) >= 85 and has_scam_word(text)
                    and job_rx.search(text.lower()) and (d is None or (now - d).days <= WINDOW_DAYS)):
                complaints.append((engine, q, key, r))

        ids = [ctx.claims.first(T.org).id]
        f = []
        if len(complaints) >= 3:
            e, q, k, r = complaints[0]
            f.append(self.finding("P05_COMPLAINTS_GENERAL", serp_receipt(e, q, k, r), ids, n=len(complaints), org=org))
        needles = self._sender_needles(ctx, official)
        for e, q, k, r in complaints:
            blob = f"{r.get('title', '')} {r.get('snippet', '')} {r.get('link', '')}".lower()
            hit = next((n for n in needles if n.lower() in blob), None)
            if hit:
                f.append(self.finding("P05_COMPLAINT_NAMES_SENDER", serp_receipt(e, q, k, r), ids,
                                      source=reg(urlparse(r.get("link", "")).netloc), identifier=hit))
                break
        if ctx.claims.first(T.scheme):
            pib = next(((e, q, k, r) for e, q, k, r in got if reg(urlparse(r.get("link", "")).netloc) == "pib.gov.in"
                        or "pib fact check" in r.get("title", "").lower()), None)
            if pib:
                f.append(self.finding("P05_PIB_FACTCHECK", serp_receipt(*pib), ids))
        return self.result(f, {"complaints": len(complaints), "failed_calls": len(failures)})

    @staticmethod
    def _sender_needles(ctx: ProbeContext, official: set[str]) -> list[str]:
        out = []
        s = ctx.claims.first(T.sender_email)
        if s:
            d = s.value["address"].split("@")[-1]
            if classify(d, official)[0] in SUSPECT:
                out.append(reg(d))
        hr = ctx.claims.first(T.hr_person)
        if hr and len((hr.value.get("name") or "").split()) >= 2:
            out.append(hr.value["name"])
        return out
