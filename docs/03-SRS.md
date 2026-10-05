# 03. Software Requirements Specification: Special26

Requirement IDs are stable. Code comments and tests reference them as `# FR-07`. Priority: **M** = MVP must, **S** = should, **C** = could (stretch).

## 1. Scope

Special26 is a web application (FastAPI backend, React frontend, SQLite) that accepts an offer, extracts claims, runs probes against SerpApi and local rules, aggregates findings into a verdict, and presents it with receipts.

## 2. Functional requirements

### 2.1 Intake

| ID | Pri | Requirement | Acceptance test |
|----|-----|-------------|-----------------|
| FR-01 | M | Accept offer text up to 20,000 characters | 20,001 chars returns `422 VALIDATION_ERROR` with `details.field = "text"` |
| FR-02 | M | Accept up to 4 files, each ≤ 5 MB, types: `application/pdf`, `image/png`, `image/jpeg`, `message/rfc822` (`.eml`) | A `.docx` returns `415 UNSUPPORTED_MEDIA` |
| FR-03 | M | Each file is tagged with a role: `offer_pdf`, `offer_image`, `eml`, `hr_photo` | Missing role defaults by MIME: pdf→`offer_pdf`, image→`offer_image`, rfc822→`eml` |
| FR-04 | M | Extract text from PDFs (first 10 pages) with `pypdf`; extract embedded images ≥ 120x120 px as `offer_image` artifacts | Fixture `tm_offer.pdf` yields text containing "Tech Mahindra" and 1 image |
| FR-05 | S | OCR `offer_image` with Tesseract (`eng+hin`) if installed | When Tesseract is absent, the check continues and `claims_ready` carries warning `OCR_UNAVAILABLE` |
| FR-06 | M | Parse `.eml`: From, Reply-To, Return-Path, Subject, Date, `Authentication-Results`, body (text/plain preferred, else stripped HTML) | Fixture `genuine_dkim.eml` yields `dkim=pass header.d=<domain>` |

### 2.2 Claim extraction

| ID | Pri | Requirement | Acceptance test |
|----|-----|-------------|-----------------|
| FR-10 | M | Extract claims of the types listed in `08-algorithm.md` §2 using regex and dictionaries, no network calls | Unit tests per claim type, ≥ 3 positive and 2 negative examples each |
| FR-11 | M | Resolve the claimed organisation using, in order: known entity dictionary match, legal-suffix line, "at/with/join X" pattern, email display name | `"Welcome to Infosys Limited"` → `org = "Infosys"`, `source = "dictionary"` |
| FR-12 | S | If `SPECIAL26_LLM_PROVIDER != none` and no org was found, call the LLM with the JSON schema in `05-LLD.md` §6; reject output that fails schema validation | Invalid LLM JSON is dropped and warning `LLM_EXTRACTION_INVALID` added |
| FR-13 | M | Classify each amount: purpose ∈ {`registration`, `training`, `verification`, `deposit`, `equipment`, `document`, `other_fee`, `stipend`, `salary`}, payer ∈ {`candidate`, `employer`} | "pay ₹2,000 for police clearance" → `verification`, `candidate` |
| FR-14 | M | Return claims to the client in status `awaiting_confirmation` unless `auto_run=true` | |
| FR-15 | M | Let the client edit, add or delete claims before the run; edited claims get `source = "user"` | |
| FR-16 | M | Redact the recipient's own name, email and phone from stored text (see §4.2) | Stored text for fixture contains `<RECIPIENT>` not "Priya" |

### 2.3 Probes and SerpApi

| ID | Pri | Requirement | Acceptance test |
|----|-----|-------------|-----------------|
| FR-20 | M | Implement probes `P01` to `P11` exactly as specified in `08-algorithm.md` §4 | One test per finding rule |
| FR-21 | S | Implement `P12_DOMAIN_AGE` via RDAP (`https://rdap.org/domain/{d}`), timeout 4 s, optional | RDAP failure gives probe status `error`, verdict still produced |
| FR-22 | M | All SerpApi calls go through `SerpClient` which is cache-first, keyed by SHA-256 of sorted params without `api_key` | Second identical call hits cache, no ledger debit |
| FR-23 | M | Enforce per-check budget `SPECIAL26_CREDIT_BUDGET_PER_CHECK` (default 14) and daily cap `SPECIAL26_DAILY_CREDIT_CAP` (default 200) | 15th uncached call in one check is refused, probe status `skipped_budget` |
| FR-24 | M | Probes run in two waves: wave 1 = `P01`, `P03`, `P05`, `P06`, `P09`, `P10`, `P11`, `P12`; wave 2 = `P02`, `P04`, `P07`, `P08` (they use P01's official domains; only `P04` is skipped without one). Max 4 SerpApi calls in flight | Event log shows `P01` finish before `P02` starts |
| FR-25 | M | Each probe has a timeout of 12 s; a timeout yields status `timeout`, never fails the check | |
| FR-26 | M | In `replay` mode, SerpApi calls read only from `demo.db`; a miss yields status `skipped_replay_miss` | Replay of golden cases makes zero network calls (asserted by a socket guard in tests) |
| FR-27 | M | Every finding stores a receipt: `engine`, `query`, `result_position`, `link`, `title`, `snippet`, `serp_cache_key`; or `rule_id` for local rules | |

### 2.4 Scoring and verdict

| ID | Pri | Requirement | Acceptance test |
|----|-----|-------------|-----------------|
| FR-30 | M | Compute score S as the sum of finding weights after per-family caps (`08-algorithm.md` §5) | Unit test with fixed findings gives exact S |
| FR-31 | M | Apply decisive rules `D1` to `D4` before thresholds | |
| FR-32 | M | Apply tier rules exactly as `08-algorithm.md` §6, including the green gate | A case with S = -4 but no positive identity finding is `amber`, not `green` |
| FR-33 | M | Output top 3 reasons ordered by absolute contribution, decisive rules first | |
| FR-34 | M | Output coverage ∈ [0, 1] | |
| FR-35 | M | Verdict computation is a pure function of (confirmed claims, probe results, ruleset version) | Property test: same inputs, same output, 100 runs |
| FR-36 | M | Store `ruleset_version` (e.g. `2026.10.1`) with each verdict | |

### 2.5 Output, sharing, campaigns

| ID | Pri | Requirement | Acceptance test |
|----|-----|-------------|-----------------|
| FR-40 | M | Stream progress over SSE with the event types in `07-api-contract.md` §5 | |
| FR-41 | M | Show next steps: official contact (from `P01` or `P04` receipts), `https://cybercrime.gov.in`, helpline `1930`, Sanchar Saathi Chakshu for suspicious calls and messages | |
| FR-42 | M | Create a share token (22-char URL-safe random) per check on request; share page shows redacted claims and masked identifiers | Share JSON has phone `+91 ******3210` |
| FR-43 | M | After each verdict, compute template signature and link the check into campaigns (`08-algorithm.md` §8) | Two golden cases sharing a UPI ID end up in one campaign |
| FR-44 | S | Campaign page: number of checks, impersonated organisations, first and last seen, masked identifiers, tier distribution | |
| FR-45 | C | TPO bulk upload of up to 20 offers as a ZIP | |

## 3. Non-functional requirements

| ID | Category | Requirement |
|----|----------|-------------|
| NFR-01 | Latency | p50 ≤ 25 s, p95 ≤ 45 s in live mode for a full check; p50 ≤ 2 s in replay |
| NFR-02 | Latency | Claim extraction returns in ≤ 1.5 s for 20,000 chars of text (no OCR) |
| NFR-03 | Cost | Mean ≤ 12 uncached SerpApi calls per check; hard cap 14 |
| NFR-04 | Determinism | Verdict pure function (FR-35); MinHash uses fixed seeds; no wall-clock in scoring except domain age, which uses the RDAP registration date relative to `check.created_at` |
| NFR-05 | Availability | Any single engine failing degrades coverage, never fails the check |
| NFR-06 | Privacy | Raw offer text and raw files deleted when the check reaches a terminal state; redacted text kept 30 days; share pages expire after 30 days |
| NFR-07 | Security | Rate limit 10 checks per IP per hour in live mode; uploads stored outside the static root; signed image URLs expire in 10 minutes; `SERPAPI_API_KEY` never logged or returned |
| NFR-08 | Portability | One Docker image, `docker run -p 8000:8000 -e SERPAPI_API_KEY=... special26` |
| NFR-09 | Observability | Structured JSON logs with `check_id`, `probe_id`, `cache_hit`, `credits`; `/api/health` shows mode, DB OK, credits used today |
| NFR-10 | Accessibility | Verdict tier is conveyed with text and icon, not colour alone; WCAG AA contrast |
| NFR-11 | Mobile | Works at 360 px width; most students will open the share link on a phone |
| NFR-12 | Testability | ≥ 80% line coverage on `special26/core`; golden case tests run in replay in CI in under 60 s |

## 4. Data handling requirements

### 4.1 What is stored

Per check: redacted text, claims, probe results, findings with receipts, verdict, identifiers (normalised), template signature. See `06-data-model.md`.

### 4.2 Redaction rules

1. The recipient name: the token sequence after "Dear", "Hi", "Hello", "Congratulations" up to the first punctuation, replaced with `<RECIPIENT>`.
2. Any email or phone the student marks as "this is mine" in the claim editor, replaced with `<RECIPIENT_EMAIL>` / `<RECIPIENT_PHONE>`.
3. Aadhaar-like numbers (`\b\d{4}\s?\d{4}\s?\d{4}\b`) and PAN-like strings (`\b[A-Z]{5}\d{4}[A-Z]\b`) always replaced with `<ID>`.

### 4.3 Masking on public pages

- Phone: keep country code and last 4 digits.
- UPI ID: keep first 2 characters and the handle (`ra******@ybl`).
- Email: keep first character of the local part and the full domain (domains are evidence).
- Domains and URLs: shown in full, they are the impersonation evidence.

## 5. External interfaces

| Interface | Use | Failure handling |
|-----------|-----|------------------|
| SerpApi `https://serpapi.com/search.json` | engines `google`, `google_news`, `google_forums`, `google_jobs`, `google_maps`, `google_lens` | Retry once on 5xx with 1 s backoff; 429 marks the probe `skipped_budget` |
| RDAP `https://rdap.org/domain/{domain}` | Domain registration date (`P12`) | Optional, 4 s timeout |
| LLM API | Optional claim extraction fallback | Off by default |

## 6. Traceability

| PRD feature | Requirements |
|-------------|--------------|
| F1 Intake | FR-01 to FR-06 |
| F2 Claims | FR-10 to FR-16 |
| F3 Probes | FR-20 to FR-27 |
| F4 Verdict | FR-30 to FR-36 |
| F5 Receipts | FR-27, FR-33 |
| F6 Next steps | FR-41 |
| F7 Share | FR-42, NFR-06 |
| F8 Campaigns | FR-43, FR-44 |
| F9 Replay | FR-26, NFR-12 |
