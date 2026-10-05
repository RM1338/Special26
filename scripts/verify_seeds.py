"""T0.8: check each official domain in known_entities.json answers over HTTPS; record source_url and verified_on.

Prints domains that fail or redirect off their entity's own domain set, for manual review.
Usage: .venv/bin/python scripts/verify_seeds.py
"""
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import tldextract

SEEDS = Path(__file__).resolve().parents[1] / "data/seeds/known_entities.json"
EXT = tldextract.TLDExtract(suffix_list_urls=(), extra_suffixes=("bank.in", "fin.in"))  # D-30
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Special26-seed-check"}


async def probe(http, d):
    for url in (f"https://www.{d}/", f"https://{d}/"):
        try:
            r = await http.get(url, follow_redirects=True, timeout=15)
            return url, str(r.url), r.status_code
        except httpx.HTTPError:
            continue
    return None, None, None


async def main():
    ents = json.loads(SEEDS.read_text())
    async with httpx.AsyncClient(headers=UA) as http:
        for e in ents:
            own = set(e["official_domains"])
            res = await asyncio.gather(*(probe(http, d) for d in e["official_domains"]))
            ok = [(d, final) for d, (_, final, st) in zip(e["official_domains"], res)
                  if final and EXT(final).top_domain_under_public_suffix in own]
            for d, (_, final, st) in zip(e["official_domains"], res):
                if not final or EXT(final).top_domain_under_public_suffix not in own:
                    print(f"REVIEW {e['name']}: {d} -> {final} ({st})")
            if ok:
                e["source_url"], e["verified_on"] = ok[0][1], datetime.now(UTC).date().isoformat()
    SEEDS.write_text(json.dumps(ents, indent=1, ensure_ascii=False) + "\n")
    print(f"verified {sum('source_url' in e for e in ents)}/{len(ents)}")


asyncio.run(main())
