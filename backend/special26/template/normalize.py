"""Template normalisation (08 §7.1)."""
import re
import unicodedata

from special26 import seeds
from special26.claims.models import ClaimSet
from special26.claims.models import ClaimType as T
from special26.claims.regexes import AMOUNT, BARE_DOMAIN, EMAIL, PHONE_IN, UPI, URL

DATE = re.compile(r"\b\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4}\b|\b\d{1,2}(?:st|nd|rd|th)?\s+(?:jan|feb|mar|apr|may|jun|jul|aug"
                  r"|sep|oct|nov|dec)[a-z]*\.?(?:,?\s+\d{4})?\b|\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)"
                  r"[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+\d{4})?\b", re.IGNORECASE)
TOKEN = re.compile(r"<[a-z]+>|[^\W_]+")


def org_names(claims: ClaimSet | None) -> list[str]:
    org = claims.first(T.org) if claims else None
    if not org:
        return []
    names = {org.value["name"]}
    ent = next((e for e in seeds.entities() if e["entity_id"] == org.value.get("entity_id")), None)
    if ent:
        names |= {ent["name"], *ent.get("aliases", [])}
    return sorted(names, key=len, reverse=True)


def placeholders(text: str, claims: ClaimSet | None = None) -> str:
    """Lowercased, NFKC text with identifiers replaced, in the 08 §7.1 order."""
    t = unicodedata.normalize("NFKC", text).lower()
    t = EMAIL.sub(" <email> ", t)
    t = URL.sub(" <url> ", t)
    t = BARE_DOMAIN.sub(" <url> ", t)
    t = UPI.sub(" <upi> ", t)
    t = PHONE_IN.sub(" <phone> ", t)
    t = AMOUNT.sub(" <amt> ", t)
    t = DATE.sub(" <date> ", t)
    for name in org_names(claims):
        t = re.sub(rf"(?<!\w){re.escape(name.lower())}(?!\w)", " <org> ", t)
    hr = claims.first(T.hr_person) if claims else None
    if hr and hr.value.get("name"):
        t = re.sub(rf"(?<!\w){re.escape(hr.value['name'].lower())}(?!\w)", " <per> ", t)
    t = re.sub(r"<recipient(?:_email|_phone)?>", " <recipient> ", t)
    t = re.sub(r"<id>", " <num> ", t)
    return re.sub(r"\d+", " <num> ", t)


def tokens(text: str, claims: ClaimSet | None = None) -> list[str]:
    return TOKEN.findall(placeholders(text, claims))
