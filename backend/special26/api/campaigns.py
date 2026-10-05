"""GET /api/campaigns/{id}: masked campaign summary (07 §7). FR-44."""
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from special26.campaign.identifiers import masked
from special26.errors import NotFound

router = APIRouter(prefix="/api")


@router.get("/campaigns/{campaign_id}")
async def campaign(campaign_id: int, request: Request):
    repo = request.app.state.s26.repo
    c = repo.campaign(campaign_id)
    if c is None:
        raise NotFound("This campaign does not exist.")
    if c["merged_into"]:
        return RedirectResponse(f"/api/campaigns/{c['merged_into']}", status_code=301)
    members = repo.campaign_members(campaign_id)
    ids = [m["check_id"] for m in members]
    shared = repo.db.execute(
        f"SELECT kind, value_norm, COUNT(DISTINCT check_id) n FROM identifiers WHERE check_id IN "
        f"({','.join('?' * len(ids))}) GROUP BY kind, value_norm HAVING n >= 2 ORDER BY n DESC, kind", ids).fetchall() \
        if ids else []
    orgs = {m["check_id"]: next((cl.value.get("name") for cl in repo.claims(m["check_id"]) if cl.type.value == "org"),
                                None) for m in members}
    return {
        "campaign_id": campaign_id, "member_count": c["member_count"], "orgs": c["orgs"],
        "first_seen": c["first_seen"], "last_seen": c["last_seen"], "edge_counts": c["edge_counts"],
        "tier_counts": c["tier_counts"],
        "shared_identifiers": [{"kind": k, **({"value": v} if k == "domain" else {"masked": masked(k, v)}), "checks": n}
                               for k, v, n in shared],
        "members": [{"share_token": m["token"], "org": orgs[m["check_id"]], "tier": m["tier"],
                     "created_at": m["created_at"]} for m in members],
    }
