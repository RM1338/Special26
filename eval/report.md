## Part 1: all 60 cases, credit-free systems (B0, B3)

Generated 2026-10-05 19:45 UTC. Ruleset `2026.10.1`. Split `all`: 60 cases (30 fraud, 30 genuine). Mode `replay`.

All cases are constructed (see `eval/build_cases.py` and `docs/DECISIONS.md` D-49). Intervals are 95% Wilson intervals; with this many cases they are wide, and that is the honest reading.

## Metrics

| system | red precision | red recall | catch rate | false red rate | green precision | green yield |
|---|---|---|---|---|---|---|
| B0 | 1.00 [0.86, 1.00] | 0.77 [0.59, 0.88] | 1.00 [0.89, 1.00] | 0.00 [0.00, 0.11] | n/a | 0.00 [0.00, 0.14] |
| B3 | 1.00 [0.88, 1.00] | 0.93 [0.79, 0.98] | 0.93 [0.79, 0.98] | 0.00 [0.00, 0.11] | n/a | 0.00 [0.00, 0.14] |

B1 (EMSCAD TF-IDF) and B2 (LLM only) are stretch baselines (`12` §3) and were not run.

### Confusion: B0

| label | red | amber | green | grey |
|---|---|---|---|---|
| fraud | 23 | 7 | 0 | 0 |
| genuine | 0 | 30 | 0 | 0 |

### Confusion: B3

| label | red | amber | green | grey |
|---|---|---|---|---|
| fraud | 28 | 0 | 0 | 2 |
| genuine | 0 | 0 | 0 | 30 |

## False reds: B0

- none

## False reds: B3

- none

## Per case

| case | label | category | expected | B0 | B3 |
|---|---|---|---|---|---|
| F-CMP-01a | fraud | campaign_variants | red | red | red |
| F-CMP-01b | fraud | campaign_variants | red | red | red |
| F-CMP-02a | fraud | campaign_variants | red | red | red |
| F-CMP-02b | fraud | campaign_variants | red | red | red |
| F-CMP-03a | fraud | campaign_variants | red | red | red |
| F-CMP-03b | fraud | campaign_variants | red | red | red |
| F-LKF-01 | fraud | lookalike_fee | red | red | red |
| F-LKF-02 | fraud | lookalike_fee | red | red | red |
| F-LKF-03 | fraud | lookalike_fee | red | red | red |
| F-LKF-04 | fraud | lookalike_fee | red | red | red |
| F-LKF-05 | fraud | lookalike_fee | red | red | red |
| F-LKF-06 | fraud | lookalike_fee | red | red | red |
| F-PER-01 | fraud | persona | amber | amber | red |
| F-PER-02 | fraud | persona | amber | amber | red |
| F-PER-03 | fraud | persona | amber | amber | red |
| F-PER-04 | fraud | persona | amber | amber | red |
| F-RPT-01 | fraud | public_report | red | red | red |
| F-RPT-02 | fraud | public_report | red | red | red |
| F-RPT-03 | fraud | public_report | red | red | red |
| F-RPT-04 | fraud | public_report | red | amber | grey |
| F-RPT-05 | fraud | public_report | red | red | red |
| F-RPT-06 | fraud | public_report | red | amber | grey |
| F-RPT-07 | fraud | public_report | red | red | red |
| F-RPT-08 | fraud | public_report | red | red | red |
| F-RPT-09 | fraud | public_report | red | red | red |
| F-RPT-10 | fraud | public_report | red | red | red |
| F-SCH-01 | fraud | scheme_impersonation | red | red | red |
| F-SCH-02 | fraud | scheme_impersonation | red | red | red |
| F-SCH-03 | fraud | scheme_impersonation | red | amber | red |
| F-SCH-04 | fraud | scheme_impersonation | red | red | red |
| G-JOB-01 | genuine | jobs_listing_message | green | amber | grey |
| G-JOB-02 | genuine | jobs_listing_message | green | amber | grey |
| G-JOB-03 | genuine | jobs_listing_message | green | amber | grey |
| G-JOB-04 | genuine | jobs_listing_message | green | amber | grey |
| G-JOB-05 | genuine | jobs_listing_message | green | amber | grey |
| G-JOB-06 | genuine | jobs_listing_message | green | amber | grey |
| G-JOB-07 | genuine | jobs_listing_message | green | amber | grey |
| G-JOB-08 | genuine | jobs_listing_message | green | amber | grey |
| G-JOB-09 | genuine | jobs_listing_message | green | amber | grey |
| G-JOB-10 | genuine | jobs_listing_message | green | amber | grey |
| G-JOB-11 | genuine | jobs_listing_message | green | amber | grey |
| G-JOB-12 | genuine | jobs_listing_message | green | amber | grey |
| G-JOB-13 | genuine | jobs_listing_message | green | amber | grey |
| G-JOB-14 | genuine | jobs_listing_message | green | amber | grey |
| G-JOB-15 | genuine | jobs_listing_message | green | amber | grey |
| G-JOB-16 | genuine | jobs_listing_message | green | amber | grey |
| G-OFF-01 | genuine | official_template | green | amber | grey |
| G-OFF-02 | genuine | official_template | green | amber | grey |
| G-OFF-03 | genuine | official_template | green | amber | grey |
| G-OFF-04 | genuine | official_template | green | amber | grey |
| G-OFF-05 | genuine | official_template | green | amber | grey |
| G-OFF-06 | genuine | official_template | green | amber | grey |
| G-OFF-07 | genuine | official_template | green | amber | grey |
| G-OFF-08 | genuine | official_template | green | amber | grey |
| G-SUP-01 | genuine | small_startup | amber | amber | grey |
| G-SUP-02 | genuine | small_startup | amber | amber | grey |
| G-SUP-03 | genuine | small_startup | amber | amber | grey |
| G-SUP-04 | genuine | small_startup | amber | amber | grey |
| G-SUP-05 | genuine | small_startup | amber | amber | grey |
| G-SUP-06 | genuine | small_startup | amber | amber | grey |

## Part 2: recorded subset (13 cases), full system S26 with ablations

Generated 2026-10-05 19:45 UTC. Ruleset `2026.10.1`. Split `all`: 13 cases (7 fraud, 6 genuine). Mode `replay`.

All cases are constructed (see `eval/build_cases.py` and `docs/DECISIONS.md` D-49). Intervals are 95% Wilson intervals; with this many cases they are wide, and that is the honest reading.

## Metrics

| system | red precision | red recall | catch rate | false red rate | green precision | green yield |
|---|---|---|---|---|---|---|
| S26 | 1.00 [0.65, 1.00] | 1.00 [0.65, 1.00] | 1.00 [0.65, 1.00] | 0.00 [0.00, 0.39] | 1.00 [0.34, 1.00] | 0.40 [0.12, 0.77] |
| B0 | 1.00 [0.61, 1.00] | 0.86 [0.49, 0.97] | 1.00 [0.65, 1.00] | 0.00 [0.00, 0.39] | n/a | 0.00 [0.00, 0.43] |
| B3 | 1.00 [0.61, 1.00] | 0.86 [0.49, 0.97] | 0.86 [0.49, 0.97] | 0.00 [0.00, 0.39] | n/a | 0.00 [0.00, 0.43] |

B1 (EMSCAD TF-IDF) and B2 (LLM only) are stretch baselines (`12` §3) and were not run.

### Confusion: S26

| label | red | amber | green | grey |
|---|---|---|---|---|
| fraud | 7 | 0 | 0 | 0 |
| genuine | 0 | 4 | 2 | 0 |

### Confusion: B0

| label | red | amber | green | grey |
|---|---|---|---|---|
| fraud | 6 | 1 | 0 | 0 |
| genuine | 0 | 6 | 0 | 0 |

### Confusion: B3

| label | red | amber | green | grey |
|---|---|---|---|---|
| fraud | 6 | 0 | 0 | 1 |
| genuine | 0 | 0 | 0 | 6 |

## Campaigns (S26)

- Campaign recall: 1.00 [0.21, 1.00]
- Campaign purity: 1.00 [0.21, 1.00]

## Ablations (one engine masked at a time)

| run | masked | red recall Δ | catch rate Δ | false red rate Δ | green yield Δ |
|---|---|---|---|---|---|
| A:google | google | -0.14 | +0.00 | +0.00 | +0.40 |
| A:google_lens | google_lens | +0.00 | +0.00 | +0.00 | +0.00 |
| A:google_maps | google_maps | +0.00 | +0.00 | +0.00 | -0.20 |
| A:google_jobs | google_jobs | +0.00 | +0.00 | +0.00 | +0.00 |
| A:google_news+google_forums | google_news+google_forums | +0.00 | +0.00 | +0.00 | +0.00 |

## False reds: S26

- none

## False reds: B0

- none

## False reds: B3

- none

## Latency and credits (S26)

- p50 latency: 22 ms, p95: 34 ms (replay mode)
- Mean uncached SerpApi calls per check: 0.0

## Per case

| case | label | category | expected | S26 | B0 | B3 |
|---|---|---|---|---|---|---|
| F-RPT-10 | fraud | public_report | red | red | red | red |
| F-RPT-03 | fraud | public_report | red | red | red | red |
| F-RPT-04 | fraud | public_report | red | red | amber | grey |
| F-RPT-09 | fraud | public_report | red | red | red | red |
| F-SCH-01 | fraud | scheme_impersonation | red | red | red | red |
| G-OFF-03 | genuine | official_template | green | green | amber | grey |
| G-OFF-07 | genuine | official_template | green | amber | amber | grey |
| G-OFF-08 | genuine | official_template | green | amber | amber | grey |
| F-CMP-01a | fraud | campaign_variants | red | red | red | red |
| F-CMP-01b | fraud | campaign_variants | red | red | red | red |
| G-OFF-02 | genuine | official_template | green | amber | amber | grey |
| G-JOB-02 | genuine | jobs_listing_message | green | green | amber | grey |
| G-SUP-01 | genuine | small_startup | amber | amber | amber | grey |
