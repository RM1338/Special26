# Cross-check of the specification

Date: 2026-10-05. Inputs: all files `00` to `14`. Every conflict or gap below has a numbered entry in `DECISIONS.md` (`D-xx`, not to be confused with decisive rules `D1` to `D4`).

Legend: ✓ present, ✗ missing, ~ partial.

## 1. Probe codes (`08` §4)

Columns: weight and family from `08`; **Copy** = an exact message string exists somewhere in the docs; **Test plan** = named acceptance test in `03`/`13`/`14` (FR-20 requires one test per finding rule for all of them); **LLD** = module named in `05` §1.

| Code | Weight | Family | Copy in docs | Test plan named | LLD module |
|------|--------|--------|--------------|-----------------|------------|
| P01_OFFICIAL_FOUND | 0.0 | identity | ✗ | ✓ T1.7 (Tech Mahindra → techmahindra.com) | p01_entity.py |
| P01_NO_PRESENCE | +1.0 | identity | ✗ | ✓ T1.7, G4 | p01_entity.py |
| P02_SENDER_OFFICIAL | -1.0 | identity (from §5.1) | ✗ | ~ T1.8 generic | p02_sender.py |
| P02_HOMOGLYPH | +3.5 | identity | ✗ | ~ T1.8 | p02_sender.py |
| P02_TYPOSQUAT | +3.0 | identity | ✗ | ~ T1.8 | p02_sender.py |
| P02_COMBOSQUAT | +3.0 | identity | ✓ `07` §4, `08` §6.1 | ✓ G1, G6 | p02_sender.py |
| P02_TLD_SWAP | +2.5 | identity | ✗ | ~ T1.8 | p02_sender.py |
| P02_FREEMAIL | +1.5 | identity | ✗ | ✓ G5 | p02_sender.py |
| P02_FREEMAIL_NO_PRESENCE | +0.8 | identity | ✗ | ✓ G4 | p02_sender.py |
| P02_UNRELATED | +1.0 | identity | ✗ | ~ T1.8 | p02_sender.py |
| P02_REPLY_DIVERTED | +2.0 | identity | ✗ | ~ T1.8 | p02_sender.py |
| P03_DKIM_ALIGNED_OFFICIAL | -3.0 | identity | ✗ | ✓ T3.4, G3 | p03_headers.py |
| P03_AUTH_FAIL | +2.0 | identity | ✗ | ✗ | p03_headers.py |
| P03_REPLY_DIVERTED | +2.0 | identity | ✗ | ✗ | p03_headers.py |
| P04_NOTICE_FOUND | +0.3 | reputation | ✓ `07` §4 | ✓ T2.4 | p04_fraud_notice.py |
| P04_NOTICE_NO_FEE | 0.0 | reputation | n/a (flag) | ✓ T2.4 (D1 fires for G1) | p04_fraud_notice.py |
| P05_COMPLAINTS_GENERAL | +0.7 | reputation | ✗ | ✗ | p05_chatter.py |
| P05_COMPLAINT_NAMES_SENDER | +2.0 | reputation | ✗ | ✗ | p05_chatter.py |
| P05_PIB_FACTCHECK | +1.5 | reputation | ✗ | ✗ | p05_chatter.py |
| P06_ID_REPORTED | +3.0 each, probe cap +4.0 | reputation | ✗ | ✗ | p06_identifier_trace.py |
| P06_ID_ON_OFFICIAL | -1.5 | reputation | ✗ | ✗ | p06_identifier_trace.py |
| P06_ID_SEEN_LOCALLY | +2.0 | reputation | ~ `09` §S5 (receipt copy only) | ✓ T3.6, G6b | p06_identifier_trace.py |
| P07_ROLE_LISTED | -1.0 | existence | ✗ | ✓ T3.1, G3 | p07_role.py |
| P07_COMPANY_LISTS_OTHER_ROLES | +0.2 | existence | ✗ | ✗ | p07_role.py |
| P08_OFFICE_MATCH | -1.0 | existence | ✗ | ✓ T3.2, G3 | p08_office.py |
| P08_RESIDENTIAL | +1.0 | existence | ✗ | ✓ T3.2 | p08_office.py |
| P08_COWORKING | +0.5 | existence | ✗ | ✗ | p08_office.py |
| P08_NOT_FOUND | +0.5 | existence | ✗ | ✗ | p08_office.py |
| P08_REVIEWS_SCAM | +1.5 | reputation | ✗ | ✗ | p08_office.py |
| P09_STOCK_PHOTO | +3.0 | artifact | ✗ | ✓ T3.3, G5 | p09_image.py |
| P09_PHOTO_OTHER_NAMES | +2.5 | artifact | ✗ | ✗ | p09_image.py |
| P09_PHOTO_OFFICIAL | -1.0 | artifact | ✗ | ✗ | p09_image.py |
| P09_LETTER_REPORTED | +2.5 | artifact | ✗ | ✗ | p09_image.py |
| P10_TEMPLATE_MATCH_HIGH | +3.0 | artifact | ✗ | ✓ T3.5 (self-match J = 1.0) | p10_template.py |
| P10_TEMPLATE_MATCH_MED | +1.5 | artifact | ✗ | ✓ T3.5 (paraphrase J in [0.4, 0.8]) | p10_template.py |
| P10_PHRASE_REPORTED | +2.0 | artifact | ✗ | ✗ | p10_template.py |
| P10_PHRASE_OFFICIAL | -0.5 | artifact | ✗ | ✗ | p10_template.py |
| P11_CANDIDATE_PAYS | +2.5 | process | ~ `09` §S5 rule receipt copy | ✓ G1, G2, G5 | p11_policy.py |
| P11_REFUNDABLE_BAIT | +0.5 | process | ✗ | ✗ | p11_policy.py |
| P11_PERSONAL_UPI | +1.0 | process | ✓ `08` §6.1 (conflicts with `07`, see D-07) | ✓ G1 reason 3 | p11_policy.py |
| P11_SCHEME_OFF_PORTAL | +3.0 | process | ✗ | ✓ G2 | p11_policy.py |
| P11_FORM_OR_SHORTLINK | +0.7 | process | ✗ | ✓ G2 | p11_policy.py |
| P11_URGENCY | +0.5 | process | ✗ | ✓ G1 | p11_policy.py |
| P11_NO_INTERVIEW | +1.0 | process | ✗ | ✓ G1, G4 | p11_policy.py |
| P11_CHAT_INTERVIEW | +0.7 | process | ✗ | ✗ | p11_policy.py |
| P12_VERY_NEW | +1.5 | identity | ✗ | ✗ | p12_domain_age.py |
| P12_NEW | +0.7 | identity | ✗ | ✗ | p12_domain_age.py |

Decisive rules: D1 copy ✓ (`08` §6.1), D3 copy ✓ (same as the lookalike finding message), D2 copy ✗, D4 copy ✗.

**Flags**
- **Copy is missing for 43 of 46 finding codes and for D2 and D4.** Only P02_COMBOSQUAT, P04_NOTICE_FOUND and P11_PERSONAL_UPI have a message string; P06_ID_SEEN_LOCALLY and P11_CANDIDATE_PAYS have receipt copy only. `09` defines headlines and screen copy, not per-finding reasons. I wrote the strings myself, following the `09` §4 copy rules (name the source, no "scam"/"safe", ₹ format, masked identifiers). See D-01. They live in `scoring/copy.py`, and startup refuses to run if any code has no string.
- `P04_NOTICE_NO_FEE` is a decisive flag on the `P04_NOTICE_FOUND` finding, not a finding of its own. `07` §4 and the `05` §7 scorer agree on this (D-02).
- Weights and families are complete for every code. Family for P02/P03/P04/P05/P06/P09/P10/P11/P12 comes from `08` §5.1 where the probe table does not state it.
- Test plans are missing for 21 codes. All of them get a unit test anyway (FR-20).
- **Wave assignment conflict.** `P06`, `P10` and `P12` sit in wave 1 (`04` §4, `05` registry, FR-24), but under `08` they need P01's official domain set: P06 picks identifiers by domain class and computes `ID_ON_OFFICIAL`, P10 computes `PHRASE_OFFICIAL`, and P12 needs the domain class. `08` wins, so these three depend on P01 (D-03).
- The `P11_CANDIDATE_PAYS` receipt is supposed to cite P04's notice, but P11 runs before P04. The citation moves into the D1 reason, which already links both findings (D-04).
- **Reason tiebreak conflict.** In the worked example, `P11_PERSONAL_UPI` and `P11_NO_INTERVIEW` both weigh +1.0. The `05` tiebreak (alphabetical code) picks NO_INTERVIEW, but `08` §6.1 shows PERSONAL_UPI. `08` wins, so the tiebreak follows `08` table order (D-05).

## 2. Tables and columns

### Used in `05`/`07`, missing or inconsistent in `06`

| Item | Where used | Issue | Resolution |
|------|-----------|-------|------------|
| `credit_ledger.created_at` | `05` §4 `budget_reserve` INSERT | The INSERT omits a NOT NULL column | Include it (D-06) |
| `credit_ledger` reserve then `ledger_add` | `05` §4 | One live call writes two uncached rows, so the budget is counted twice | Reserve one row, then update it to `spent` or `refunded`. Budget counts rows with status ≠ `refunded` (D-06) |
| `verdicts.headline`, `strength`, `next_steps` | `07` §4 | Not stored | Derived at read time from tier, red_kind, score and claims (D-08) |
| `official_contacts[].finding_id` | `07` §4 | `06` §3 P01 outputs use `receipt_finding_id` | API and `verdicts.official_contacts_json` use `finding_id`. P01 `outputs_json` stores `kind`, `value` and the source receipt (D-08) |
| `org_unknown` | `07` §3 PUT | No column | Stored as warning `ORG_UNKNOWN` in `checks.warnings_json` (D-09) |
| `mine` phones/emails | `07` §3 PUT | No column | Phones get claim `role = recipient`. Emails are deleted as claims. Both are redacted in `redacted_text` (D-09) |
| Identifier rows | `05` §10 `checks_with_identifier`, P06 local memory | The `05` §8 runner never writes `identifiers` | Runner writes identifiers for every check after scoring, before campaign linking (D-10) |
| RDAP responses in replay | `04` §7 (replay = no network) | Only `serp_cache` is recorded, so P12 can't replay | RDAP JSON goes into `serp_cache` with `engine = 'rdap'`, and no ledger row (D-11) |
| Lens cache key | `05` §4 | The signed URL holds an expiry, so the key changes on every run and replay always misses | The canonical key replaces `url`/`image_id` with `image_sha256` (D-12) |
| `templates`/`lsh_bands` for purged checks | `06` §5 | `templates.check_id` has no FK to `checks`, so purge leaves orphans | Retention deletes templates of purged checks (D-13) |
| Share token expired | `07` §9 410 | Retention deletes expired tokens, so callers get 404 | Handler returns 410 while the row exists, and 404 after purge (D-13) |

### In `06`, not used by `05`/`07`

| Column | Status |
|--------|--------|
| `checks.text_sha256` | Computed. Never read (dedupe isn't specified). Kept |
| `known_entities.careers_url`, `fraud_notice_url` | Seed data only. Official contacts must come from P01/P04 receipts (`09` S6), so these aren't shown in next steps |
| `artifacts.derived_from`, `width`, `height` | Used by PDF image extraction (FR-04) |
| `eval_runs`, `eval_results` | Used by `eval/run_eval.py` (`11` §7) |
| `campaigns.merged_into` | Used by the 301 redirect in `07` §7 |

## 3. API (`07`) against screen needs (`09`)

| Screen need | Endpoint/field | Status |
|-------------|----------------|--------|
| S1 submit, 413/415/400 copy | `POST /api/checks`, §9 codes | ✓ |
| S1 example chips (G1, G2, G3) | none | Frontend bundles the golden texts. G3 has no text until the consented `.eml` exists (D-14) |
| S2 "Please check" badge | `claims[].source` | ✓ |
| S2 HR title | `hr_person.value.title` | ✓ |
| S2 "who pays" editable | PUT claims | ~ `07` says the server recomputes payer, which would overwrite the student's edit. Server recomputes a derived field only when the client didn't send it (D-15) |
| S2 OCR banner | `warnings` contains `OCR_UNAVAILABLE` | ✓ |
| S2 "The offer doesn't say" | `org_unknown` | ✓ |
| S3 rows and engine badges | SSE `probe.started.engine` | ~ P05 uses 3 engines. The UI maps probe → badges statically from `04` §4, and `engine` carries the primary engine |
| S3 rows for skipped probes | SSE | ~ Skipped probes emit only `probe.finished`. The UI creates a row on either event |
| S3 end text "1 concern" / "Looks consistent" / "Nothing found" | `probe.finished.findings` is a count only | ✗ The direction is missing. The UI refetches `GET /api/checks/{id}` on each `probe.finished` and reads finding weights, so the contract stays unchanged (D-16) |
| S3 `check.running` payload | `07` §5 `{probes_planned, budget}` | `05` §8 publishes `{}`. Follow `07` |
| S3 replay banner date | `GET /api/health.replay_recorded_at`, `check.mode` | ✓ |
| S4 headline, sub line with `{org}`, `{official_contact}` | `verdict.headline`, `claims`, `official_contacts` | ✓ |
| S4 engine badge per reason | `reasons[].finding_ids` → `findings[].receipt.engine` | ✓ |
| S4 "We could run 10 of 11 checks" | `probes[].status` | ✓ Shows counts of covered/applicable probes. The weighted `coverage` number drives the tier |
| S5 receipt fields | `receipt.*` | ✓ |
| S5 "Why it matters" | none | Uses `finding.message` |
| S5 rule receipt copy | `receipt.rule_id` | Rule copy table in `scoring/copy.py` (D-01) |
| S5 local memory "appeared in 3 earlier checks" + campaign link | `receipt.extra` | `extra = {count, campaign_id}` |
| S6 next steps | `verdict.next_steps` | ~ The `07` red example omits 1930 and the placement cell step, which `09` S6 requires. Keys: `do_not_pay`, `verify_official`, `call_1930`, `report_cybercrime`, `report_chakshu`, `tell_placement_cell` (D-17) |
| S7 share page, masked | `GET /api/share/{token}` | ✓ |
| S7 WhatsApp preview (OG tags) | none | ✗ WhatsApp's crawler doesn't run JS. The server renders `/s/{token}` as `index.html` with OG tags injected (D-18) |
| S8 title "{n} offers linked to the same {edge}" | `member_count`, `edge_counts` | ✓ Uses the edge type with the highest count |
| S8 "template similarity" | `edge_counts.template` | ~ Shown as a count of template edges (D-19) |
| Error: daily cap before start | 429 `BUDGET_EXHAUSTED` on `POST run` (and on create with `auto_run`) | ✓ |
| Error: rate limited, minutes | 429 + `Retry-After` | ✓ |
| Error: expired check | 410 `EXPIRED` | ✓ |

## 4. Requirements → module → test

| ID | Module | Test |
|----|--------|------|
| FR-01 | `api/checks.py` | `tests/api/test_create.py::test_text_too_long_422` |
| FR-02 | `api/checks.py` | `test_create.py::test_docx_415`, `test_file_too_big_413`, `test_five_files_413` |
| FR-03 | `api/checks.py` | `test_create.py::test_role_defaults_by_mime` |
| FR-04 | `intake/pdf.py` | `tests/unit/test_pdf.py` (fixture `tm_offer.pdf`) |
| FR-05 | `intake/ocr.py` | `tests/unit/test_ocr.py::test_ocr_unavailable_warning` |
| FR-06 | `intake/eml.py` | `tests/unit/test_eml.py` (fixture `genuine_dkim.eml`) |
| FR-10 | `claims/regexes.py`, `claims/extract.py` | `tests/unit/test_regexes.py` (≥ 3 positive, 2 negative per type) |
| FR-11 | `claims/org.py` | `tests/unit/test_org.py` |
| FR-12 | `claims/llm.py` | `tests/unit/test_llm.py` (mocked, invalid → warning) |
| FR-13 | `claims/amounts.py` | `tests/unit/test_amounts.py` |
| FR-14 | `api/checks.py` | `test_create.py::test_awaiting_confirmation` |
| FR-15 | `api/checks.py` | `tests/api/test_claims.py` |
| FR-16 | `claims/redact.py` | `tests/unit/test_redact.py` |
| FR-20 | `probes/p01..p11` | `tests/unit/test_pXX_*.py`, one test per finding code |
| FR-21 | `probes/p12_domain_age.py`, `domains/rdap.py` | `tests/unit/test_p12.py` |
| FR-22 | `serp/client.py` | `tests/unit/test_serp_client.py::test_second_call_hits_cache` |
| FR-23 | `serp/client.py`, `storage/repo.py` | `test_serp_client.py::test_budget_15th_call`, `test_daily_cap` |
| FR-24 | `probes/registry.py`, `pipeline/runner.py` | `tests/unit/test_runner.py::test_p01_before_dependents` |
| FR-25 | `pipeline/runner.py` | `test_runner.py::test_timeout_status` |
| FR-26 | `serp/client.py` | `test_serp_client.py::test_replay_miss`, golden tests with socket guard |
| FR-27 | `probes/base.py` | `tests/unit/test_receipts.py` (every finding has a receipt) |
| FR-30 to FR-34 | `scoring/aggregate.py` | `tests/unit/test_scoring.py` (worked example, caps, D1 to D4, tiers, green gate, grey, reasons, coverage) |
| FR-35 | `scoring/aggregate.py` | `test_scoring.py::test_determinism_100_runs` |
| FR-36 | `scoring/aggregate.py`, `storage/repo.py` | `test_scoring.py::test_ruleset_version` |
| FR-40 | `api/checks.py`, `pipeline/events.py` | `tests/api/test_sse.py` (incl. `Last-Event-ID`) |
| FR-41 | `scoring/nextsteps.py` | `tests/unit/test_nextsteps.py` |
| FR-42 | `api/share.py`, `scoring/mask.py` | `tests/api/test_share.py`, `tests/unit/test_mask.py` |
| FR-43 | `template/*`, `campaign/*` | `tests/unit/test_minhash.py`, `test_unionfind.py`, golden G6 |
| FR-44 | `api/campaigns.py` | `tests/api/test_campaigns.py` |
| FR-45 | out of scope (stretch 6) | none |
| NFR-01 | whole pipeline | `eval/run_eval.py` latency histogram; replay timing in golden tests |
| NFR-02 | `claims/extract.py` | `test_extract.py::test_20k_under_1_5s` |
| NFR-03 | `serp/client.py` | ledger stats in eval report |
| NFR-04 | `scoring`, `template/minhash.py` | determinism test, fixed-seed MinHash test |
| NFR-05 | `pipeline/runner.py` | `test_runner.py::test_engine_failure_degrades` |
| NFR-06 | `storage/retention.py`, runner `purge_raw` | `tests/unit/test_retention.py` |
| NFR-07 | `api/ratelimit.py`, `api/public_img.py`, logging | `tests/api/test_ratelimit.py`, `test_public_img.py`, `test_no_key_in_logs` |
| NFR-08 | `Dockerfile` | manual `docker run` (M5) |
| NFR-09 | `logging_setup.py`, `api/health.py` | `tests/api/test_health.py` |
| NFR-10, NFR-11 | `frontend/` | manual mobile pass at 360 px (T4.3) |
| NFR-12 | CI | `pytest --cov` on `claims`, `domains`, `probes`, `scoring`, `template`, `campaign` ≥ 80%, total < 60 s |

## 5. Worked example (`08` §6.1) recomputed by hand

Findings and raw weights:

| Finding | Family | Raw | Effective |
|---------|--------|-----|-----------|
| P01_OFFICIAL_FOUND | identity | 0.0 | 0.0 |
| P02_COMBOSQUAT | identity | +3.0 | +3.0 (only lookalike, full weight) |
| P04_NOTICE_FOUND (flag P04_NOTICE_NO_FEE) | reputation | +0.3 | +0.3 |
| P05_COMPLAINTS_GENERAL | reputation | +0.7 | +0.7 |
| P11_CANDIDATE_PAYS | process | +2.5 | +2.5 |
| P11_PERSONAL_UPI | process | +1.0 | +1.0 |
| P11_URGENCY | process | +0.5 | +0.5 |
| P11_NO_INTERVIEW | process | +1.0 | +1.0 |

Family sums, then caps:
- identity: 0.0 + 3.0 = 3.0, clamp(-3.5, +4.0) → **3.0**
- process: 2.5 + 1.0 + 0.5 + 1.0 = 5.0, clamp(0.0, +4.0) → **4.0**
- reputation: 0.3 + 0.7 = 1.0, clamp(-1.5, +4.0) → **1.0**
- artifact: **0.0**, existence: **0.0**

**S = 3.0 + 4.0 + 1.0 + 0 + 0 = 8.0** ✓

Decisive rules:
- D1: P11_CANDIDATE_PAYS ✓ and flag P04_NOTICE_NO_FEE ✓ → fires
- D2: no P11_SCHEME_OFF_PORTAL → no
- D3: P02_COMBOSQUAT ✓ and P11_CANDIDATE_PAYS ✓ → fires
- D4: no P06_ID_REPORTED → no

**Decisive = {D1_FEE_VS_NOTICE, D3_LOOKALIKE_PLUS_FEE}** ✓

Tier: rule 1 (a decisive rule fired) → **red** ✓. red_kind: decisive fired (and S_identity = 3.0 ≥ 2.5) → **impersonation** ✓.

Strength = clamp((8.0 + 8.5) / 26.5, 0, 1) = 16.5 / 26.5 = 0.6226 → 0.62, which matches `07` §4 ✓.

Reasons: D1 first, then D3. The remaining findings exclude those already used by a fired decisive rule (P04_NOTICE_FOUND, P11_CANDIDATE_PAYS, P02_COMBOSQUAT). That leaves PERSONAL_UPI 1.0, NO_INTERVIEW 1.0, COMPLAINTS_GENERAL 0.7 and URGENCY 0.5. PERSONAL_UPI and NO_INTERVIEW tie on |w| and probe, so reason 3 = PERSONAL_UPI only under the `08`-table-order tiebreak (D-05) ✓.

The extraction trace for G1 (text in `14` §3) also reproduces these inputs:
- The amount window for ₹2,000 contains "police clearance", so purpose = verification. It contains "paying"/"upi", so payer = candidate.
- "within 24 hours" → urgent.
- "on the basis of your profile" → no_interview.
- `techm.hr@ybl` → handle `ybl` is a known handle.
- `techmahindra-careers.in` → minus `techmahindra` leaves `careers`, a lure token → combosquat.

## 6. Other conflicts found

| # | Conflict | Winner | Entry |
|---|----------|--------|-------|
| a | P11_PERSONAL_UPI copy: `08` "...(te****@ybl) within 24 hours." vs `07` "...(te****@ybl)." | `08`: deadline suffix added when a deadline claim exists | D-07 |
| b | UPI mask: `03` §4.3 example `ra******@ybl` vs `07`/`08` `te****@ybl` | `07`: fixed 4 stars (also avoids leaking length) | D-20 |
| c | Green/grey headlines in `02` §9 vs `09` S4 | `09` (marked exact) | D-21 |
| d | `02` §7 says green needs "two independent sources"; `08` green_anchor accepts P03 alone | `08` | D-21 |
| e | FR-27 field name `result_position` vs `05`/`07` `position` | `07` | D-22 |
| f | `04` §6 says "task T1.6" for the Lens decision; `13` calls it T0.6 | `13` | D-22 |
| g | D4 counts distinct `netloc` in `05`, "distinct source domains" in `08` | `08`: registrable domain | D-22 |
| h | Amount window crossing sentences misclassifies G2's ₹499 as `stipend` ("per month" sits 10 tokens back) | Gap fill: the 12-token window is clipped at sentence ends | D-23 |
| i | `P11_REFUNDABLE_BAIT` matches "non-refundable" (G2) | Gap fill: "non-refundable" excluded | D-23 |
| j | The UPI regex matches the `user@domain-with-hyphen` prefix of emails | Gap fill: UPI matches that overlap an email span are dropped | D-24 |
| k | Legal-line org regex gives "We at Nimbleleaf Analytics" for G4 | Gap fill: strip a leading `... at/with/from/join/welcome to/behalf of` prefix | D-24 |
| l | `04` §6 image token is an HMAC only, so it can't be verified without a lookup | Gap fill: token carries sha256, expiry and HMAC | D-25 |
| m | P05 call A uses `-site:{o1}`, which is undefined when P01 found nothing | Clause dropped when there is no official domain | D-26 |
