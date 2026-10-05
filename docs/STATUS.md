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
- T0.5 live spike: needs `SERPAPI_API_KEY`. The script is ready at `scripts/spike_engines.py` (6 credits).
- T0.7 frontend scaffold, T0.8 seed entities (40 verified domains): not started.
- G3 needs a consented real offer `.eml` with `dkim=pass` from the team (D-14).

**Credits used so far:** 0.

**Next three tasks**
1. Run the spike and store fixtures. Confirm the Lens `exact_matches` key and the Maps review fields.
2. T1.1 to T1.5: regexes, org resolution, amounts, redaction, eml/pdf intake, domain classification table (tests first).
3. T0.8 seeds: `known_entities.json` (≥ 40 with `source_url`), freemail, aggregators, stock, platform hosts, lure tokens, lexicons.
