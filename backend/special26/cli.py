"""python -m special26.cli check FILE  -> prints tier and reasons (T1.10)."""
import argparse
import asyncio
from datetime import UTC, datetime
from pathlib import Path

import httpx

from special26.claims.extract import extract_claims
from special26.claims.redact import redact
from special26.config import get_settings
from special26.deps import build
from special26.pipeline.runner import run_probes
from special26.probes.base import validate_ruleset
from special26.probes.registry import PROBES
from special26.scoring.aggregate import score, strength
from special26.scoring.copy import HEADLINES


async def check(path: str, mode: str | None) -> None:
    validate_ruleset()
    s = get_settings()
    if mode:
        s.mode = mode
    text, _ = redact(Path(path).read_text())
    claims = extract_claims(text)
    async with httpx.AsyncClient() as http:
        repo, serp = build(s, http)
        base = {"check_id": None, "claims": claims, "created_at": datetime.now(UTC), "serp": serp, "settings": s,
                    "redacted_text": text, "repo": repo}
        results = await run_probes(base, PROBES)
    v = score(results)
    head = HEADLINES[(v.tier, v.red_kind)].format(org=claims.org_name or "the employer")
    print(f"{v.tier.upper()}{f' ({v.red_kind})' if v.red_kind else ''}: {head}")
    print(f"score {v.score}  strength {strength(v.score)}  coverage {v.coverage}  decisive {v.decisive or '-'}")
    for r in v.reasons:
        print(f"  {r.rank}. [{r.code}] {r.message}")
    for pid, r in results.items():
        print(f"  {pid:22} {r.status:22} credits={r.credits_used} cache={r.cache_hits} "
              f"{[f.code for f in r.findings]}")


def main() -> None:
    ap = argparse.ArgumentParser(prog="special26")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("file")
    c.add_argument("--mode", choices=["live", "replay"])
    a = ap.parse_args()
    asyncio.run(check(a.file, a.mode))


if __name__ == "__main__":
    main()
