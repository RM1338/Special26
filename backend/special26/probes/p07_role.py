"""P07_ROLE: does the role exist? Google Jobs, 1 call (08 §4)."""
from rapidfuzz import fuzz

from special26.claims.models import ClaimType as T
from special26.errors import UpstreamError
from special26.probes.base import Probe, ProbeContext, ProbeResult, serp_receipt


def job_receipt(q: str, key: str, i: int, j: dict):
    return serp_receipt("google_jobs", q, key, {
        "position": i + 1, "title": f"{j.get('title')} at {j.get('company_name')}",
        "link": j.get("share_link"), "snippet": " · ".join(x for x in (j.get("location"), f"via {j['via']}"
                                                                        if j.get("via") else None) if x)})


class P07Role(Probe):
    id = "P07_ROLE"
    engine = "google_jobs"
    depends_on = ("P01_ENTITY",)
    max_calls = 1
    timeout_s = 25.0

    def applicable(self, ctx: ProbeContext):
        return None if ctx.claims.org_name and ctx.claims.first(T.role) else "skipped_no_input"

    async def run(self, ctx: ProbeContext) -> ProbeResult:
        org, role = ctx.claims.first(T.org), ctx.claims.first(T.role)
        org_name, title = org.value["name"], role.value["title"]
        addr = ctx.claims.first(T.address)
        city = addr.value.get("city") if addr else None
        q = f"{title} {org_name}"
        try:
            data, key = await self.search(ctx, {"engine": "google_jobs", "q": q,
                                                "location": f"{city}, India" if city else "India"})
        except UpstreamError as e:                    # D-37: SerpApi may not know the city as a location
            if not city or "location" not in str(e).lower():
                raise
            data, key = await self.search(ctx, {"engine": "google_jobs", "q": q, "location": "India"})
        jobs = data.get("jobs_results", [])
        same_co = [(i, j) for i, j in enumerate(jobs) if fuzz.token_set_ratio(j.get("company_name", ""), org_name) >= 85]
        matched = [(i, j) for i, j in same_co if fuzz.token_set_ratio(j.get("title", ""), title) >= 60]
        ids = [org.id, role.id]
        if matched:
            i, j = matched[0]
            return self.result([self.finding("P07_ROLE_LISTED", job_receipt(q, key, i, j), ids, role=title,
                                             org=org_name)], {"listings": len(jobs)})
        if same_co:
            i, j = same_co[0]
            return self.result([self.finding("P07_COMPANY_LISTS_OTHER_ROLES", job_receipt(q, key, i, j), ids,
                                             role=title, org=org_name)], {"listings": len(jobs)})
        return self.result([], {"listings": len(jobs)})        # absence is not evidence (08 §4)
