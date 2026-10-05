# Status

## M0 Skeleton (due Mon 5 Oct 23:59 IST), 2026-10-05

**Works**
- Repo layout started (`backend/special26`), `pyproject.toml` (pytest + ruff), `backend/requirements.txt` per `05` §12, Python 3.11 venv.
- `config.py`: all `04` §9 env vars.
- `001_init.sql`: the `06` DDL verbatim. `storage/db.py` (pragmas, migrations, replay DB).
- `storage/repo.py`: cache, ledger, budget (D-06).
- `serp/client.py`:
  - cache-first, per-check and daily budget, refund on failure, one retry on 5xx, 429 → budget
  - empty-result special case
  - replay from `demo.db`, record-to
  - Lens keyed by image hash (D-12)
  - RDAP through the cache (D-11)
  - API key kept out of logs and errors
- 13 tests, offline (socket guard), 1.3 s. Ruff clean.
- `docs/CROSSCHECK.md` and `docs/DECISIONS.md` (D-01 to D-28). Lens path decided (T0.6, D-27).

**Demoable:** nothing user-facing yet.

**Behind / blocked**
- T0.7 frontend scaffold, T0.8 seed entities (40 verified domains): not started.
- G3 needs a consented real offer `.eml` with `dkim=pass` from the team (D-14).

**Credits used so far:** 7 (T0.5 spike: 5 engines plus 2 Lens calls, D-29). M0 exit criterion met: real responses for all 6 engines are stored as fixtures.

**Next three tasks**
1. T1.1 to T1.5: regexes, org resolution, amounts, redaction, eml/pdf intake, domain classification table (tests first).
2. T0.8 seeds: `known_entities.json` (≥ 40 with `source_url`), freemail, aggregators, stock, platform hosts, lure tokens, lexicons.
3. T1.6 to T1.10: probe base, weights.yaml, copy, P01, P02, P11, scorer, worked-example test, CLI (M1).

## M1 Core logic (due Tue 6 Oct 23:59 IST), done 2026-10-05

**Works**
- Seeds (T0.8): 54 companies and 6 schemes, all verified over HTTPS (D-30). `bank.in` handled. Freemail, aggregator, stock, platform, lure, lexicon and city lists.
- Claim extraction (T1.1 to T1.4, except `.eml`/PDF intake): every `08` §2.1 type, plus redaction. ≥ 3 positive and 2 negative tests per type. All golden inputs extract as expected.
- Domain classification (T1.5): all 12 rows of the `05` §5 table plus 11 extras.
- Probe base, `weights.yaml` (46 codes, `08` order), copy for every code and decisive rule, startup ruleset check (T1.6).
- P01 (on the live fixture), P02, P11: one test per finding code (T1.7, T1.8).
- Scorer (T1.9): the worked example passes exactly (S = 8.0, D1 + D3, red, impersonation, strength 0.62, reasons in `08` order). Also: determinism over 100 shuffled runs, green gate, grey, D2, D4.
- Runner with dependency scheduling and failure statuses. CLI (T1.10): `PYTHONPATH=backend .venv/bin/python -m special26.cli check backend/tests/golden/inputs/g1.txt` prints RED (impersonation) with D3. D1 arrives with P04 in M2.
- 260 tests offline in about 2 s. 91% line coverage overall; claims, domains, probes and scoring are 94 to 100%.

**Demoable:** the CLI verdict for G1, G2 and G4.

**Behind**
- T1.4 `.eml` and PDF intake: moved to the start of M2 (needed by the API).
- T1.11 and T1.12 frontend components: not started (lane B).
- Seed target of 80 companies: 54 so far.

**Credits used so far:** 7, unchanged (the G1 CLI run was served from cache).

**Next three tasks**
1. Intake (`.eml`, PDF, images), then the API: create, PUT claims, run, GET, error envelope, rate limit (T2.1).
2. Pipeline persistence and events, SSE with `Last-Event-ID`, then P04 + D1 (T2.2 to T2.4).
3. Frontend scaffold and the four screens wired to the API, then deploy (T0.7, T2.5 to T2.7) for M2 on Wed 7 Oct 21:00.

## M2 Vertical slice (due Wed 7 Oct 21:00 IST), done 2026-10-05

**Works**
- Intake (T1.4): `.eml` (auth results, HTML or plain body), PDF text and images, images resized with EXIF stripped and pHash, Lens sizing, optional OCR.
- API (T2.1): create, edit claims, run, read, health. Every `07` §9 error code has a test.
- Pipeline (T2.2): persists each probe before its event, then scores, saves the verdict, purges raw data.
- SSE with `Last-Event-ID` (T2.3).
- P04 + D1 (T2.4): Google ignored every site-restricted query we tried, so P04 filters results to official domains and falls back to the employer's verified notice (D-34).
- Frontend (T0.7, T1.11, T1.12, T2.5, T2.6): Home, Confirm, live timeline, verdict card, receipt slip, next steps. Checked in Chromium at 360 px with no horizontal scroll.
- Dockerfile for Railway (T2.7, D-33). Railway CLI installed.
- G1 end to end through the API (replay test) and in the browser (live, from cache): red, impersonation, D1 + D3, reason 1 = D1.
- 284 backend tests in about 5 s.

**Deployed:** https://web-production-4b8c8.up.railway.app (Railway project `special26`, service `web`, volume at `/app/data`, live mode).

**M2 exit met:** G1 run in a real browser (360 px) on the public URL, live. Red, impersonation, D1 + D3, reasons with clickable receipts. Verdict 3.9 s after "Run checks". 2 SerpApi credits (P01 1.7 s, P04).

**Demoable:** the full G1 flow on the public URL.

**Blocked on the user**
- The local Docker daemon isn't reachable (the user isn't in the `docker` group), so the image builds only on Railway for now. M5's offline `docker run` check needs local Docker.
- G3 consented `.eml` (D-14).

**Credits used so far:** 17 (15 local, 2 on the deployed G1 run; 8 of them on the D-34 site-restriction investigation).

**Next three tasks**
1. P07, P08, P09 (Lens upload path, D-27), P03, P10, P06, P05 (T3.1 to T3.8).
2. Share token, share page with OG tags (D-18), campaigns.
3. Scam template seed corpus (≥ 25) and eval cases (lane B).
