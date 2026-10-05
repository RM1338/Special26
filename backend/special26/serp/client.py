"""Cache-first SerpApi client with budget, ledger, replay and record-to (04 §5, 05 §4). FR-22, FR-23, FR-26."""
import asyncio
import hashlib
import json
import logging

import httpx

from special26.errors import BudgetExhausted, ReplayMiss, UpstreamError

SERP_URL = "https://serpapi.com/search.json"
UPLOAD_URL = "https://serpapi.com/image"                # Lens image upload (D-27)
RDAP_URL = "https://rdap.org/domain/{}"
EMPTY_RESULT = "hasn't returned any results"   # SerpApi's empty-result "error" (05 §4 note)
NOT_KEYED = ("api_key", "output", "no_cache")
LENS_IMAGE_PARAMS = ("url", "image_id")        # D-12: Lens is keyed by image_sha256 instead
REQUEST_ONLY = ("image_sha256",)
HTTP_TIMEOUT = {"google_lens": 30.0}             # Lens measured 13.6 s and 16.6 s (D-29)
DEFAULT_TIMEOUT = 22.0                             # google measured up to 23 s on 2026-10-05 (D-34)

log = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)   # httpx INFO logs full URLs incl. api_key (NFR-07)


def key_params(params: dict) -> dict:
    drop = NOT_KEYED + (LENS_IMAGE_PARAMS if params.get("engine") == "google_lens" else ())
    return {k: params[k] for k in sorted(params) if k not in drop}


def cache_key(params: dict) -> str:
    return hashlib.sha256(json.dumps(key_params(params), sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def is_empty_result(data: dict) -> bool:
    return EMPTY_RESULT in str(data.get("error", ""))


class SerpClient:
    def __init__(self, settings, repo, http: httpx.AsyncClient):
        self.s, self.repo, self.http = settings, repo, http
        self._sem = asyncio.Semaphore(4)

    async def search(self, check_id: str | None, params: dict) -> tuple[dict, str, bool]:
        """Returns (json, cache_key, cache_hit). Raises BudgetExhausted, ReplayMiss or UpstreamError."""
        loc = {"hl": self.s.hl, "country": self.s.gl} if params["engine"] == "google_lens" \
            else {"gl": self.s.gl, "hl": self.s.hl}       # Lens takes country, not gl (D-28)
        params = {**loc, **params}
        key = cache_key(params)
        engine = params["engine"]
        if engine in self.s.masked_engines:
            raise ReplayMiss(f"{engine} masked for ablation")
        if self.s.mode == "replay":
            row = self.repo.demo_get(key)
            if row is None:
                raise ReplayMiss(f"no recording for {engine}")
            return row, key, True
        hit = self.repo.cache_get(key, ttl_hours=self.s.cache_ttl_hours)
        if hit is not None:
            self.repo.ledger_cache_hit(check_id, engine, key)
            self.repo.record_put(key, engine, key_params(params), hit)
            return hit, key, True
        row_id = self.repo.budget_reserve(check_id, engine, per_check=self.s.credit_budget_per_check,
                                          daily=self.s.daily_credit_cap)
        try:
            async with self._sem:
                data = await self._get_with_retry(params)
        except BaseException as e:
            # a timed-out request may still have run (and been billed) on SerpApi's side (D-29)
            self.repo.ledger_settle(row_id, key, spent=getattr(e, "charged", False))
            raise
        self.repo.ledger_settle(row_id, key, spent=True)
        self.repo.cache_put(key, engine, key_params(params), data)
        self.repo.record_put(key, engine, key_params(params), data)
        log.info("serp_call", extra={"check_id": check_id, "engine": engine, "cache_hit": False})
        return data, key, False

    async def _get_with_retry(self, params: dict) -> dict:
        if self.s.serpapi_api_key is None:
            raise UpstreamError("SERPAPI_API_KEY is not set")
        q = {k: v for k, v in params.items() if k not in REQUEST_ONLY}
        q["api_key"] = self.s.serpapi_api_key.get_secret_value()
        for attempt in (0, 1):
            try:
                r = await self.http.get(SERP_URL, params=q, timeout=HTTP_TIMEOUT.get(q["engine"], DEFAULT_TIMEOUT))
            except httpx.TimeoutException as e:
                err = UpstreamError(f"SerpApi request timed out: {type(e).__name__}")
                err.charged = True
                raise err from None
            except httpx.HTTPError as e:   # never str(e): it can carry the URL with api_key
                raise UpstreamError(f"SerpApi request failed: {type(e).__name__}") from None
            if r.status_code == 429:
                raise BudgetExhausted("SerpApi rate or plan limit")
            if r.status_code >= 500:
                if attempt == 0:
                    await asyncio.sleep(1.0)
                    continue
                break
            data = r.json()
            if is_empty_result(data):
                return data
            if r.status_code >= 400 or ("error" in data and not data.get("search_metadata")):
                raise UpstreamError(f"SerpApi {r.status_code}: {data.get('error', '')}")
            return data
        raise UpstreamError("SerpApi 5xx after retry")

    async def rdap(self, domain: str) -> dict | None:
        """RDAP lookup cached in serp_cache as engine 'rdap', no credits (D-11). None = no registration data."""
        params = {"engine": "rdap", "domain": domain}
        key = cache_key(params)
        if self.s.mode == "replay":
            row = self.repo.demo_get(key)
            if row is None:
                raise ReplayMiss("no recording for rdap")
        else:
            row = self.repo.cache_get(key, ttl_hours=self.s.cache_ttl_hours)
            if row is None:
                try:
                    r = await self.http.get(RDAP_URL.format(domain), timeout=4.0, follow_redirects=True)
                except httpx.HTTPError as e:
                    raise UpstreamError(f"RDAP failed: {type(e).__name__}") from None
                if r.status_code == 404:
                    row = {"not_found": True}
                elif r.status_code >= 400:
                    raise UpstreamError(f"RDAP {r.status_code}")
                else:
                    row = r.json()
                self.repo.cache_put(key, "rdap", params, row)
            self.repo.record_put(key, "rdap", params, row)
        return None if row.get("not_found") else row

    async def upload_image(self, jpeg: bytes) -> str:
        """Upload bytes for Google Lens; returns image_id. Not a search, so no ledger row (D-27)."""
        if self.s.mode == "replay" or self.s.serpapi_api_key is None:
            raise UpstreamError("image upload unavailable")
        try:
            r = await self.http.post(UPLOAD_URL, params={"api_key": self.s.serpapi_api_key.get_secret_value()},
                                     files={"image": ("photo.jpg", jpeg, "image/jpeg")}, timeout=30.0)
        except httpx.HTTPError as e:
            raise UpstreamError(f"Lens upload failed: {type(e).__name__}") from None
        image_id = r.json().get("image_id") if r.headers.get("content-type", "").startswith("application/json") else None
        if r.status_code >= 400 or not image_id:
            raise UpstreamError(f"Lens upload {r.status_code}")
        return image_id
