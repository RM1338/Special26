"""Amount purpose and payer (08 §2.5). FR-13. Window clipped at sentence ends (D-23)."""
import re
from functools import lru_cache

from special26 import seeds
from special26.claims.regexes import word_rx

WINDOW = 12
ABBREV = {"rs", "no", "p.m", "a.m", "dr", "mr", "mrs", "ms", "pvt", "ltd", "co", "inc", "st", "sr", "jr", "vs", "approx"}
_SENT_END = re.compile(r"[.!?](?=\s)|\n\s*\n")
TOKEN = re.compile(r"\S+")
NON_REFUNDABLE = re.compile(r"\bnon[\s\-]?refundable")
PURPOSE_ORDER = ["stipend", "salary", "verification", "deposit", "equipment", "training", "registration", "document",
                 "other_fee"]


@lru_cache
def _purpose_rx() -> dict[str, re.Pattern]:
    p = seeds.lexicons()["purposes"]
    return {k: word_rx(p[k]) for k in PURPOSE_ORDER}


@lru_cache
def _payer_rx() -> re.Pattern:
    return word_rx(seeds.lexicons()["payer_words"])


def sentence_span(text: str, start: int, end: int) -> tuple[int, int]:
    """The sentence holding [start, end). '.', '!' or '?' + whitespace ends a sentence unless it closes an
    abbreviation (Rs., p.m.); a blank line always does. Single line wraps do not."""
    lo, hi = 0, len(text)
    for m in _SENT_END.finditer(text):
        if m.group().startswith("."):
            word = re.search(r"([\w.]+)\.$", text[max(0, m.start() - 16):m.end()])   # bounded look-back
            if word and word.group(1).lower() in ABBREV:
                continue
        if m.end() <= start:
            lo = m.end()
        elif m.start() >= end:
            hi = m.start()
            break
    return lo, hi


def window(text: str, start: int, end: int, n: int = WINDOW) -> str:
    lo, hi = sentence_span(text, start, end)
    before = TOKEN.findall(text[lo:start])[-n:]
    after = TOKEN.findall(text[end:hi])[:n]
    w = " ".join(before + [text[start:end]] + after).lower()
    return NON_REFUNDABLE.sub("nonrefundable", w)          # D-23: "non-refundable" is not a deposit


def classify(text: str, start: int, end: int) -> tuple[str | None, str, str]:
    """Returns (purpose, payer, window). FR-13."""
    w = window(text, start, end)
    purpose = next((k for k, rx in _purpose_rx().items() if rx.search(w)), None)
    payer = "candidate" if purpose not in ("stipend", "salary") and _payer_rx().search(w) else "employer"
    return purpose, payer, w
