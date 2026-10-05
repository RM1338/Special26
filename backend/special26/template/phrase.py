"""Distinctive sentence for the P10 Google query (08 §7.4)."""
import re

from wordfreq import zipf_frequency

from special26.claims.models import ClaimSet
from special26.template.normalize import tokens

SENT = re.compile(r"(?<=[.!?])\s+|\n\s*\n|\n(?=[A-Z])")


def distinctive_sentence(text: str, claims: ClaimSet | None = None) -> str | None:
    best, best_score = None, -1.0
    for s in SENT.split(text):
        s = " ".join(s.split())
        if not s or "<RECIPIENT" in s.upper():               # never send the recipient's name
            continue
        toks = tokens(s, claims)
        if not 8 <= len(toks) <= 25 or sum(t.startswith("<") for t in toks) > 1:
            continue
        words = [t for t in toks if not t.startswith("<")]
        score = sum(7 - zipf_frequency(w, "en") for w in words) / len(words)
        if score > best_score:
            best, best_score = s, score
    return " ".join(best.split()[:20]) if best else None
