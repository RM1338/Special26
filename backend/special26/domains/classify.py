"""Domain classification (08 §3, 05 §5)."""
import re
import unicodedata

import tldextract
from rapidfuzz.distance import DamerauLevenshtein

from special26 import seeds

# Offline PSL snapshot; bank.in / fin.in (RBI-restricted zones) are missing from it (D-30).
EXT = tldextract.TLDExtract(suffix_list_urls=(), extra_suffixes=("bank.in", "fin.in"))
SWAPS = [("rn", "m"), ("vv", "w"), ("0", "o"), ("1", "l"), ("3", "e"), ("5", "s"), ("l", "i")]  # order matters
# Minimal Unicode confusables (Cyrillic/Greek lookalikes of Latin letters); IDNs are caught by "xn--" anyway.
CONFUSABLES = str.maketrans({"а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x", "і": "i",
                             "ј": "j", "ԁ": "d", "ɡ": "g", "ո": "n", "ս": "u", "ν": "v", "ο": "o", "ρ": "p",
                             "α": "a", "ϲ": "c", "ӏ": "l", "ɩ": "i", "ʟ": "l"})


def to_ascii(d: str) -> str:
    d = d.strip().strip(".").lower()
    try:
        return d.encode("idna").decode()
    except UnicodeError:
        return d


def reg(d: str) -> str:
    """Registrable domain, punycode-encoded for comparison (08 §2.2)."""
    d = to_ascii(d)
    return EXT(d).top_domain_under_public_suffix or d


def label(d: str) -> str:
    return EXT(to_ascii(d)).domain


def host_of(url: str) -> str:
    u = re.sub(r"^[a-z][a-z0-9+.\-]*://", "", url.strip(), flags=re.IGNORECASE)
    return to_ascii(re.split(r"[/?#:]", u, maxsplit=1)[0])


def platform_kind(url_or_host: str) -> str | None:
    """Kind from 08 §2.2 platform hosts; matched on host (+ path prefix), not registrable domain."""
    if url_or_host.strip().lower().startswith("upi:"):
        return "payment"
    u = re.sub(r"^[a-z][a-z0-9+.\-]*://", "", url_or_host.strip().lower())
    u = re.sub(r"^www\.", "", u)
    for hostpath, kind in seeds.platform_hosts():
        if u == hostpath or u.startswith((hostpath + "/", hostpath + "?")) \
                or ("/" not in hostpath and host_of(u).endswith("." + hostpath)):
            return kind
    return None


def skeleton(s: str) -> str:
    return unicodedata.normalize("NFKC", s).translate(CONFUSABLES)


def _swap_norm(s: str) -> str:
    for a, b in SWAPS:
        s = s.replace(a, b)
    return s


def _segment_into_lures(p: str, lure: frozenset) -> bool:
    i = 0
    while i < len(p):
        for n in range(len(p) - i, 0, -1):
            if p[i:i + n] in lure:
                i += n
                break
        else:
            return False
    return True


def _is_combo(lab: str, olab: str) -> bool:
    a, o = lab.replace("-", ""), olab.replace("-", "")
    if o not in a or a == o:
        return False
    lure = frozenset(seeds.lines("lure_tokens.txt"))
    rest = a.replace(o, " ", 1)
    return all(_segment_into_lures(p, lure) for p in rest.split() if p)


def classify(d: str, official: set[str] | frozenset[str]) -> tuple[str, str | None]:
    """Returns (class, matched_official). FR-20 inputs for P02, P06, P12."""
    d = to_ascii(d)
    r = reg(d)
    official = {reg(o) for o in official}
    if r in official:
        return ("official" if d in (r, "www." + r) else "official_subdomain", r)
    if r in seeds.lines("freemail.txt"):
        return ("freemail", None)
    if platform_kind(d):
        return ("platform", None)
    lab, sub = label(d), EXT(d).subdomain.split(".")
    best = None
    for o in sorted(official):
        ol = label(o)
        if lab != ol and ("xn--" in d or skeleton(lab) == ol or _swap_norm(lab) == _swap_norm(ol)):
            return ("homoglyph", o)
        if lab == ol:
            return ("tld_swap", o)
        if DamerauLevenshtein.distance(lab, ol) <= max(1, len(ol) // 8):
            best = best or ("typosquat", o)
        if _is_combo(lab, ol) or ol in sub:
            best = ("combosquat", o)
    return best or ("unrelated", None)
