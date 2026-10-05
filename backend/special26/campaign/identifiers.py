"""Hard scammer-side identifiers (08 §4 P06, §8; 06 identifiers). Priority: upi, phone, domain, email."""
from special26.claims.models import ClaimSet
from special26.claims.models import ClaimType as T
from special26.domains.classify import classify, reg
from special26.scoring.mask import mask_email, mask_phone, mask_upi

SUSPECT = {"typosquat", "combosquat", "tld_swap", "homoglyph", "unrelated"}
ORDER = {"upi": 0, "phone": 1, "domain": 2, "email": 3}


def hard_identifiers(claims: ClaimSet, official: set[str]) -> list[dict]:
    """[{kind, value (normalised), domain_class, claim_id}] in 08 priority order, de-duplicated."""
    out, seen = [], set()

    def add(kind, value, cls, claim_id):
        if value and (kind, value) not in seen:
            seen.add((kind, value))
            out.append({"kind": kind, "value": value, "domain_class": cls, "claim_id": claim_id})

    for c in claims.all(T.upi_id):
        add("upi", c.value["vpa"].lower(), None, c.id)
    for c in claims.all(T.phone):
        if c.value.get("role") != "recipient":
            add("phone", "".join(ch for ch in c.value["e164"] if ch.isdigit())[-10:], None, c.id)
    domains = []
    for t in (T.sender_email, T.reply_to):
        for c in claims.all(t):
            domains.append((c.value["address"].split("@")[-1], c.id))
    domains += [(c.value["host"], c.id) for c in claims.all(T.url)
                if c.value.get("kind") in ("other", "document") and c.value.get("host")]
    for d, cid in domains:
        cls = classify(d, official)[0]
        if cls in SUSPECT:
            add("domain", reg(d), cls, cid)
    for t in (T.sender_email, T.reply_to):
        for c in claims.all(t):
            cls = classify(c.value["address"].split("@")[-1], official)[0]
            if cls not in ("official", "official_subdomain", "freemail"):
                add("email", c.value["address"].lower(), cls, c.id)
    return sorted(out, key=lambda x: ORDER[x["kind"]])


def display(kind: str, value: str) -> str:
    """Masked form for reason text (D-20); domains stay in full."""
    return {"upi": lambda v: f"The UPI ID {mask_upi(v)}", "phone": lambda v: f"The phone number {mask_phone(v)}",
            "email": lambda v: f"The email address {mask_email(v)}",
            "domain": lambda v: f"The domain {v}"}[kind](value)


def masked(kind: str, value: str) -> str:
    return {"upi": mask_upi, "phone": mask_phone, "email": mask_email}.get(kind, lambda v: v)(value)
