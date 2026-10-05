# Special26 docs

Special26 checks an internship or job offer that an Indian student or fresher has received and tells them, with linked evidence, whether the offer really comes from the employer it claims to come from. It is built for the SerpApi India Hackathon 2026 (deadline 10 Oct 2026, 23:59 IST).

The name comes from the film *Special 26* (2013), where con men pose as CBI officers and get people to trust them because they look official. That is exactly how these scams work: they borrow the name of TCS, Tech Mahindra, the PM Internship Scheme or an MSME ministry form, and the student pays because the offer looks official.

## One-line pitch

Paste the offer, get a verdict card in under 30 seconds that shows each claim in the offer (company, sender domain, HR person, office address, role, payment ask) next to what Google, Google Maps, Google Jobs, Google Lens, Google News and Google Forums actually say about it.

## Reading order

| # | File | What it settles |
|---|------|-----------------|
| 01 | `01-investigation.md` | The problem, evidence it is real and large, why SerpApi is essential |
| 02 | `02-PRD.md` | Users, jobs to be done, features, success metrics |
| 03 | `03-SRS.md` | Numbered functional and non-functional requirements (FR-x, NFR-x) |
| 04 | `04-architecture.md` | Components, data flow, deployment, modes (live and replay) |
| 05 | `05-LLD.md` | Module layout, classes, function signatures, code for the hard parts |
| 06 | `06-data-model.md` | SQLite DDL, indexes, retention, seed files |
| 07 | `07-api-contract.md` | HTTP endpoints, JSON shapes, SSE events, error codes |
| 08 | `08-algorithm.md` | Claim extraction, the 12 probes, lookalike detection, scoring, verdict rules, template fingerprinting, campaign clustering |
| 09 | `09-user-flow.md` | Screens, states, exact copy |
| 10 | `10-novelty.md` | Competitors and what Special26 does that they do not |
| 11 | `11-evaluation.md` | Dataset, metrics, baselines, ablations, targets |
| 12 | `12-mvp-scope.md` | In, out, stretch, cut order |
| 13 | `13-dev-plan.md` | Dated task breakdown, 5 Oct to 10 Oct 2026 |
| 14 | `14-demo-plan.md` | The 3 minute video script and golden cases |

## Source of truth rules

1. `08-algorithm.md` is authoritative for probe IDs, weights, thresholds and verdict rules. Every other doc refers to it.
2. `06-data-model.md` is authoritative for table and column names.
3. `07-api-contract.md` is authoritative for endpoint paths and JSON field names.
4. If two docs disagree, the more specific doc wins in this order: 08, 06, 07, 05, 03, everything else. Record the conflict in `docs/DECISIONS.md` with the date and the resolution.

## Canonical names (use these exactly)

| Thing | Name |
|-------|------|
| Python package | `special26` |
| Base exception | `Special26Error` |
| Env var prefix | `SPECIAL26_` (plus `SERPAPI_API_KEY`) |
| Main DB | `data/special26.db` |
| Replay DB | `data/demo.db` |
| Run modes | `live`, `replay` |
| Verdict tiers | `red`, `amber`, `green`, `grey` |
| Probe IDs | `P01_ENTITY`, `P02_SENDER`, `P03_HEADERS`, `P04_FRAUD_NOTICE`, `P05_CHATTER`, `P06_IDENTIFIER_TRACE`, `P07_ROLE`, `P08_OFFICE`, `P09_IMAGE`, `P10_TEMPLATE`, `P11_POLICY`, `P12_DOMAIN_AGE` |
| Decisive rules | `D1_FEE_VS_NOTICE`, `D2_SCHEME_IMPERSONATION`, `D3_LOOKALIKE_PLUS_FEE`, `D4_IDENTIFIER_REPORTED` |
| Evidence families | `identity`, `process`, `reputation`, `artifact`, `existence` |

## Glossary

- **Offer**: whatever the student received, as text, PDF, screenshot, `.eml` file, plus an optional HR profile photo.
- **Claim**: one checkable assertion pulled from the offer, for example "sender domain is `techmahindra-careers.in`" or "asks ₹2,000 for police verification".
- **Probe**: one check that turns claims plus SerpApi results into findings.
- **Finding**: one piece of evidence with a direction, a log-likelihood weight and a receipt (the URL and snippet that justify it).
- **Receipt**: the exact SerpApi result (engine, query, position, link, snippet) behind a finding. Every finding shown to the user has one, or is marked `local_rule`.
- **Campaign**: a cluster of checks that share a hard identifier (UPI ID, phone, non-official domain, image hash) or a near-identical template.
- **Official domain set**: the registrable domains that the claimed employer actually uses, resolved by `P01_ENTITY`.

## Style rules for all copy and docs

- No em dashes.
- Never print "This is a scam" or "Safe". Use the verdict copy in `09-user-flow.md`.
- Every number in the UI links to the receipt it came from.
