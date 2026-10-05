"""Organisation and scheme resolution (08 §2.3, §2.4). FR-11."""
import re
from functools import lru_cache

import ahocorasick

from special26 import seeds

LEGAL_SUFFIX = r"(?:Private Limited|Pvt\.?\s?Ltd\.?|Limited|Ltd\.?|LLP|Inc\.?)"
DESCRIPTOR = r"(?:Technologies|Solutions|Services|Consultancy|Infotech|Softech)"
LEGAL_LINE = re.compile(rf"^(.{{2,60}}?)\s+({LEGAL_SUFFIX}|{DESCRIPTOR})(?!\w)")
TRAILING_LEGAL = re.compile(rf"^[ \t,]*({LEGAL_SUFFIX})(?!\w)")
PREPOSITION = re.compile(r"^.*\b(?:at|with|join|joining|from|welcome to|behalf of)\s+(?=[A-Z])", re.IGNORECASE)  # D-24
PATTERN = re.compile(r"(?i:\b(?:at|with|join(?:ing)?|from|welcome to|behalf of))[ \t]+"
                     r"([A-Z][\w&.\-]*(?:[ \t]+[A-Z][\w&.\-]*){0,4})")
# D-31: brand matches that name a product or a payment rail, not the employer
PRODUCT_NEXT = {"form", "forms", "pay", "meet", "drive", "docs", "sheets", "lens", "maps", "play", "wallet", "jobs",
                "translate", "classroom", "upi"}
PAYMENT_APPS = {"Paytm"}
PAYMENT_PREV = {"via", "on", "using", "through", "to", "with", "in"}


@lru_cache
def _automaton():
    """Lowercase alias -> [(entity, original alias)] for companies and schemes."""
    a = ahocorasick.Automaton()
    table: dict[str, list] = {}
    for e in seeds.entities():
        for alias in {e["name"], *e.get("aliases", [])}:
            table.setdefault(alias.lower(), []).append((e, alias))
    for k, v in table.items():
        a.add_word(k, (k, v))
    a.make_automaton()
    return a


def _matches(text: str, kinds: set[str]):
    """Yield (entity, start, end) for dictionary hits passing boundary and casing guards."""
    lower = text.lower()
    for end_idx, (alias, cands) in _automaton().iter(lower):
        start, end = end_idx - len(alias) + 1, end_idx + 1
        if (start > 0 and lower[start - 1].isalnum()) or (end < len(lower) and lower[end].isalnum()):
            continue
        surface = text[start:end]
        for e, orig in cands:
            if e["kind"] not in kinds:
                continue
            if e["kind"] == "company":
                if len(orig) <= 4 and surface != orig:        # short aliases (TCS, EY, HCL) match exact case only
                    continue
                if surface == surface.lower():                # proper-noun guard: "reliance", "@paytm"
                    continue
                nxt = re.match(r"[ \t]+(\w+)", text[end:])
                if nxt and nxt.group(1).lower() in PRODUCT_NEXT:
                    continue
                prev = re.search(r"(\w+)[ \t]+$", text[:start])
                if e["name"] in PAYMENT_APPS and prev and prev.group(1).lower() in PAYMENT_PREV:
                    continue
            yield e, start, end


def by_dictionary(text: str):
    """Longest match wins; ties by earliest position (08 §2.3 step 1)."""
    best = None
    for e, s, t in _matches(text, {"company", "scheme"}):
        if best is None or (t - s, -s) > (best[2] - best[1], -best[1]):
            best = (e, s, t)
    return best


def schemes(text: str) -> list[tuple[dict, int, int]]:
    seen, out = set(), []
    for e, s, t in sorted(_matches(text, {"scheme"}), key=lambda x: x[1]):
        if e["scheme_key"] not in seen:
            seen.add(e["scheme_key"])
            out.append((e, s, t))
    return out


def _stop(name: str) -> bool:
    stop = {w.lower() for w in seeds.lexicons()["org_stop_words"]}
    cities = {c.lower() for c in seeds.lines("cities.txt")}
    return name.split()[0].lower() in stop or name.lower() in stop or name.lower() in cities


def by_legal_line(text: str):
    lines = text.splitlines()
    idx = list(range(min(8, len(lines)))) + list(range(max(0, len(lines) - 12), len(lines)))
    offsets = [0]
    for ln in lines:
        offsets.append(offsets[-1] + len(ln) + 1)
    for i in dict.fromkeys(idx):
        line = lines[i]
        lead = len(line) - len(line.lstrip())
        m = LEGAL_LINE.match(line.strip())
        if not m:
            continue
        name, suffix = m.group(1), m.group(2)
        cut = PREPOSITION.match(name)
        if cut:
            name = name[cut.end():]
        legal = None
        if re.fullmatch(DESCRIPTOR, suffix):
            name = f"{name} {suffix}"
            t = TRAILING_LEGAL.match(line.strip()[m.end():])
            legal = t.group(1) if t else None
        else:
            legal = suffix
        name = name.strip(" ,.-:")
        if not name or not name[0].isupper() or _stop(name):
            continue
        start = offsets[i] + lead + line.strip().find(name)
        return name, legal, (start, start + len(name))
    return None


def by_pattern(text: str):
    for m in PATTERN.finditer(text):
        name = m.group(1).rstrip(".,-")
        if not _stop(name):
            return name, (m.start(1), m.start(1) + len(name))
    return None


def by_display_name(display_name: str | None) -> str | None:
    if not display_name:
        return None
    drop = {w.lower() for w in seeds.lexicons()["display_name_drop"]}
    name = " ".join(w for w in re.split(r"\s+", display_name.strip(" \"'")) if w.lower() not in drop)
    return name or None


def trailing_legal(text: str, end: int) -> str | None:
    t = TRAILING_LEGAL.match(text[end:])
    return t.group(1) if t else None


def ending_legal(surface: str) -> str | None:
    m = re.search(rf"\s({LEGAL_SUFFIX})$", surface)
    return m.group(1) if m else None
