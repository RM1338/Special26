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

## M3 Full probes (due Thu 8 Oct 23:59 IST), progress at 2026-10-06

**Works** (deployed: https://web-production-4b8c8.up.railway.app)
- All 11 MVP probes are live: P01, P02, P03, P04, P05 (Google, News, Forums), P06, P07 (Jobs), P08 (Maps), P09 (Lens via SerpApi upload), P10 (MinHash/LSH + quoted sentence), P11.
- **Full G1 live run:** red, impersonation, D1 + D3, S = 6.0, coverage 1.0, 7 credits, verdict in 7.9 s.
- Template fingerprinting, identifiers, union-find campaigns, `/api/campaigns/{id}`. G6a + G6b link into one campaign (Infosys, HCLTech) in replay.
- Share tokens and the masked share page with WhatsApp OG tags. Campaign page. Verdict links to its campaign.
- Reason ordering now follows the verdict's direction (D-44).
- 329 backend tests in about 5 s.

**Behind**
- T3.11: 60 eval cases. Not started; needs sourcing from public reports.
- Seed scam template corpus (≥ 25, `08` §7.5): empty, so P10's local part matches only earlier red checks.
- P12 (stretch): not started.
- G3 consented `.eml`: still pending (D-14).

**Credits used so far:** 31 (17 earlier, 1 for the Lens upload spike, 13 on the deployed server today, including two full G1 runs).

**Next three tasks**
1. Seed scam templates (≥ 25 transcribed public texts with source URLs).
2. Eval cases (30 fraud + 30 genuine, `11` §2), schema-valid with sources.
3. P12 RDAP (stretch), then the golden tests in replay and the `demo.db` recording (M5).

## M3 done / M5 partly done, 2026-10-06

**Since the last update**
- **P12 (RDAP domain age)** built.
- **Per-claim "what we found" view**, after the user's own offer letter showed the extracted website was never reported back (D-45).
- **Seed corpus:** 27 constructed scam texts, each following a cited report. Receipts say "pattern described in a public report", never "known text" (D-46, D-47).
- **Eval:** 60 constructed cases, 30 fraud and 30 genuine, split 40/60 by template group. Harness `eval/run_eval.py` covers S26, B0, B3, ablations, Wilson CIs, false reds, latency and credits (D-49).
  - B0 so far: catch rate 1.00, red recall 0.73.
  - B3 so far: red recall 0.90, no false reds; all genuine cases grey (no coverage without search).
- **Golden G1, G2, G4, G5, G6a and G6b recorded live into `data/demo.db`** (46 credits; 50 responses). All `14` §3 invariants hold, and the replay tests pass offline in 2.4 s. G3 stays a strict xfail.
- P01 and P10 keep local evidence when search is unavailable (D-48). The G2 contact links to `pminternship.mca.gov.in` (D-50).
- 340 tests pass, 1 xfail.

**Credits:** SerpApi Free Plan, **54 searches left** this month (196 used). The deployed daily cap is 15 (D-47) until the user confirms more credits.

**Blocked on the user**
- More SerpApi credits, needed to record S26 for the 60 eval cases (about 540 searches; `11` §6's fallback of 40 stratified cases is about 360).
- The `docker` group for the M5 offline `docker run` check.
- G3 consented `.eml`.

**Next three tasks**
1. README (T4.7): the problem with sources, the GIF, run instructions for live and replay, the engine table, the eval table, limitations.
2. Copy audit, em dash grep and mobile pass (T4.3).
3. S26 eval recording and report once credits arrive. Until then the report shows B0 and B3 only.
