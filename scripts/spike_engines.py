"""T0.5: one live call per SerpApi engine; raw JSON saved to backend/tests/fixtures/serp/.

Usage: SERPAPI_API_KEY=... .venv/bin/python scripts/spike_engines.py   (spends 6 credits, cached after)
"""
import asyncio
import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from special26.config import Settings
from special26.errors import Special26Error
from special26.serp.client import SerpClient
from special26.storage.db import connect, migrate
from special26.storage.repo import Repo

OUT = Path(__file__).resolve().parents[1] / "backend/tests/fixtures/serp"
# Widely reused Pexels stock portrait: 400 exact matches incl. pexels.com (D-29).
LENS_URL = "https://images.pexels.com/photos/774909/pexels-photo-774909.jpeg?w=800"

CALLS = {
    "google_entity_techmahindra": {"engine": "google", "q": "\"Tech Mahindra\"", "num": 10},
    "google_news_techmahindra": {"engine": "google_news", "q": "\"Tech Mahindra\" fake job offer"},
    "google_forums_techmahindra": {"engine": "google_forums", "q": "Tech Mahindra offer letter fee scam"},
    "google_jobs_techmahindra": {"engine": "google_jobs", "q": "Data Analyst Intern Tech Mahindra", "location": "India"},
    "google_maps_techmahindra": {"engine": "google_maps", "type": "search", "q": "Tech Mahindra office Noida"},
    "google_lens_exact_stock": {"engine": "google_lens", "url": LENS_URL, "type": "exact_matches", "image_sha256": "spike"},
}


async def main():
    s = Settings()
    if s.serpapi_api_key is None:
        sys.exit("set SERPAPI_API_KEY")
    conn = connect(s.db_path)
    migrate(conn)
    async with httpx.AsyncClient() as http:
        c = SerpClient(s, Repo(conn), http)
        for name, params in CALLS.items():
            try:
                data, _, hit = await c.search(None, params)
            except Special26Error as e:
                print(f"{name}: FAILED {type(e).__name__}: {e}")
                continue
            data.get("search_parameters", {}).pop("api_key", None)
            (OUT / f"{name}.json").write_text(json.dumps(data, indent=1, ensure_ascii=False))
            print(f"{name}: {'cache' if hit else 'live'} keys={sorted(k for k in data if not k.startswith('search_'))}")


asyncio.run(main())
