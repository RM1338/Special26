# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Status

Docs-only so far: the repo holds design docs in `docs/` and no code yet. The layout, commands and names below are the **planned** design from `docs/05-LLD.md` and `docs/13-dev-plan.md`. Build to them; don't invent alternatives. Hackathon deadline: feature freeze Fri 9 Oct 2026 12:00 IST, submission Sat 10 Oct 2026 18:00 IST. `docs/12-mvp-scope.md` lists what's in, out, stretch, and the cut order.

## What it is

Special26 checks an internship or job offer that an Indian student received and returns a verdict card (`red`/`amber`/`green`/`grey`). Each claim in the offer (org, sender domain, HR person, address, role, payment ask) is checked against SerpApi results (google, google_news, google_forums, google_jobs, google_maps, google_lens), and every finding carries a receipt.

## Docs: source of truth

Precedence when docs disagree: `08-algorithm` > `06-data-model` > `07-api-contract` > `05-LLD` > `03-SRS` > the rest. Record each conflict with its date and resolution in `docs/DECISIONS.md`.
- `08`: probe IDs, finding codes, weights, thresholds, decisive rules, verdict rules. The G1 worked example in §6.1 must score S = 8.0, fire D1 + D3, and come out red/impersonation.
- `06`: table and column names (DDL goes in `backend/special26/storage/migrations/001_init.sql`).
- `07`: endpoint paths, JSON field names, SSE events, error codes, frontend routes, TS types.
- `docs/00-README.md`: canonical names (package `special26`, `Special26Error`, env prefix `SPECIAL26_` plus `SERPAPI_API_KEY`, probe IDs `P01_ENTITY`..`P12_DOMAIN_AGE`, decisive rules `D1`..`D4`, evidence families). Use them exactly.

## Architecture (big picture)

One process, one container: FastAPI serves the API, SSE and the built React app. SQLite runs in WAL mode. Each check runs as a background task. There is no queue or worker by design.

- **Pipeline**: intake (PDF/OCR/.eml) → claim extraction (regex + Aho-Corasick dictionary; LLM fallback off by default) → user confirms or edits claims → probes in two waves → scorer → template fingerprint/campaign linking → DB. Wave 1 runs in parallel: P01, P03, P05, P06, P09, P10, P11, P12. Wave 2 waits for P01's official domain set: P02, P04, P07, P08. At most 4 SerpApi calls in flight.
- **Probes** subclass `Probe` (`probes/base.py`) with `applicable()` → a `skipped_*` status or None, and an async `run()` → `ProbeResult`. Findings are built only through `Probe.finding()`, which pulls weight and family from `rules/weights.yaml` and message text from `scoring/copy.py`. Never compute weights ad hoc. The app refuses to start if a finding code lacks a weight or copy.
- **SerpClient** (`serp/`): all SerpApi traffic goes through it. Cache key is sha256 of the canonical params minus api_key, TTL 72h. A per-check credit budget (14) and a daily cap (200) raise `BudgetExhausted`. In `replay` mode it reads `data/demo.db` and raises `ReplayMiss` on a miss, with no network. `SPECIAL26_RECORD_TO` copies the responses it uses into a replay DB.
- **Scorer** (`scoring/aggregate.py`) is pure: family caps, decisive rules checked before thresholds, tiers, red_kind, reasons, coverage. A probe failure lowers coverage but never stops the check.
- **Campaigns**: MinHash/LSH template signatures, plus union-find over shared UPI IDs, phones, domains, emails and templates.
- **Lens image path**: SerpApi image upload first. Fallback is a signed `/public/img/{token}` URL, which needs `SPECIAL26_PUBLIC_BASE_URL`. With neither, P09 returns `skipped_no_public_url`.
- **Privacy**: raw files and text are deleted when a check reaches a terminal state (`done`/`failed`/`expired`).

## Planned commands

```bash
pytest                                                # backend tests (tests/conftest.py adds a socket guard + temp DB)
pytest backend/tests/unit/test_<module>.py -k <name>  # single test
pytest backend/tests/golden                           # G1..G6 in replay; CI fails if tier/red_kind/decisive/first reason change
ruff check .
python -m special26.cli check fixtures/g1.txt         # CLI verdict
uvicorn special26.main:app --host 0.0.0.0 --port 8000
cd frontend && npm run dev                            # Vite + React + TS + Tailwind + React Query
python scripts/record_demo.py                         # live golden run -> data/demo.db
python -m eval.run_eval --split holdout --mode replay --replay-db data/eval.db \
  --systems S26,B0,B3 --ablate google_lens,google_maps,google_jobs --out eval/report.md
docker run -e SPECIAL26_MODE=replay -p 8000:8000 <image>   # no API key needed
```

Use replay mode for development and tests to save SerpApi credits. The env vars are listed in `docs/04-architecture.md` §9.

## Rules

- No em dashes anywhere in UI copy, README or docs (`grep -rnP '\x{2014}' frontend/src README.md` must return nothing).
- Never print "This is a scam" or "Safe". Use the verdict copy in `docs/09-user-flow.md`.
- Every finding the user sees has a receipt (SerpApi result) or is marked `local_rule`. Every number in the UI links to its receipt.
- No ML classifier inside the verdict. An LLM may only be used where `08` §10 allows it.
- Eval: tune thresholds on `dev` only. After the holdout split is opened, weights must not change.
