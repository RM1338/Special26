"""FR-22, FR-23, FR-26, NFR-07."""
import json
import logging

import httpx
import pytest

from special26.errors import BudgetExhausted, ReplayMiss, UpstreamError
from special26.serp.client import SerpClient, cache_key


def client_with(settings, repo, handler):
    calls = []

    def h(request):
        calls.append(request)
        return handler(request)
    return SerpClient(settings, repo, httpx.AsyncClient(transport=httpx.MockTransport(h))), calls


def ok(request):
    return httpx.Response(200, json={"search_metadata": {"id": "x"}, "organic_results": [{"position": 1}]})


def test_cache_key_ignores_api_key_and_order():
    assert cache_key({"q": "a", "engine": "google", "api_key": "k1"}) == cache_key({"engine": "google", "q": "a"})


def test_lens_key_uses_image_sha_not_url():  # D-12
    a = {"engine": "google_lens", "url": "https://x/img/tok1", "image_sha256": "ab", "type": "exact_matches"}
    b = {**a, "url": "https://x/img/tok2"}
    assert cache_key(a) == cache_key(b)


async def test_second_call_hits_cache(settings, repo, check_id, db):
    c, calls = client_with(settings, repo, ok)
    _, k1, hit1 = await c.search(check_id, {"engine": "google", "q": "Tech Mahindra"})
    _, k2, hit2 = await c.search(check_id, {"engine": "google", "q": "Tech Mahindra"})
    assert (hit1, hit2) == (False, True) and k1 == k2 and len(calls) == 1
    rows = db.execute("SELECT cached, status FROM credit_ledger ORDER BY id").fetchall()
    assert [tuple(r) for r in rows] == [(0, "spent"), (1, "spent")]


async def test_15th_uncached_call_refused(settings, repo, check_id):
    c, calls = client_with(settings, repo, ok)
    for i in range(14):
        await c.search(check_id, {"engine": "google", "q": f"q{i}"})
    with pytest.raises(BudgetExhausted):
        await c.search(check_id, {"engine": "google", "q": "q14"})
    assert len(calls) == 14


async def test_daily_cap(settings, repo):
    settings.daily_credit_cap = 2
    c, _ = client_with(settings, repo, ok)
    await c.search(None, {"engine": "google", "q": "a"})
    await c.search(None, {"engine": "google", "q": "b"})
    with pytest.raises(BudgetExhausted):
        await c.search(None, {"engine": "google", "q": "c"})


async def test_failed_call_is_refunded(settings, repo, check_id, db):
    c, calls = client_with(settings, repo, lambda r: httpx.Response(503))
    with pytest.raises(UpstreamError):
        await c.search(check_id, {"engine": "google", "q": "a"})
    assert len(calls) == 2  # one retry on 5xx
    assert db.execute("SELECT status FROM credit_ledger").fetchone()[0] == "refunded"


async def test_429_is_budget(settings, repo, check_id):
    c, _ = client_with(settings, repo, lambda r: httpx.Response(429, json={"error": "limit"}))
    with pytest.raises(BudgetExhausted):
        await c.search(check_id, {"engine": "google", "q": "a"})


async def test_empty_result_is_success(settings, repo, check_id):
    body = {"search_metadata": {"status": "Success"}, "error": "Google hasn't returned any results for this query."}
    c, _ = client_with(settings, repo, lambda r: httpx.Response(200, json=body))
    data, _, _ = await c.search(check_id, {"engine": "google", "q": "zzz"})
    assert "organic_results" not in data


async def test_replay_reads_demo_db_and_misses(settings, repo):
    settings.mode = "replay"
    params = {"gl": "in", "hl": "en", "engine": "google", "q": "x"}
    repo.replay.execute("INSERT INTO serp_cache VALUES (?, 'google', '{}', ?, '2026-10-09T00:00:00Z', 2)",
                        (cache_key(params), json.dumps({"organic_results": []})))
    c, calls = client_with(settings, repo, ok)
    data, _, hit = await c.search(None, {"engine": "google", "q": "x"})
    assert hit and data == {"organic_results": []} and not calls
    with pytest.raises(ReplayMiss):
        await c.search(None, {"engine": "google", "q": "other"})


async def test_record_to_copies_used_responses(settings, repo, tmp_path):
    from special26.storage.db import connect_replay
    repo.record = connect_replay(str(tmp_path / "rec.db"))
    c, _ = client_with(settings, repo, ok)
    await c.search(None, {"engine": "google", "q": "a"})
    await c.search(None, {"engine": "google", "q": "a"})
    assert repo.record.execute("SELECT COUNT(*) FROM serp_cache").fetchone()[0] == 1


async def test_api_key_never_logged_or_in_errors(settings, repo, caplog):
    caplog.set_level(logging.DEBUG)

    def boom(request):
        assert request.url.params["api_key"] == "SECRET-KEY-123"
        raise httpx.ConnectError(f"failed {request.url}")
    c, _ = client_with(settings, repo, boom)
    with pytest.raises(UpstreamError) as e:
        await c.search(None, {"engine": "google", "q": "a"})
    assert "SECRET" not in str(e.value) and "SECRET" not in caplog.text


async def test_timeout_is_charged_not_refunded(settings, repo, check_id, db):  # D-29
    def slow(request):
        raise httpx.ReadTimeout("slow")
    c, _ = client_with(settings, repo, slow)
    with pytest.raises(UpstreamError):
        await c.search(check_id, {"engine": "google_lens", "url": "u", "image_sha256": "a", "type": "exact_matches"})
    assert db.execute("SELECT status FROM credit_ledger").fetchone()[0] == "spent"


def test_lens_empty_result_fixture_is_empty():
    from pathlib import Path

    from special26.serp.client import is_empty_result
    d = json.loads((Path(__file__).parents[1] / "fixtures/serp/google_lens_exact_empty.json").read_text())
    assert is_empty_result(d)


async def test_masked_engine_is_a_replay_miss(settings, repo):  # 11 §6 ablations
    settings.masked_engines = ["google_lens"]
    c, calls = client_with(settings, repo, ok)
    with pytest.raises(ReplayMiss):
        await c.search(None, {"engine": "google_lens", "url": "u", "image_sha256": "a", "type": "exact_matches"})
    assert calls == []
