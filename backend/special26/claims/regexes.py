"""Patterns from 08 §2.2 and helpers for keyword matching. FR-10."""
import re

from special26 import seeds

EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", re.IGNORECASE)
URL = re.compile(r"(?:https?://|www\.)[^\s<>\"')\]]+", re.IGNORECASE)
BARE_DOMAIN = re.compile(r"\b(?:[a-z0-9\-]+\.)+(?:com|in|co\.in|org|net|io|xyz|online|site|top|info|co|live|work"
                         r"|careers|jobs)\b", re.IGNORECASE)
UPI_URI = re.compile(r"upi://[^\s<>\"')\]]+", re.IGNORECASE)
PHONE_IN = re.compile(r"(?<!\d)(?:\+?91[\s\-]?|0)?([6-9]\d{4})[\s\-]?(\d{5})(?!\d)", re.IGNORECASE)
UPI = re.compile(r"\b([a-z0-9.\-_]{2,256})@([a-z]{2,64})\b(?!\.[a-z])", re.IGNORECASE)
AMOUNT = re.compile(r"(?:₹|(?<![a-z])(?:rs\.?|inr|rupees))\s?(\d{1,3}(?:,\d{2,3})+|\d+)(?:\.\d+)?(?:\s?(k|lakh|lakhs|lpa)(?!\w))?"
                    r"|(\d{1,3}(?:,\d{2,3})+|\d+)\s?(?:/-|rs\b|rupees)", re.IGNORECASE)
CIN = re.compile(r"\b[LU]\d{5}[A-Z]{2}\d{4}(?:PLC|PTC|OPC|LLC|NPL|GOI|SGC|FTC|GAP|GAT)\d{6}\b")   # case-sensitive
GSTIN = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b")                                # case-sensitive
PIN = re.compile(r"\b[1-9]\d{5}\b")

TRAILING_PUNCT = ".,;:!?"


def strip_url(u: str) -> str:
    return u.rstrip(TRAILING_PUNCT)


def overlaps(span: tuple[int, int], spans: list[tuple[int, int]]) -> bool:
    return any(span[0] < e and s < span[1] for s, e in spans)


def amount_value(m: re.Match) -> int:
    num = re.search(r"\d[\d,]*(?:\.\d+)?", m.group()).group().replace(",", "")   # keeps decimals: 1.5 lakh
    mult = {"k": 1_000, "lakh": 100_000, "lakhs": 100_000, "lpa": 100_000}.get((m.group(2) or "").lower(), 1)
    return round(float(num) * mult)


def norm_phone(a: str, b: str) -> str:
    return "+91" + a + b


def word_rx(words, inflect: bool = True, prefix: bool = False) -> re.Pattern:
    """Lowercase keyword matcher. inflect: also -s/-es/-ed/-ing; prefix: stem match (e.g. 'impersonat')."""
    alts = "|".join(re.escape(w.lower()) for w in sorted(words, key=len, reverse=True))
    tail = r"\w*" if prefix else (r"(?:s|es|ed|ing)?(?!\w)" if inflect else r"(?!\w)")
    return re.compile(rf"(?<![a-z0-9])(?:{alts}){tail}")


def scam_rx() -> re.Pattern:
    return word_rx(seeds.lexicons()["scam_words"], prefix=True)


def has_scam_word(text: str) -> bool:
    return bool(scam_rx().search(text.lower()))


def flat(text: str) -> str:
    """Lowercase, punctuation to spaces, collapsed: for phrase lists ('Last date: today' -> 'last date today')."""
    return re.sub(r"\s+", " ", re.sub(r"[^\w/]+", " ", text.lower())).strip()
