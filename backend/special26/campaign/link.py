"""Union-find campaign linking over shared identifiers, images and templates (08 §8, 05 §10). FR-43."""
from special26.template.minhash import signature
from special26.template.normalize import tokens

LINK_TIERS = ("red", "amber")
TEMPLATE_J = 0.6


def neighbours(repo, check_id: str, ids: list[dict], text: str, claims) -> dict[str, str]:
    """{other_check_id: first edge type that links it}."""
    out: dict[str, str] = {}
    for i in ids:
        if i["kind"] == "domain" and i["domain_class"] in ("freemail", "platform"):
            continue
        for other in repo.checks_with_identifier(i["kind"], i["value"], tiers=LINK_TIERS, exclude=check_id):
            out.setdefault(other, i["kind"])
    for other in repo.phash_neighbours(check_id, tiers=LINK_TIERS):
        out.setdefault(other, "image")
    sig = signature(tokens(text or "", claims))
    if sig:
        for c in repo.template_candidates(sig, exclude=check_id):
            if c["jaccard"] >= TEMPLATE_J and not c["check_id"].startswith("seed:") \
                    and repo.tier_of(c["check_id"]) in LINK_TIERS:
                out.setdefault(c["check_id"], "template")
    return out


def link_campaign(repo, check_id: str, ids: list[dict], text: str, claims) -> int | None:
    """Merge every campaign touched by a neighbour into the lowest id (stable); returns the campaign id."""
    near = neighbours(repo, check_id, ids, text, claims)
    if not near:
        return None
    existing = {c for c in (repo.campaign_of(n) for n in near) if c is not None}
    target = min(existing) if existing else repo.create_campaign()
    for cid in sorted(existing - {target}):
        repo.merge_campaign(src=cid, dst=target)
    first_edge = next(iter(near.values()))
    repo.add_member(target, check_id, first_edge)
    for other, edge in near.items():
        if repo.campaign_of(other) != target:
            repo.add_member(target, other, edge)
    repo.refresh_campaign_stats(target)
    return target
