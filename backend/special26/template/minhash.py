"""MinHash signature and LSH (08 §7.2, §7.3; 05 §10). Fixed seed: part of the ruleset (NFR-04)."""
import hashlib
import random

P = (1 << 61) - 1
_rng = random.Random(26)
A = [_rng.randrange(1, P) for _ in range(128)]
B = [_rng.randrange(0, P) for _ in range(128)]
BANDS, ROWS = 32, 4
MIN_TOKENS = 30


def signature(tokens: list[str], k: int = 5) -> list[int] | None:
    if len(tokens) < MIN_TOKENS:
        return None
    xs = {int.from_bytes(hashlib.blake2b(" ".join(tokens[i:i + k]).encode(), digest_size=8).digest(), "big")
          for i in range(len(tokens) - k + 1)}
    return [min((a * x + b) % P for x in xs) for a, b in zip(A, B, strict=True)]


def band_keys(sig: list[int]) -> list[str]:
    return [hashlib.blake2b(f"{b}:".encode() + b"".join(v.to_bytes(8, "big") for v in sig[b * ROWS:(b + 1) * ROWS]),
                            digest_size=8).hexdigest() for b in range(BANDS)]


def jaccard_est(a: list[int], b: list[int]) -> float:
    return sum(x == y for x, y in zip(a, b, strict=True)) / len(a)


def to_blob(sig: list[int]) -> bytes:
    return b"".join(v.to_bytes(8, "big") for v in sig)


def from_blob(blob: bytes) -> list[int]:
    return [int.from_bytes(blob[i:i + 8], "big") for i in range(0, len(blob), 8)]
