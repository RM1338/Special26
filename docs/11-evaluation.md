# 11. Evaluation Plan

## 1. Questions the evaluation must answer

1. When Special26 says red, is it right? (Red precision: a false red on a real offer makes a student turn down a job.)
2. How many fraudulent offers does it catch as red or amber?
3. Does each SerpApi engine actually add something? (Ablation: proves "meaningful SerpApi usage".)
4. Does it beat the obvious alternatives: a fee keyword rule, a text classifier, an LLM asked "is this a scam"?
5. Is it fast and cheap enough?

## 2. Dataset

Target 100 cases, minimum 60. Each case is a JSON file in `eval/cases/`:

```json
{
  "case_id": "F-NEWS-007",
  "label": "fraud",
  "category": "lookalike_fee",
  "split": "holdout",
  "template_group": "tg-12",
  "source_url": "https://www.dinamalar.com/news/kalvimalar-news-en/...",
  "provenance": "transcribed_public",
  "text": "Dear <RECIPIENT>, Congratulations! ...",
  "files": ["F-NEWS-007_letter.png"],
  "confirmed_claims": null,
  "expected_tier": "red",
  "notes": "Org and amount from the article; sender domain constructed to match the described pattern"
}
```

### 2.1 Fraud cases (target 50)

| Category | Count | Source |
|----------|-------|--------|
| `public_report` | 20 | Text or screenshots published in news (§2 of `01-investigation.md`), employer fraud notices with sample messages, PIB fact-checks, r/developersIndia and r/Indian_Academia posts. Transcribed with `source_url` |
| `lookalike_fee` | 10 | Constructed from public patterns: real employer names, constructed lookalike domains (verified unregistered via RDAP at creation time), fee asks |
| `scheme_impersonation` | 6 | PM Internship, AICTE, MSME patterns with Google Forms and fees |
| `persona` | 6 | Stock-photo HR persona, free-mail sender, no fee upfront ("documents first") |
| `campaign_variants` | 8 | Same UPI/template, different brands (tests clustering) |

### 2.2 Genuine cases (target 50)

| Category | Count | Source |
|----------|-------|--------|
| `consented_real` | 15 | Real offer emails from team members, friends and seniors, with written consent, `.eml` where possible, redacted |
| `official_template` | 10 | Offer or onboarding text published by employers themselves (careers FAQ pages, sample letters) |
| `jobs_listing_message` | 15 | Real Google Jobs or Internshala listings rewritten as a recruiter message with the company's real domain |
| `small_startup` | 10 | Real small companies with little web presence (expect amber, not red; counts as correct if not red) |

### 2.3 Splits

- Split by `template_group` so near-duplicate templates never sit on both sides.
- `dev` 40%, `holdout` 60%. Weights in `08-algorithm.md` §4 are frozen before the holdout is run. On `dev` only the thresholds in §6 (3.0 red, -2.0 green, 0.40 grey) may be tuned; changes go in `docs/DECISIONS.md`.

### 2.4 Labelling

- Fraud label requires a public source or a constructed case. Genuine label requires the employer's real domain and either consent or a public employer source.
- Correct-tier mapping: fraud → `red` is correct, `amber` is a catch but not a red; genuine → `green` is ideal, `amber`/`grey` acceptable, `red` is an error.

## 3. Metrics

| Metric | Definition | Target |
|--------|------------|--------|
| Red precision | fraud ∧ red / red | ≥ 0.95 |
| Red recall | fraud ∧ red / fraud | ≥ 0.75 |
| Catch rate | fraud ∧ (red ∨ amber) / fraud | ≥ 0.90 |
| False red rate | genuine ∧ red / genuine | ≤ 0.05 |
| Green precision | genuine ∧ green / green | ≥ 0.90 |
| Green yield | genuine ∧ green / genuine (excluding `small_startup`) | ≥ 0.50 |
| Campaign purity | share of campaign pairs that truly share an operator (constructed groups) | ≥ 0.90 |
| Campaign recall | share of constructed same-operator pairs linked | ≥ 0.80 |
| p50 / p95 latency, live | wall clock POST run → verdict.ready | ≤ 25 s / ≤ 45 s |
| p50 latency, replay | | ≤ 2 s |
| Mean uncached SerpApi calls | from `credit_ledger` | ≤ 12 |

Report 95% Wilson intervals for precision and recall: with 50 cases per class the intervals are wide, and saying so is better than over-claiming.

## 4. Baselines

| ID | Baseline | Implementation |
|----|----------|----------------|
| B0 | Fee keyword rule | red if any amount with payer=candidate, else amber |
| B1 | Text classifier | TF-IDF (1-2 grams, min_df 2) + logistic regression trained on EMSCAD (`fake_job_postings.csv`), threshold at 0.5 on fraud probability; fraud → red, else green |
| B2 | LLM only | Prompt: "Here is an offer a student received. Answer RED, AMBER or GREEN and one sentence why." Temperature 0. Same text, no tools |
| B3 | Special26 local only | Only P02, P03, P11, P12 and local P10 (no SerpApi) |
| S26 | Full Special26 | All probes |

Hypotheses to confirm or reject:
- B1 will label most `lookalike_fee` and `public_report` cases as genuine, because they copy real company language.
- B0 catches fee cases but cannot produce green, and misses `persona` cases that ask for documents first.
- B3 vs S26 measures what SerpApi adds; expect the biggest gap in green yield (needs P07/P08/P09 anchors) and in `persona` cases (needs Lens).

## 5. Ablations (one engine removed at a time)

| Run | Removed | Expected effect |
|-----|---------|-----------------|
| A1 | `google` (P01, P04, P05A, P06, P10 phrase) | Lookalike detection fails without an official domain; D1 never fires |
| A2 | `google_lens` (P09) | `persona` cases drop from red to amber |
| A3 | `google_maps` (P08) | Fewer greens; residential-address cases lose a signal |
| A4 | `google_jobs` (P07) | Fewer greens |
| A5 | `google_news` + `google_forums` (P05B, P05C) | Small effect on red; scheme cases lose PIB evidence |

Output a table: metric deltas vs full run. This table goes in the README and the video.

## 6. Credit budget for evaluation

Full live run ≈ 11 calls per case. 100 cases ≈ 1,100 calls. Plan:

1. Record once: run all cases live with `SPECIAL26_RECORD_TO=data/eval.db`. If credits are short, record 40 stratified cases (≈ 450 calls) and run the remaining cases with B3 only.
2. All baselines, ablations and threshold tuning then run in replay against `eval.db`: zero extra credits, fully reproducible.
3. Ablations are computed by masking engines in replay (the runner treats a masked engine as `skipped_replay_miss`), not by re-querying.

## 7. Harness

```
python -m eval.run_eval --split holdout --mode replay --replay-db data/eval.db \
       --systems S26,B0,B1,B2,B3 --ablate google_lens,google_maps,google_jobs \
       --out eval/report.md
```

Writes `eval_runs` and `eval_results` rows and `eval/report.md` with:
- confusion matrix per system (rows: label, columns: tier)
- metrics table with Wilson intervals
- ablation delta table
- every false red, with its top 3 reasons (to debug)
- latency and credit histograms

## 8. Error analysis protocol

For each false red and each missed fraud on `dev`:
1. Which finding contributed most?
2. Was the claim extracted correctly? (If not, extraction bug, not a scoring problem.)
3. Was the SerpApi result misread? (e.g. knowledge graph for a different company with the same name)
4. Fix only extraction and parsing bugs freely. Weight changes after holdout is opened are not allowed; threshold changes only on `dev`.

## 9. Golden cases as tests

The 6 golden cases in `14-demo-plan.md` are pytest tests in `tests/golden/`, run in replay with a socket guard, asserting tier, red_kind, decisive rules and the first reason code. CI fails if any changes.
