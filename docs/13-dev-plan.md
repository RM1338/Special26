# 13. Development Plan and Task Breakdown

Window: Monday 5 Oct 2026 evening to Saturday 10 Oct 2026. All times IST.

| Milestone | When | Exit criterion |
|-----------|------|----------------|
| M0 Skeleton | Mon 5 Oct, 23:59 | Repo, DB migrations, SerpClient with cache and budget, one real SerpApi call stored |
| M1 Core logic | Tue 6 Oct, 23:59 | Claims + P01 + P02 + P11 + scorer pass unit tests; CLI prints a verdict for G1 |
| **M2 Vertical slice** | **Wed 7 Oct, 21:00** | Browser: paste G1 → confirm → live timeline → red verdict card with receipts, on the deployed URL |
| M3 Full probes | Thu 8 Oct, 23:59 | P03 to P10 live; campaigns; 60 eval cases collected |
| **M4 Feature freeze** | **Fri 9 Oct, 12:00** | MVP definition of done in `12-mvp-scope.md` §5, except video |
| M5 Eval + replay recorded | Fri 9 Oct, 23:59 | `eval/report.md`, `demo.db` recorded, Docker image pushed |
| **M6 Submitted** | **Sat 10 Oct, 18:00** | Website entry, public repo, video < 3 min public. 18:00 to 23:59 only for video or link fixes |

Two lanes. **A** = backend and algorithm. **B** = frontend, data, eval, video. Solo: do lane A tasks first each day, then lane B; the order inside each day already respects dependencies.

## Monday 5 Oct (evening, about 5 hours)

| ID | Lane | Task | Est | Depends | Done when |
|----|------|------|-----|---------|-----------|
| T0.1 | A | Repo layout from `05-LLD.md` §1, `pyproject`, `requirements.txt`, ruff, pytest, pre-commit | 0.5h | | `pytest` runs (0 tests) |
| T0.2 | A | `config.py` with all env vars from `04` §9 | 0.5h | T0.1 | Settings load with defaults |
| T0.3 | A | `001_init.sql`, `storage/db.py` (pragmas), `repo.py` stubs | 1h | T0.1 | Migration creates all tables in a temp DB |
| T0.4 | A | `SerpClient` with cache key, cache, ledger, budget reserve, retry, empty-result special case, replay read, record-to | 2h | T0.3 | Tests: second call hits cache; 15th uncached call raises `BudgetExhausted`; replay miss raises |
| T0.5 | A | Spike: one live call per engine (`google`, `google_news`, `google_forums`, `google_jobs`, `google_maps`, `google_lens`), save JSON to `tests/fixtures/serp/` | 1h | T0.4 | 6 fixture files; note any field names differing from the docs in `DECISIONS.md` |
| T0.6 | A | Confirm Lens image path: SerpApi image upload vs signed URL; write the decision | 0.5h | T0.5 | `DECISIONS.md` entry |
| T0.7 | B | Frontend scaffold: Vite + React + TS + Tailwind + React Query, routes from `07` §10 | 1h | | `npm run dev` shows 4 empty pages |
| T0.8 | B | Collect seed data: 40 known entities with verified official domains and `source_url` | 2h | | `known_entities.json` validates |

## Tuesday 6 Oct

| ID | Lane | Task | Est | Depends | Done when |
|----|------|------|-----|---------|-----------|
| T1.1 | A | `claims/regexes.py` + tests (≥ 3 positive, 2 negative per type) | 1.5h | T0.1 | Tests pass |
| T1.2 | A | `claims/org.py`: Aho-Corasick over seeds, legal-line, pattern, display name | 1.5h | T0.8, T1.1 | G1 to G6 texts resolve the expected org |
| T1.3 | A | `claims/amounts.py` purpose and payer classifier | 1h | T1.1 | "₹2,000 for police clearance" → verification, candidate; "stipend ₹15,000/month" → stipend, employer |
| T1.4 | A | `claims/redact.py` + `intake/eml.py` + `intake/pdf.py` | 1.5h | T1.1 | Fixture `.eml` parsed incl. Authentication-Results; recipient redacted |
| T1.5 | A | `domains/classify.py` + the 12-row test table in `05` §5 | 1.5h | T0.1 | All 12 rows pass |
| T1.6 | A | `probes/base.py`, `weights.yaml`, `scoring/copy.py`, startup check that every code has a weight and copy | 1h | | App refuses to start on a missing code |
| T1.7 | A | P01_ENTITY with candidate scoring | 1.5h | T0.4, T1.6 | On fixtures: Tech Mahindra → `techmahindra.com`; a fake name → `P01_NO_PRESENCE` |
| T1.8 | A | P02_SENDER, P11_POLICY | 1.5h | T1.5, T1.7 | Unit tests per finding code |
| T1.9 | A | `scoring/aggregate.py` + worked example test (`08` §6.1 must give S = 8.0, D1 + D3, red, impersonation) | 1.5h | T1.6 | Test passes exactly |
| T1.10 | A | CLI `python -m special26.cli check fixtures/g1.txt` | 0.5h | T1.9 | Prints tier and reasons |
| T1.11 | B | `ClaimEditor` against a mocked create response | 2h | T0.7 | All groups editable, "This is mine" works |
| T1.12 | B | `VerdictCard`, `ReceiptDrawer`, `NextSteps` against the mocked `GET` response in `07` §4 | 3h | T0.7 | Matches `09` copy exactly |
| T1.13 | B | Write G1 to G6 input texts and assets (`14-demo-plan.md` §3) | 1.5h | | Files in `tests/golden/inputs/` |

## Wednesday 7 Oct (vertical slice day)

| ID | Lane | Task | Est | Depends | Done when |
|----|------|------|-----|---------|-----------|
| T2.1 | A | API: `POST /api/checks`, `PUT claims`, `POST run`, `GET check`, error envelope, rate limit | 2h | T1.10 | httpx tests for each error code in `07` §9 |
| T2.2 | A | Pipeline runner with waves, timeouts, statuses, events table | 1.5h | T2.1 | G1 runs through the API |
| T2.3 | A | SSE endpoint with `Last-Event-ID` | 1h | T2.2 | Reconnect replays missed events |
| T2.4 | A | P04_FRAUD_NOTICE + D1 | 1h | T1.7 | Live: Tech Mahindra notice found; D1 fires for G1 |
| T2.5 | B | Wire Home → Confirm → Timeline → Verdict to the real API | 3h | T2.1, T2.3 | G1 in the browser |
| T2.6 | B | `ProbeTimeline` with engine badges and live region | 1.5h | T2.3 | |
| T2.7 | A+B | Dockerfile, deploy to Render/Railway, set env, public URL | 1.5h | T2.5 | **M2: G1 red on the deployed URL by 21:00** |

If M2 slips past 21:00, cut T3.8 (Forums) and T3.10 (P12) tomorrow.

## Thursday 8 Oct

| ID | Lane | Task | Est | Depends | Done when |
|----|------|------|-----|---------|-----------|
| T3.1 | A | P07_ROLE (Google Jobs) | 1h | T1.7 | Fixture match test; G3 gets `P07_ROLE_LISTED` |
| T3.2 | A | P08_OFFICE (Google Maps) | 1.5h | T1.7 | Residential and match cases tested |
| T3.3 | A | P09_IMAGE (Lens exact matches for HR photo), image endpoint or upload | 2h | T0.6 | G5 stock photo → `P09_STOCK_PHOTO` |
| T3.4 | A | P03_HEADERS incl. forwarded detection | 1h | T1.4 | G3 `.eml` → `P03_DKIM_ALIGNED_OFFICIAL` |
| T3.5 | A | Template: normalise, MinHash, LSH, seed corpus loader; P10 local + phrase | 2h | T0.3 | Seed template self-match J = 1.0; paraphrase J in [0.4, 0.8] |
| T3.6 | A | P06_IDENTIFIER_TRACE + identifiers table + local memory | 1.5h | T2.2 | G6 second offer gets `P06_ID_SEEN_LOCALLY` |
| T3.7 | A | Campaign linking + `GET /api/campaigns/{id}` | 1.5h | T3.5, T3.6 | G6 two offers in one campaign |
| T3.8 | A | P05_CHATTER (Google + News; Forums optional) | 1h | T1.6 | Degrades when forums errors |
| T3.9 | B | Share token, share page, masking, OG tags | 2h | T2.5 | WhatsApp preview shows headline |
| T3.10 | A | P12_DOMAIN_AGE (stretch) | 0.5h | T1.5 | |
| T3.11 | B | Eval cases: 30 fraud + 30 genuine in `eval/cases/` | 4h | | Schema-valid JSON, sources recorded |
| T3.12 | B | Campaign page | 1h | T3.7 | |

## Friday 9 Oct (freeze at 12:00)

| ID | Lane | Task | Est | Depends | Done when |
|----|------|------|-----|---------|-----------|
| T4.1 | A | Golden tests G1 to G6 in replay with socket guard | 1.5h | all probes | CI green |
| T4.2 | A | `scripts/record_demo.py`: live run of golden cases → `demo.db` | 0.5h | T4.1 | Replay reproduces identical verdicts |
| T4.3 | B | Polish: copy audit against `09`, mobile pass at 360 px, em dash grep | 2h | | |
| **Freeze** | | **12:00. Only bug fixes after this.** | | | |
| T4.4 | A | Record eval responses to `eval.db` (budget per `11` §6) | 1.5h | T3.11 | |
| T4.5 | A | `eval/run_eval.py`: S26, B0, B3, ablations A1 to A5, report.md | 2.5h | T4.4 | Report generated |
| T4.6 | A | Threshold tuning on dev only, `DECISIONS.md` | 1h | T4.5 | Holdout run once after |
| T4.7 | B | README: problem + sources, GIF, run instructions, engine table, eval table, limitations | 2h | T4.5 | |
| T4.8 | B | Video script dry run with replay (`14-demo-plan.md`) | 1h | T4.2 | Under 2:50 |
| T4.9 | A | Push Docker image with replay data; test `docker run` on a clean machine | 1h | T4.2 | **M5** |

## Saturday 10 Oct

| Time | Task |
|------|------|
| 09:00 to 12:00 | Record video (screen + voice), 2 takes, edit to ≤ 2:55 |
| 12:00 to 13:00 | Upload video (public), check it plays logged out |
| 13:00 to 15:00 | Final README pass, repo public, license, topics, `#BuiltWithSerpApi` |
| 15:00 to 17:00 | Submission form on the hackathon site; verify every link from a phone on mobile data |
| **18:00** | **Submitted.** After this only video re-upload or link fixes until 23:59 |

## Risk register

| Risk | Likelihood | Impact | Trigger | Response |
|------|-----------|--------|---------|----------|
| SerpApi credits run out | Medium | High | `credits_today` > 70% of plan before Fri | Switch dev to replay, record only golden + 40 eval cases |
| Lens cannot fetch images on host | Medium | High | T3.3 fails | Use SerpApi upload path; if both fail, demo P09 from replay recorded on a machine where it worked |
| Knowledge graph picks the wrong company for ambiguous names | Medium | Medium | Eval false reds | Prefer seed entities; add city to Q1 when org < 6 chars |
| Short-brand false combosquat (e.g. `tcs`) | Medium | High | Genuine sister domains flagged | Seed sister domains; lure-only leftover rule; test table |
| Google Forums down | High | Low | errors | Already optional |
| OCR missing on host | Low | Low | | Paste-text prompt |
| Deploy host sleeps on free tier | High | Medium | Cold start > 30 s | Ping before judging windows; replay Docker as fallback |
