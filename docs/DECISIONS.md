# Decisions log

Each entry has a date, context, decision and the files it affects. IDs are `D-xx`, which are separate from the decisive rules `D1` to `D4`. Precedence when docs disagree: `08` > `06` > `07` > `05` > `03` > the rest.

---

### D-01 · 2026-10-05 · Finding and rule copy strings
**Context:** `09` defines headlines and screen copy, but has reason copy for only 3 of 46 finding codes and for D1/D3. D2 and D4 have no copy. FR-20 and the startup check require a message for every code.
**Decision:** Write one template per code in `scoring/copy.py`, following the `09` §4 rules: name the evidence source in the sentence, never "scam"/"safe"/"guaranteed"/"100%", "fraud" only when quoting a source's own notice, amounts as ₹2,000, identifiers masked, no em dashes. Strings that the docs do give are used verbatim. Rule receipts (`kind = rule`) get a `RULE_COPY[rule_id]` sentence, starting from the `09` S5 example for P11_CANDIDATE_PAYS.
**Files:** `backend/special26/scoring/copy.py`, `rules/weights.yaml`.

### D-02 · 2026-10-05 · `P04_NOTICE_NO_FEE` is a flag
**Context:** `08` lists it as a code with weight 0.0. `07` §4 and the `05` §7 scorer treat it as `decisive_flag` on `P04_NOTICE_FOUND`.
**Decision:** Emitted as `decisive_flag="P04_NOTICE_NO_FEE"` on the `P04_NOTICE_FOUND` finding. No separate finding. It is listed in `weights.yaml` under `flags:` so the startup check still knows it.
**Files:** `probes/p04_fraud_notice.py`, `rules/weights.yaml`.

### D-03 · 2026-10-05 · P06, P10, P12 depend on P01
**Context:** `04` §4, the `05` registry and FR-24 put P06, P10 and P12 in wave 1. But `08` defines their inputs and findings in terms of the official domain set that only P01 produces:
- P06 picks identifiers by domain class and emits `ID_ON_OFFICIAL`.
- P10 emits `PHRASE_OFFICIAL`.
- P12 needs the domain class.
**Decision:** `08` wins. `DEPENDS` adds `P06_IDENTIFIER_TRACE`, `P10_TEMPLATE` and `P12_DOMAIN_AGE` → `P01_ENTITY`. The runner schedules by dependencies: each probe awaits only its own upstreams. This keeps the FR-24 acceptance test (P01 finishes before P02 starts). Only P04 is skipped when there is no official domain. The others run with an empty official set.
**Files:** `probes/registry.py`, `pipeline/runner.py`.

### D-04 · 2026-10-05 · P11 receipt and P04 notice
**Context:** `08` P11 says the `P11_CANDIDATE_PAYS` receipt cites P04's notice "if available", but P11 has no dependency on P04.
**Decision:** The P11 receipt is a `rule` receipt (`rule_id = P11_CANDIDATE_PAYS`). The link to the employer's notice is carried by the D1 reason, whose `finding_ids` include both the P04 and the P11 findings (as in the `07` §4 example).
**Files:** `probes/p11_policy.py`, `scoring/aggregate.py`.

### D-05 · 2026-10-05 · Reason ordering and tiebreak
**Context:** `05` §7 breaks ties by `-|effective_weight|`, then `probe_id`, then `code` alphabetically. In the worked example, `P11_PERSONAL_UPI` and `P11_NO_INTERVIEW` tie at 1.0, and the alphabetical tiebreak picks NO_INTERVIEW. `08` §6.1 shows PERSONAL_UPI as reason 3.
**Decision:** `08` wins. The final tiebreak is the code's position in `08`'s tables, which is the order of `weights.yaml`. Findings already cited by a fired decisive rule are not repeated as separate reasons; `08` §6.1 implies this, since its reason 3 is neither P02_COMBOSQUAT nor P11_CANDIDATE_PAYS. Findings with weight 0 are never reasons.
**Files:** `scoring/aggregate.py`.

### D-06 · 2026-10-05 · Credit ledger accounting
**Context:** In `05` §4, `budget_reserve` inserts a `reserved` row without the NOT NULL `created_at`, and `ledger_add(cached=False)` then inserts a second uncached row. One call would be counted twice.
**Decision:**
- `budget_reserve` inserts one row (`status = reserved`, `created_at` set) and returns its id.
- On success, that row is updated to `spent` with its `cache_key`. On any failure, it becomes `refunded`.
- Budget counts are rows with `cached = 0 AND status != 'refunded'`.
- A cache hit inserts one `cached = 1, status = spent` row.
- Replay mode writes no ledger rows.
**Files:** `storage/repo.py`, `serp/client.py`.

### D-07 · 2026-10-05 · P11_PERSONAL_UPI copy
**Context:** `08` §6.1 reads "You are asked to pay a personal UPI ID (te****@ybl) within 24 hours." `07` §4 has the same sentence without the deadline.
**Decision:** `08` wins. Append " within {hours} hours" when a deadline claim exists.
**Files:** `scoring/copy.py`.

### D-08 · 2026-10-05 · Derived verdict fields
**Context:** `07` returns `headline`, `strength` and `next_steps`, which have no columns in `06`. `06` §3 uses `receipt_finding_id`, while `07` uses `finding_id`.
**Decision:** Derived at read time from the stored tier, red_kind, score and claims. This is deterministic and needs no schema change. `official_contacts` uses the `07` shape `{kind, value, finding_id}` in `verdicts.official_contacts_json`. P01 `outputs_json.official_contacts` stores `{kind, value}` plus the source receipt.
**Files:** `api/checks.py`, `scoring/nextsteps.py`, `storage/repo.py`.

### D-09 · 2026-10-05 · `org_unknown` and `mine`
**Context:** `07` §3 accepts both fields, but `06` has no columns for them.
**Decision:**
- `org_unknown = true` adds warning `ORG_UNKNOWN` to `checks.warnings_json`. P01 is then `skipped_no_input`.
- Phones listed in `mine` keep their claim with `role = recipient`. They are excluded from probes, identifiers and campaigns.
- Emails in `mine` lose their claim.
- Both are replaced in `redacted_text` (`<RECIPIENT_PHONE>`, `<RECIPIENT_EMAIL>`).
**Files:** `api/checks.py`, `claims/redact.py`.

### D-10 · 2026-10-05 · Writing identifiers
**Context:** P06 local memory and campaign linking read `identifiers`, but the `05` §8 runner never writes it.
**Decision:** After scoring, the runner writes the hard identifiers of every check: upi, non-recipient phone, non-official and non-freemail domains and emails, with `domain_class`. It then links campaigns. Retention already keeps them only for red checks after 30 days.
**Files:** `pipeline/runner.py`, `storage/repo.py`, `campaign/link.py`.

### D-11 · 2026-10-05 · RDAP in replay
**Context:** Replay must make no network calls. `demo.db` holds only `serp_cache`.
**Decision:** RDAP responses are cached in `serp_cache` with `engine = 'rdap'` and params `{"engine":"rdap","domain":d}`, and copied by `SPECIAL26_RECORD_TO`. They use no budget and write no ledger row. In replay a miss gives `skipped_replay_miss`. A 404 from rdap.org means "no registration data": status `ok` with no finding, which matches the `08` §6.1 note on unregistered demo domains.
**Files:** `domains/rdap.py`, `serp/client.py`.

### D-12 · 2026-10-05 · Lens cache key
**Context:** The signed image URL contains an expiry. Using it in the cache key would make every Lens call a cache and replay miss.
**Decision:** For `engine = google_lens`, the canonical params used for the cache key replace `url` / `image_id` with `image_sha256`. The real request still sends the URL or `image_id`.
**Files:** `serp/client.py`, `probes/p09_image.py`.

### D-13 · 2026-10-05 · Retention gaps
**Context:** `templates` has no FK to `checks`, so purged checks leave orphan signatures. Expired share tokens are deleted, so `410 EXPIRED` can never be returned.
**Decision:** Retention also deletes `templates` (and their `lsh_bands` via cascade) whose `check_id` no longer exists and is not `seed:*`. The share handler returns 410 while an expired row still exists, and 404 after purge.
**Files:** `storage/retention.py`, `api/share.py`.

### D-14 · 2026-10-05 · G3 needs real data
**Context:** G3 must be a consented real offer `.eml` with `dkim=pass`. It can't be constructed.
**Decision:** Blocked on the team providing it. Until then the G3 golden test is marked `xfail(reason="needs consented eml")`, and the home page chip loads G4 instead. See `STATUS.md`.
**Files:** `tests/golden/`, `frontend/src/pages/Home.tsx`.

### D-15 · 2026-10-05 · Server recompute on PUT claims
**Context:** `07` §3 says the server recomputes derived fields (registrable domain, purpose, payer), which would overwrite a payer the student edited in S2.
**Decision:** `registrable_domain` and `host` are always recomputed. `purpose` and `payer` are recomputed only when the client omits them.
**Files:** `api/checks.py`, `claims/extract.py`.

### D-16 · 2026-10-05 · Timeline row result text
**Context:** `09` S3 needs "1 concern" / "Looks consistent" / "Nothing found", but `probe.finished` carries only a finding count.
**Decision:** The SSE contract is unchanged. On each `probe.finished` the UI refetches `GET /api/checks/{id}` (findings are saved before the event fires) and computes the text from the probe's finding weights: any positive → "{n} concern(s)", only negative → "Looks consistent", none → "Nothing found".
**Files:** `frontend/src/components/ProbeTimeline.tsx`.

### D-17 · 2026-10-05 · Next step keys
**Context:** The red example in `07` §4 lists 4 keys. `09` S6 requires 1930 and the placement cell step for red too.
**Decision:** Keys in `09` S6 order:
- `do_not_pay` (red, amber, grey)
- `verify_official` (any tier, if a contact exists)
- `call_1930` (red, amber)
- `report_cybercrime` (red)
- `report_chakshu` (red, and a phone claim exists)
- `tell_placement_cell` (red, amber)
**Files:** `scoring/nextsteps.py`, `frontend/src/components/NextSteps.tsx`.

### D-18 · 2026-10-05 · OG tags for share pages
**Context:** `09` S7 requires a WhatsApp preview, but WhatsApp's crawler does not run JavaScript.
**Decision:** FastAPI serves `/s/{token}` itself: it returns the built `index.html` with `og:title` (headline) and `og:description` (reason 1) injected server-side, both HTML-escaped. All other SPA routes get the plain `index.html`.
**Files:** `api/share.py`, `main.py`.

### D-19 · 2026-10-05 · Campaign template similarity
**Context:** `09` S8 lists "template similarity", but `07` §7 has no such field.
**Decision:** Shown from `edge_counts.template` ("{n} offers share near-identical wording"). No contract change.
**Files:** `frontend/src/pages/Campaign.tsx`.

### D-20 · 2026-10-05 · Mask formats
**Context:** The `03` §4.3 example `ra******@ybl` uses one star per character. The `07`/`08` examples use `te****@ybl` for `techm.hr`.
**Decision:** `07` wins, with fixed widths so length is not leaked:
- UPI: first 2 characters + `****` + `@handle`
- Email: first character + `***` + `@domain`
- Phone: `+91 ******` + last 4 digits
Finding messages always use masked UPI, phone and email, so stored messages are safe on the share page.
**Files:** `scoring/mask.py`.

### D-21 · 2026-10-05 · Headlines and the green gate
**Context:** The green and grey headlines in `02` §9 differ from `09` S4. `02` §7 says green needs two independent sources, while `08` accepts `P03_DKIM_ALIGNED_OFFICIAL` alone as an anchor.
**Decision:** `09` copy is used verbatim, since it is marked exact. The `08` green rule applies.
**Files:** `scoring/copy.py`, `scoring/aggregate.py`.

### D-22 · 2026-10-05 · Minor naming conflicts
- FR-27 `result_position` → field is `position` (`05`, `07`).
- `04` §6 cites "T1.6" for the Lens decision; the task is T0.6 in `13`.
- D4 counts distinct *registrable* source domains (`08`), not `netloc` (`05`).
- `05` names `SerpClient.search(check_id, params)`; `04` draws `search(engine, params, check_id)`. Follow `05`.
**Files:** `probes/base.py`, `scoring/aggregate.py`.

### D-23 · 2026-10-05 · Amount window and refundable bait
**Context:** In G2, "Rs 5,000 per month for 12 months. Register now: ... Registration fee Rs 499" puts "per month" inside the 12-token window of ₹499. Under "first purpose wins in order" (stipend first), ₹499 would become a stipend paid by the employer. Separately, "non-refundable" contains "refundable", which would fire `P11_REFUNDABLE_BAIT` on the opposite meaning.
**Decision:**
- The 12-token window is clipped at sentence boundaries (`.`, `!` or `?` followed by whitespace, or a blank line). Single line wraps do not end a sentence, so G1's wrapped sentence still works.
- "refundable" is matched only when not preceded by "non-" / "non ".
- Neither change touches weights or thresholds.
**Files:** `claims/amounts.py`, `probes/p11_policy.py`.

### D-24 · 2026-10-05 · Extraction edge cases
**Context:** The `08` §2.2 UPI regex matches `hr.onboarding@techmahindra` inside the email `hr.onboarding@techmahindra-careers.in`. The `08` §2.3 legal-line regex captures "We at Nimbleleaf Analytics" in G4.
**Decision:**
- UPI matches that overlap an EMAIL match span are dropped.
- If a legal-line capture contains a `08` §2.3 pattern preposition (`at|with|join|joining|from|welcome to|behalf of`) followed by a capitalised word, only the text after the last such preposition is kept.
**Files:** `claims/regexes.py`, `claims/org.py`.

### D-25 · 2026-10-05 · Signed image token
**Context:** The `04` §6 token is `base64url(hmac(...))` only, so the server cannot tell which image or expiry it covers.
**Decision:** `token = base64url(sha256_hex + "." + expiry_unix + "." + hmac_sha256(SPECIAL26_SHARE_SALT, sha256_hex + "." + expiry_unix))`. Checked with a constant-time compare and the expiry.
**Files:** `api/public_img.py`.

### D-26 · 2026-10-05 · P05 without an official domain
**Context:** P05 call A uses `-site:{o1}`, which is undefined when P01 found nothing.
**Decision:** The clause is omitted. P05 still runs, since it needs only the org.
**Files:** `probes/p05_chatter.py`.

### D-27 · 2026-10-05 · Lens image path (task T0.6)
**Context:** `04` §6 lists SerpApi image upload first, with a signed URL as the fallback.
**Verified** (https://serpapi.com/google-lens-upload-an-image, read 2026-10-05):
- `POST https://serpapi.com/image`, `multipart/form-data`, field `image`, max **500 KB**.
- The response is `{"message": ..., "image_id": "..."}`. It is then passed as `engine=google_lens&image_id=...`, and `url` can be omitted.
**Decision:**
- Upload is the primary path. It works locally without a public URL.
- Images are resized to 1024 px on the long side (`04` §6), then JPEG quality is stepped down until the file is ≤ 500 KB.
- The signed URL is the fallback when an upload fails and `SPECIAL26_PUBLIC_BASE_URL` is set.
- The upload is not a search, so it writes no ledger row. This still needs confirming against the account's search counter in the spike.
- Cache key: by `image_sha256` (D-12).
**Files:** `serp/client.py`, `probes/p09_image.py`, `intake/images.py`.

### D-28 · 2026-10-05 · Engine field names verified against SerpApi docs
Sources: https://serpapi.com/google-lens-api, /google-forums-api, /google-jobs-api, /maps-local-results, all read 2026-10-05. The live fixtures from T0.5 are still pending a key.
- **google_lens:** `type` ∈ {all, products, exact_matches, visual_matches}. Localisation is `hl` + `country` (no `gl`), so the client sends `country = SPECIAL26_GL` for Lens. Match fields: `position, title, link, source, thumbnail, image`. The result array for `type=exact_matches` is assumed to be `exact_matches`; the fixture will confirm.
- **google_forums:** results in `organic_results[]` with `title, link, snippet, source, displayed_meta`. There is no separate `date` field. The age shows in `displayed_meta` ("14 years ago"), so the P05 24-month rule parses relative ages from it.
- **google_jobs:** `jobs_results[]` with `title, company_name, location, via, share_link, apply_options, job_id`, matching `08` P07. `location` and `uule` can't be combined, so P07 sends `location` only.
- **google_maps** (`type=search`): `local_results[]` with `title, type, types, website, address, rating, reviews` (a count), and sometimes a truncated `user_review`. `place_results` appears for single-place answers.
**Decision for P08_REVIEWS_SCAM:** Review text is read only from what the search response already holds: `user_review`, plus `place_results.user_reviews` snippets if present. No extra reviews call, since the budget doesn't allow it. This makes the signal weaker than `08` implies; the gap is recorded here and the code stays.
**Files:** `serp/client.py`, `probes/p05_chatter.py`, `probes/p07_role.py`, `probes/p08_office.py`.

### D-29 · 2026-10-05 · Live spike results (task T0.5)
Fixtures are in `backend/tests/fixtures/serp/`. 7 credits spent: 5 engines, 1 Lens call that timed out but was billed, 1 Lens stock test.
- **Lens latency:** SerpApi reported `total_time_taken` 13.6 s on one call, and 16.6 s wall clock on another. Both exceed the 10 s HTTP timeout and the FR-25 12 s probe timeout.
  - **Decision:** HTTP timeout is 30 s for `google_lens` and stays 10 s for other engines. P09's probe timeout is 30 s and every other probe keeps 12 s. P09 runs in parallel, so this keeps NFR-01 (p95 ≤ 45 s). A timed-out request is recorded as `spent`, not `refunded`, because SerpApi completes and bills it anyway: the retry came back in 0.3 s from SerpApi's own cache.
- **Lens exact matches:**
  - A Wikimedia portrait returned `"error": "Google Lens hasn't returned any results for this query."`. The empty-result rule catches it, and it's kept as fixture `google_lens_exact_empty.json`.
  - A popular Pexels portrait returned 400 `exact_matches[]` with fields `position, title, link, source, source_icon, thumbnail, date, actual_image_width, actual_image_height`. `pexels.com` hits came at positions 13, 92 and 105. P09 scans all returned matches, not just the top 10, so `P09_STOCK_PHOTO` works as specified.
- **google (entity):** `knowledge_graph.website` = `http://www.techmahindra.com/`, which registers as `techmahindra.com` ✓. The KG `phone` is a US number (`+1 214-974-9907`). It is still listed as an official contact per `08`, labelled with its source. `careers.techmahindra.com/...` appears in organic results (position 6), which gives the careers contact.
- **google_jobs:** `jobs_results[]` has both `title` and `job_title`. P07 uses `title`. The query "Data Analyst Intern Tech Mahindra" returns a real listing, "Data Analyst Intern at Tech Mahindra". So in the live G1 run, `P07_ROLE_LISTED` (-1.0 existence) will likely fire and S drops from 8.0 to 7.0. Tier, red_kind, decisive set and reason 1 are unchanged. The worked-example unit test keeps the `08` §6.1 findings exactly, and the G1 golden test asserts only what `14` §3 lists.
- **google_news:** `news_results[]` with `date` and `iso_date`. P05 uses `iso_date` for the 24-month rule.
- **google_forums:** `organic_results[]`. Its age is only in `displayed_meta` ("10+ comments · 1 year ago"), as D-28 predicted.
- **google_maps:** `local_results[]` with `type`, `types`, `website` (`techmahindra.com` ✓), `reviews_link`, and `user_review` on 2 of 3 places. Types seen: "Software company", "Corporate office", which are in the P08 match list ✓.
**Files:** `serp/client.py`, `scripts/spike_engines.py`, `pipeline/runner.py` (per-probe timeout), `probes/p05`, `p07`, `p09`.

### D-30 · 2026-10-05 · Seed verification and `bank.in`
**Context:** T0.8 requires official domains verified against each company's own site. `scripts/verify_seeds.py` fetched every domain over HTTPS and found:
- **Banks:** HDFC, ICICI, Axis and Kotak now redirect to `hdfc.bank.in`, `icici.bank.in`, `axis.bank.in` and `kotak.bank.in`. `sbi.bank.in` answers too.
- **LTIMindtree** redirects to `ltm.com`.
- **AICTE** redirects to `aicte.gov.in`.
- **tldextract:** its bundled public-suffix snapshot doesn't list `bank.in`, so every bank resolved to the same registrable domain, `bank.in`.
**Decision:**
- The new domains are added alongside the old ones, which are still used for email.
- tldextract runs with `extra_suffixes=("bank.in", "fin.in")` (the RBI-restricted zones) everywhere, via the shared `domains/classify.py:EXT`.
- `source_url` is the final URL after redirects; `verified_on` is 2026-10-05. Persistent Systems' site is behind a bot check, so it keeps the URL from the first pass.
- 54 companies and 6 schemes. The `06` target of 80 is still open.
- `cities.txt` has 491 cities and tech localities, without PIN prefixes. No algorithm in `08` uses the prefixes.
- City names that are also common first names (Anand, Sagar, Puri, ...) are left out so signatures don't turn into addresses.
**Files:** `data/seeds/*`, `scripts/verify_seeds.py`, `domains/classify.py`.

### D-31 · 2026-10-05 · Extraction guards not spelled out in `08`
**Context:** These came up while making G1 to G6 and the FR-10 tests extract correctly.
**Decision:**
- **Dictionary matching of companies:**
  - Aliases of 4 characters or fewer (TCS, EY, HCL, SBI) match exact case only.
  - Any brand surface that is all lowercase is ignored ("in reliance on", "@paytm").
  - A brand followed by a product word (Form, Pay, Meet, Drive, Docs, Jobs, UPI, ...) is ignored.
  - "Paytm" preceded by via, on, using, through, to, with or in is ignored, since it names the payment rail.
  - Schemes match without the casing guards.
- **AMOUNT regex (`08` §2.2), two bug fixes:**
  - The `rs`/`inr` prefix may not follow a letter ("Mrs. 5" is not ₹5).
  - The unit (`k`, `lakh`, `lpa`) must end at a word boundary ("Rs 2000 kit" is not ₹20,00,000).
  - Decimals are kept in the value: ₹1.5 lakh = 150000.
- **Address:**
  - A PIN line gives the whole line, and its city is the last city on the line.
  - A city-only address is the clause ending at the city, without leading prepositions ("at Infosys Limited, Mysuru" → "Infosys Limited, Mysuru").
- **Legal line:**
  - Descriptor suffixes (Technologies, Solutions, Services, Consultancy, Infotech, Softech) are kept as part of the name: "Brightpath Technologies", legal suffix "Pvt Ltd".
  - The legal-line and pattern steps reject names whose first word is in the stop list, or that are a city.
- **Process phrases** are matched on punctuation-flattened text ("Last date: today" = "last date today").
- **"non-refundable"** is normalised to "nonrefundable" before purpose matching, extending D-23 to purpose classification.
- **A process claim** is emitted only when at least one flag is true.
**Files:** `claims/org.py`, `claims/regexes.py`, `claims/extract.py`, `claims/amounts.py`, `data/seeds/lexicons.yaml`.

### D-32 · 2026-10-05 · P01, P02, P11 and scorer details
- **P01 Q2:** The second query (`"{org}" careers`) runs only when Q1 accepted nothing *and* the org has no seed domains. When the org came from the dictionary, its verified seed domains already form the official set (`08` unions them), so Q2 would spend a credit to learn nothing. `P01_NO_PRESENCE` keeps its meaning: nothing is known after Q2.
- **P01 careers contact:**
  - An organic link on an official domain counts if its path contains `/careers` or `/jobs` (as in `08`), or if its host starts with `careers.` or `jobs.`. The live fixture's only careers link is `careers.techmahindra.com/LCA/...`, whose path has neither.
  - The KG phone is listed only when an official domain exists.
- **P01 receipts:** P01 stores a receipt per official domain in `outputs.receipts`: the KG website, else the first organic result, else the seed `source_url` as a `rule` receipt. P02 cites these, which matches the `07` §4 example (the COMBOSQUAT receipt is the P01 knowledge graph).
- **P02 lookalike copy:** "The {what} {domain} ...", where what ∈ {sender domain, reply-to domain, link domain}. For the sender this reproduces the `07`/`08` string exactly.
- **P11 PERSONAL_UPI target** is one of:
  - "a personal UPI ID (te****@ybl)"
  - "through a payment link (host)"
  - "by scanning a QR code"
- **Runner:** dependency-driven (D-03). Unknown dependencies are ignored, so the registry can grow probe by probe. A probe that fails keeps the credits it spent in its result.
- **CLI:** runs with `check_id = None`. It's a developer tool, so only the daily cap applies; there is no check row to budget against.
- **Scorer:** `Verdict.effective` gives the per-finding effective weights for `findings.effective_weight`. Each finding keeps its message `vars` so decisive copy (D1, D2, D4) can name the org, amount and scheme without re-deriving them.
**Files:** `probes/p01_entity.py`, `probes/p02_sender.py`, `probes/p11_policy.py`, `pipeline/runner.py`, `scoring/aggregate.py`, `cli.py`.

### D-33 · 2026-10-05 · Deploy target: Railway free plan
**Context:** `04` §8 allows Render or Railway. The user chose Railway's free plan and has an account. Per Railway's 2026 pricing as summarised in third-party comparisons: a 30-day trial with $5 credit, then $1/month capped at 1 vCPU and 0.5 GB RAM. No cold starts. Volumes are supported.
**Decision:**
- One container, one uvicorn worker, built to fit in 0.5 GB RAM.
- Tesseract runs only when an image needs OCR.
- SQLite lives on a Railway volume mounted at `/app/data`. Volume size on the free plan is to be confirmed at deploy time.
- Seeds ship inside the image at `/app/seeds` (`SPECIAL26_SEEDS_DIR`), so the volume mount can't hide them.
- If the free plan's RAM or volume proves too small, fall back to Hobby ($5/month) with the same image.
**Files:** `Dockerfile`, `special26/seeds.py`, `railway.json` (at deploy).

### D-34 · 2026-10-05 · Google ignores site restrictions; P04 fallback; SerpApi timeouts
**Observed live** (fixtures in `backend/tests/fixtures/serp/google_notice_*.json`; 8 credits on this investigation, 15 in total today). These queries all returned off-site pages (YouTube, Reddit, blogs) and not one techmahindra.com result:
1. `(site:techmahindra.com) (fraud OR ...)` (the `08` form)
2. `site:techmahindra.com (fraud OR ...)`
3. The same with `nfpr=1`, where SerpApi then reported "Results for exact spelling"
4. `site:techmahindra.com recruitment fraud`
5. `as_sitesearch=techmahindra.com`

The org query `"Tech Mahindra" recruitment fraud notice` didn't surface the company's own notice either. Google latency also varied widely: SerpApi `total_time_taken` was 0.8 to 2.3 s on some calls and 19.6 to 23 s on others, and three calls timed out at our 10 s limit.

**Decision:**
- **P04 runs the `08` query unchanged** (1 credit), but a result counts as the employer's notice only if its registrable domain is in the official set. Without that filter, P04 had produced a false `P04_NOTICE_FOUND` from a YouTube video.
- **Fallback:** if no on-site notice comes back, P04 uses the employer's own notice recorded in `known_entities.json` (`fraud_notice_url`, `fraud_notice_quote`, `fraud_notice_verified_on`). The receipt is `kind = rule`, `rule_id = known_entities.fraud_notice`, with the notice link and the verified quote. `P04_NOTICE_NO_FEE` is set only if the quote matches the `08` NO_FEE regex. The finding code and its meaning ("the employer's own words") are unchanged; only the receipt source differs, and the receipt says so.
- **Verified 2026-10-05:** `https://careers.techmahindra.com/CPDOC/Recruitment_Fraud.pdf` (fetched directly) says "Tech Mahindra does not charge any fee or collect any deposit from candidates for any jobs". Other employers get a notice only after the same manual check.
- **P05 call A** (`-site:{o1}`): the exclusion can't be relied on either, so P05 also drops results on official domains client-side.
- **Timeouts:**
  - HTTP timeout is 22 s for all engines except Lens (30 s).
  - Probe timeouts: local probes keep FR-25's 12 s, SerpApi probes 25 s, P01 45 s (two sequential calls), P09 35 s.
  - This deviates from FR-25 because of the measured latency. NFR-01 (p95 ≤ 45 s) is checked again on the deployed URL at M2.
- **To revisit:** retest `site:` once on 2026-10-07 (1 credit). If it works again, the filter stays anyway and the fallback is simply used less.
**Files:** `probes/p04_fraud_notice.py`, `data/seeds/known_entities.json`, `serp/client.py`, `probes/base.py`, `probes/p01_entity.py`.

### D-35 · 2026-10-05 · API details not fixed by `07`
- **Additive fields:**
  - `verdict.sub_line` (the `09` S4 sub line, rendered server-side next to `headline`).
  - Top-level `warnings` on `GET /api/checks/{id}`, which S2 needs for the OCR banner.
  - Both are left out of share responses.
- **Uploads:**
  - Stored under `data/uploads/{check_id}/`, outside the static root, so purging one check never deletes another check's file.
  - At most 2 embedded images per PDF become `offer_image` artifacts.
  - The type is detected by magic bytes. `.eml` is accepted by extension or `message/rfc822` plus a header sniff, because browsers often send it as `application/octet-stream`.
- **Rate-limit key:** `sha256(ip | SPECIAL26_SHARE_SALT | UTC day)`, taking the first `X-Forwarded-For` hop (Railway proxy). Rate limiting applies in `live` only, as NFR-07 says.
- **Daily cap:** checked at `POST /run`, and at create when `auto_run=true` (`07` §9).
- **Expiry:** checked lazily on PUT/run (30 min idle → `expired`, raw data purged, 410). Retention does the same hourly.
- **PUT claims:**
  - An unchanged claim keeps its source and id. A changed one becomes `source = user` and keeps its id.
  - Changing a claim's type, or citing an unknown id, gives 422.
  - Org names typed by the student go through the dictionary, so "TCS" becomes "Tata Consultancy Services" with its `entity_id`.
- **SSE:** subscribe first, then replay from `check_events`, so no event falls between the two. `?last_event_id=` works as well as the header. The stream ends immediately for a terminal check once its stored events have been sent.
**Files:** `api/checks.py`, `intake/ingest.py`, `api/health.py`, `main.py`.

### D-36 · 2026-10-05 · Frontend build choices
- **Stack:** the Vite scaffold installed React 19, React Router 7, Tailwind 4 (`@tailwindcss/vite`) and TanStack Query 5. `05` names React 18, but nothing in the spec depends on React 18 APIs, so the newer versions stay.
- **Fonts:** Public Sans (civic, form-like) for everything; IBM Plex Mono only inside receipt slips. Both are self-hosted via `@fontsource`, so offline replay in Docker renders the real fonts.
- **Palette:** page `#F5F6F8`, ink `#1C2433`, action ballpoint blue `#2B3FA0`, plus the `09` §5 tier colours exactly. A receipt opens as a printed slip with a perforated edge, the one deliberate visual flourish.
- **Example chips:** "WhatsApp offer with a fee" (G1), "PM Internship form" (G2), and "Startup offer, documents first" (G4). The third one stands in for G3 until the consented `.eml` exists (D-14). `09`'s "Real offer email" label isn't used for G4, because that wouldn't be true.
- **Receipt drawer:** opened from a reason, "Why it matters" shows that reason's sentence. Opened from All findings, it shows the finding's own message. The employer's seed notice is labelled "Employer's own notice" with its verified date (D-34).
- **Rule receipts** carry their `09` S5 sentence in `receipt.extra.text`, so the copy lives only in `scoring/copy.py`.
- **Serving:** FastAPI serves `frontend/dist` (`SPECIAL26_STATIC_DIR` in Docker), with an SPA fallback for every non-`/api`, non-`/public` path.
**Files:** `frontend/*`, `backend/special26/api/web.py`, `backend/special26/probes/base.py`.

### D-37 · 2026-10-06 · P07 and P08 inputs
- **P07 location:** `location = "{city}, India"` when an address gives a city, else `"India"`. If SerpApi rejects the location string (an UpstreamError mentioning "location"), P07 retries once with `"India"`.
- **P08 query:** an address claim is queried as an address only if it has a PIN or a comma-separated part ("Tech Mahindra Limited, Noida"). A bare city mention ("Join our Bengaluru campus") falls back to `08`'s `{org} office {city}`. `P08_NOT_FOUND` and `P08_RESIDENTIAL` apply only to address queries, as `08` says.
- **P08 matching:**
  - `08`'s type lists match case-insensitively. Entries longer than 3 characters also match as a substring ("Company" matches "BPO Company"), and "PG" must match exactly.
  - `P08_REVIEWS_SCAM` reads only the review text already in the search response (D-28).
  - The receipt link is a public Google Maps search URL built from the place title and `place_id`.
- **Org pattern fix:** the `08` §2.3 pattern allows dots inside names, so "Welcome to Acme Widgets. Office: ..." captured "Acme Widgets. Office". The capture is now cut at the first ". ".
**Files:** `probes/p07_role.py`, `probes/p08_office.py`, `claims/org.py`.

### D-38 · 2026-10-06 · P09 Lens implementation
- **Upload path verified live:** `POST https://serpapi.com/image` with `api_key` and the `image` file returned an `image_id` in 1.4 s. Lens `exact_matches` by `image_id` then took 7.5 s and returned 400 matches, with `pexels.com` at positions 12 and 111. 1 credit. Fixture: `google_lens_g5_upload.json`.
- **Order of attempts:**
  1. SerpApi upload.
  2. On upload failure, the signed URL `{SPECIAL26_PUBLIC_BASE_URL}/public/img/{token}` (D-25).
  3. With neither available, `skipped_no_public_url` (`04` §6).
- **Replay** never uploads: Lens results are keyed by `image_sha256` (D-12) and searched with `image_id = "replay"`, which the cache key ignores.
- **`P09_STOCK_PHOTO`** scans every exact match; stock hits sit deep in the list.
- **`P09_PHOTO_OTHER_NAMES`** counts distinct registrable domains whose match title holds a capitalised two-word name with `fuzz.ratio < 70` to the HR name. When there is no HR name, any such name counts.
- **`P09_PHOTO_OFFICIAL`** uses `fuzz.partial_ratio ≥ 80` between the HR name and the match title, so that "Neha Kapoor - HR Manager" counts.
- **Letter call:** it runs only when `budget - reserved_calls ≥ 3` (`05` §8). The runner computes `reserved_calls` before wave 1, counting probes that are applicable or wait only for P01. The rule is the same in replay, so a replay reproduces exactly what was recorded.
**Files:** `serp/client.py`, `api/public_img.py`, `probes/p09_image.py`, `pipeline/runner.py`.

### D-39 · 2026-10-06 · P03 inputs
- **P03 depends on P01**, extending D-03: `P03_DKIM_ALIGNED_OFFICIAL` needs the official set, which only P01 produces. P02 already waits for P03, so the order is P01 → P03 → P02.
- **Input:** P03 re-parses the `.eml` artifact from disk during the run. Raw files are purged only after the verdict (NFR-06).
- **DKIM domain:** `header.d`, or the domain of `header.i` when providers report only `header.i` (Gmail's format, as in the fixture).
- **`skipped_forwarded`:** the Subject starts with `Fwd:` or `Fw:`, or there is no `from_headers` sender claim, meaning the student marked the From address "This is mine" (D-09).
- **Receipts:** `rule` receipts carrying the topmost `Authentication-Results` header (trimmed to 400 characters) in `extra.header`.
**Files:** `probes/p03_headers.py`, `probes/registry.py`.

### D-40 · 2026-10-06 · Template fingerprinting and P10
- **Normalisation** (`08` §7.1):
  - Placeholders are applied in the `08` order.
  - The dictionary entity's aliases also become `<org>`.
  - Redaction placeholders `<RECIPIENT*>` map to `<recipient>`, and `<ID>` (Aadhaar/PAN) to `<num>`.
  - Tokens are runs of word characters, so Devanagari survives; punctuation is dropped.
- **No percentages in reasons:** `P10_TEMPLATE_MATCH_*` copy no longer includes "{similarity}%". A perfect match would have read "100% similar", which `09` §4 forbids in reasons. The estimated Jaccard is kept in `receipt.extra.similarity`.
- **Receipts:**
  - A seed match is `local_memory`, linking to the seed's `# source:` URL.
  - A match with an earlier red check shows "An earlier check marked high risk" with no link, so no other student's check is exposed.
- **Every check gets a template row:** `scam` if red, else `unlabeled` (`08` §7.5). Seeds load at startup as `seed:<file>`.
- **Distinctive sentence:** sentences split on `.`, `!` or `?` plus whitespace, a blank line, or a line break followed by a capital. Sentences with `<RECIPIENT>` are never sent.
**Files:** `template/*`, `probes/p10_template.py`, `scoring/copy.py`, `storage/repo.py`, `storage/retention.py`, `pipeline/runner.py`.

### D-41 · 2026-10-06 · P06, identifiers and campaigns
- **Identifiers:** one helper (`campaign/identifiers.py`) produces `08`'s hard identifiers in priority order (upi, phone, domain, email) for P06, the `identifiers` table (D-10) and campaign edges.
  - Domains come from the sender, the reply-to and `other`/`document` links whose class is typosquat, combosquat, tld_swap, homoglyph or unrelated.
  - Emails count unless they are official or freemail.
- **P06 keeps local memory when search fails:** if the Google part fails (replay miss, budget, upstream), the probe keeps that status, so coverage stays honest, but still returns any `P06_ID_SEEN_LOCALLY` findings. The earlier red checks are local evidence that needs no search. (G6b in replay depends on this.)
- **"Present" in a result:** identifier matched in title + snippet + link, phones by digits only. `P06_ID_REPORTED`: one finding per distinct registrable source domain. `P06_ID_ON_OFFICIAL`: phone or email only, as in `08`.
- **Copy:** `P06_ID_SEEN_LOCALLY` reads "...appeared in 1 earlier check / 3 earlier checks marked high risk" (pluralised). Its receipt links to `/campaign/{id}` when the earlier check is already in one.
- **Campaigns:**
  - Union-find works over persisted `campaign_members`. Neighbours are red or amber checks sharing an identifier, an image within pHash Hamming distance 6, or a template with J ≥ 0.6 (seeds excluded). Freemail and platform domains are never edges.
  - The lowest touched campaign id survives; merged campaigns keep `merged_into` for the 301.
  - A check with no neighbour gets no campaign.
- **`edge_counts`** = count of members by the edge that linked them. `orgs` are in first-seen order.
- **`/api/campaigns/{id}`:** identifiers shared by ≥ 2 members are masked, except domains, which are shown in full (`03` §4.3).
**Files:** `campaign/*`, `probes/p06_identifier_trace.py`, `api/campaigns.py`, `storage/repo.py`, `pipeline/runner.py`.

### D-42 · 2026-10-06 · P05 details
- **Official filter:** the `-site:{o1}` exclusion can't be trusted (D-34), so results on official domains are dropped client-side.
- **Complaint dates** (24-month window):
  - News `iso_date`.
  - A relative age ("1 year ago") in Forums `displayed_meta` or Google `date`.
  - An absolute "Mar 3, 2024" date.
  - A result with no date stays eligible, as `08` says "date (if any)".
- **"Contains the org":** `fuzz.partial_ratio(org, title + snippet) ≥ 85`, case-insensitive.
- **`P05_COMPLAINT_NAMES_SENDER`:** the sender's domain counts only if it is a suspect class (typosquat, combosquat, tld_swap, homoglyph, unrelated), because "gmail.com" would match everything. HR names count only when they have at least two words.
- **Failure handling:**
  - Forums errors are skipped quietly (`08`).
  - If one of Google or News fails, P05 still reports `ok` on the remaining results, recording `outputs.failed_calls`. This is consistent with `04` §10's forums degradation.
  - Only when both fail does P05 raise, which makes its status `error` or `skipped_*`.
- **`P05_PIB_FACTCHECK`:** any result from the three calls whose registrable domain is `pib.gov.in`, or with "PIB Fact Check" in the title, counts when a scheme claim exists. It doesn't need to meet the complaint criteria.
**Files:** `probes/p05_chatter.py`.

### D-43 · 2026-10-06 · Share and campaign pages
- **The share view drops `check_id`.** The check id is the only key to the unmasked `GET /api/checks/{id}`, so a shared link must not reveal it.
- **More masking on share pages:** receipt `query` and `title` are masked as well as `snippet`, because P06's query quotes raw identifiers. `claim_ids` are emptied.
- **Field:** `shared_on` is added to the share response for "Checked on {date}" (S7).
- **`/s/{token}`:** rendered server-side with `og:title` (headline) and `og:description` (reason 1), HTML-escaped. Crawler fetches of this page don't count as views; only `GET /api/share/{token}` does.
- **The share page** shows the verdict card and next steps without the "Tell your placement cell" step, since the reader is already the person it was shared with.
- **Campaign page:**
  - The title uses the edge type with the highest count.
  - Tier words: High risk, Unverified, Consistent, Not enough information.
  - Template similarity is shown as "{n} offers share near-identical wording" (D-19).
- **Verdict screen:** a check in a campaign shows "Linked to N other offers using the same details", linking to the campaign page (`09` §1, F → J).
**Files:** `api/share.py`, `api/checks.py`, `api/web.py`, `frontend/src/pages/{Share,Campaign,Check}.tsx`.

### D-44 · 2026-10-06 · Reason direction
**Context:** On the first full live G1 run (`chk_353i4x65ya7r`, 7 credits, 7.9 s, S = 6.0), `P07_ROLE_LISTED` (−1.0) tied `P11_PERSONAL_UPI` (+1.0) on |w|. Under the `05` tiebreak it became reason 3 of a red verdict, so evidence for a genuine offer appeared under "Why" the offer is high risk. The `08` §6.1 example, where reason 3 = PERSONAL_UPI, had no P07/P08 findings.
**Decision:**
- After decisive rules, reasons first list findings pointing the verdict's way: positive weights for red and amber, negative for green. Grey keeps pure |w| order. Within each direction the order is still |effective| desc, probe_id, `08` table order (D-05). So FR-33's "ordered by absolute contribution" holds within each direction.
- Counter-evidence stays visible under "All findings".
- The worked example still gives D1, D3, PERSONAL_UPI. The live G1 case is now a unit test.
**Files:** `scoring/aggregate.py`, `tests/unit/test_scoring.py`.

### D-45 · 2026-10-06 · Per-claim view and P12, prompted by a user's real offer letter
**Context:** The user ran their own offer letter. P01 found no official website: both Google queries returned only LinkedIn posts and Scribd copies of offer letters. The letter's own website `www.thiranex.in` was extracted as a link claim, but nothing about it was shown, so it looked "ignored". The PRD core story (`02` §5) promises a card that "lists each claim, what the web says about it". Findings were grouped only by family.
**Decision:**
- **New section on the private verdict page,** "What the offer claims, and what we found". It lists each claim with the findings that cite it (via `claim_ids`), each opening its receipt.
  - A claim no finding cites gets a neutral sentence that says only what is true. For a link: whether its registrable domain is among the official domains P01 found, and whether P06 searched for it.
  - The offer's own website is never treated as official. Official contacts still come only from P01/P04 (`09` S6). This is a display of existing evidence, not a new finding, weight or rule.
- **P12_DOMAIN_AGE built** (stretch item 1, FR-21) via `SerpClient.rdap` (D-11):
  - Up to 3 suspect-class domains are checked: sender, reply-to and `other`/`document` links. One finding is emitted, for the youngest.
  - RDAP verified live: `thiranex.in` registered 2025-09-09, which is over a year before the check, so no finding.
  - The constructed demo domains (`techmahindra-careers.in`, `infosys-careers.co`) have no registration record, confirming `14` §3's requirement that they be unregistered.
**Files:** `probes/p12_domain_age.py`, `probes/registry.py`, `frontend/src/components/ClaimsChecked.tsx`, `frontend/src/pages/Check.tsx`.

### D-46 · 2026-10-06 · Seed scam corpus is verbatim-only; credits are the binding constraint
**Seed corpus (`08` §7.5):**
- I searched news reports, employer notices (Dr. Reddy's, Mahindra Aerospace, Wipro), PIB fact-checks, CyberPeace, consumercomplaints.in and forums for transcribed scam texts.
- Published sources describe the messages but almost never reprint them. The verbatim fragments found (consumercomplaints.in, HCL complaint 2013/2015: "You have to deposit the (Cash) as an initial amount in favor of our company accountant ... Rs.6, 725/-"; techenclave Wipro thread) are under P10's 30-token minimum.
- **Decision:** the seed corpus holds only verbatim texts with a source. No texts are written by us. A P10 receipt reads "Known fake offer text" and links to its source, so a reconstructed text would be a false receipt.
- Until real texts arrive from the team (redacted student messages), P10's local part matches against checks that ended red (`08` §7.5's second source), and the quoted-sentence search still runs. This is a gap against `12` §1 ("≥ 25 scam templates"); reported in `STATUS.md`.

**Credits:**
- `GET serpapi.com/account.json` (2026-10-06): Free Plan, 250 searches/month, 100 left, 150 used this month.
- `11` §6 assumes a live recording of 450 to 1,100 calls. That isn't affordable.
- Pending the user's answer on extra credits: no more exploratory live calls. The remaining credits go first to recording `demo.db` for the golden cases (about 50).
**Files:** `data/seeds/scam_templates/`, `docs/STATUS.md`.

### D-47 · 2026-10-06 · Constructed seed corpus, as directed by the user
**Context:** D-46 found no verbatim scam texts long enough to fingerprint. The user chose: "replicate stuff like it happens in real life", with no real student messages for now. The user is getting more SerpApi credits. Until a new limit is confirmed, the deployed daily cap is 15 (`SPECIAL26_DAILY_CREDIT_CAP`, set on Railway).
**Decision:**
- **27 constructed templates** in `data/seeds/scam_templates/`, each modelled on a pattern described in a cited public report or employer notice: amounts, purpose, channel, pressure tactics.
  - Each file starts with `# source:`, `# provenance: constructed` and `# note:`.
  - The two fragments quoted verbatim in forum posts (techenclave Wipro thread, consumercomplaints.in HCL complaint) are kept word for word inside their templates, and the note says so.
  - Identifiers are written as placeholders (`<upi>`, `<phone>`, `<email>`, `<url>`), so no real or real-looking UPI IDs, numbers or addresses are in the repo.
- **Honest receipt:** a P10 match on a constructed seed reads "Matches a fake offer pattern described in a public report" and links to that report, with `extra.provenance = constructed`. It never says "Known fake offer text". `08`'s finding codes and weights are unchanged.
- **Checked before shipping:**
  - All 27 texts are ≥ 30 tokens.
  - Max seed-to-seed Jaccard is 0.08, so they are varied.
  - Golden inputs G1, G2, G4, G5, G6a and G6b score at most 0.03 against any seed, so the golden verdicts don't depend on the corpus.
  - The genuine fixture offer scores 0.03, so there's no false template match.
- **README limitation:** the corpus is constructed from reports, not collected from victims.
**Files:** `data/seeds/scam_templates/*.txt`, `storage/retention.py`, `probes/p10_template.py`, `tests/unit/test_template.py`.

### D-48 · 2026-10-06 · Probes keep local evidence when search is unavailable
- **P01:** if its first search fails (replay miss, budget, upstream error, or an engine masked for ablation) and the org came from the dictionary, the verified seed domains still become the official set, with `P01_OFFICIAL_FOUND` citing the seed receipt. The status records the failure (`skipped_replay_miss` and so on), so coverage stays honest. With no seed, P01 still raises.
- **P10:** if the quoted-sentence search fails, the local MinHash match is kept, with the failure status.
- **Why:** a SerpApi outage shouldn't throw away evidence that needs no search. B3 "local only" (`11` §4) needs P10's local part and seed-based lookalike detection.
- **Engine masking:** `Settings.masked_engines` makes `SerpClient.search` raise `ReplayMiss` for the masked engines (`11` §6).
**Files:** `probes/p01_entity.py`, `probes/p10_template.py`, `serp/client.py`, `config.py`.

### D-49 · 2026-10-06 · Evaluation set and harness
**Context:** `11` §2 targets 100 cases (minimum 60), split by category. The user has no real material to share for now ("replicate stuff like it happens in real life"), and credits are scarce (D-46).
**Decision:**
- **60 constructed cases** (`eval/build_cases.py`, deterministic; files in `eval/cases/`):
  - **Fraud, 30:**
    - `public_report` ×10: each follows a cited report's pattern.
    - `lookalike_fee` ×6: constructed lookalike domains of real brands.
    - `scheme_impersonation` ×4.
    - `persona` ×4: documents first, no fee, no photo, so expected amber; Lens would be needed for red.
    - `campaign_variants` ×6: 3 pairs sharing a UPI ID across brands.
  - **Genuine, 30:**
    - `official_template` ×8: real employers, real domains, no fee.
    - `jobs_listing_message` ×16: replaces `consented_real`, which has no data.
    - `small_startup` ×6: fictional companies, amber or grey is correct.
- **Split:** dev/holdout ≈ 40/60 per label by whole `template_group` (fraud 13/17, genuine 12/18).
- **`eval/run_eval.py`** runs every case through `run_check` (the production path) on a fresh DB per system, in case-id order, so campaign memory builds up as in production.
  - Systems: S26, B0, B3 (all six engines masked).
  - Ablations: one engine (or `news+forums`) masked per run.
  - Output: rows in `eval_runs`/`eval_results` and `eval/report.md`, with metrics plus 95% Wilson intervals, confusion matrices, an ablation delta table, every false red with its top 3 reasons, latency and credits.
  - B1 and B2 are stretch (`12` §3) and not run.
- **Recording S26:** needs about 9 searches per case, so roughly 540 for all 60. That waits for the extra credits. Until then only B0 and B3 can be reported.
**Files:** `eval/*`.

### D-50 · 2026-10-06 · Golden tests and recording
- **Golden runner:** `backend/tests/golden/golden_run.py` runs G1, G2, G4, G5 (with `g5_hr_photo.jpg` as `hr_photo`) and G6a then G6b through the real API.
- **Two checks:**
  1. The `14` §3 invariants, hardcoded. G1: red, impersonation, decisive {D1, D3}, reason 1 = D1. G2: D2 and the `pminternship.mca.gov.in` contact. G4: amber with its three findings. G5: red, impersonation, with FREEMAIL, STOCK_PHOTO and CANDIDATE_PAYS. G6: shared campaign, G6b has SEEN_LOCALLY.
  2. A snapshot (`expected.json`: tier, red_kind, decisive, reason 1), written at recording time. This freezes the parts `14` leaves to "whatever the recording shows" (G5's decisive set).
- **`scripts/record_demo.py`:** runs live with `SPECIAL26_RECORD_TO=data/demo.db`, reusing the local cache. If an invariant fails, it writes no snapshot. It adds a `recording` row (time, git sha, note).
- **Tests skip** until `demo.db` has a recording. G3 is a strict xfail (D-14).
- **Contact fix:** P01 now also outputs `official_hosts`, the seed hostnames as written. The "website" official contact uses it, so G2 links to `https://pminternship.mca.gov.in` rather than the registrable `mca.gov.in` (`14` §3 G2).
**Files:** `backend/tests/golden/*`, `scripts/record_demo.py`, `probes/p01_entity.py`, `scoring/nextsteps.py`.

### D-51 · 2026-10-06 · Extraction fixes found by evaluation (11 §8: extraction bugs may be fixed freely)
- **Amount purpose:** if no purpose keyword lies within the 12-token window, the whole (D-23-clipped) sentence is used. F-RPT-03: "You have to deposit the (Cash) as an initial amount ... for Rs. 4,250/-" has "deposit" 14 tokens before the amount.
- **Role patterns added** to `08` §2.1's two:
  - "offer you the / for the / interview for (the) position|role|post of X"
  - "applying for / application for / regarding / interview for / clearing the interview for / offer you the X (role|position|opening|with|at|()"
- **City-only address:** only the capitalised name before the city is kept ("Wipro, Pune"). A city inside a sentence without a comma becomes just the city, so P08 uses `{org} office {city}`.
- **No weights, thresholds or decisive rules changed.** The golden snapshot is unchanged and its tests pass.
**Files:** `claims/amounts.py`, `claims/extract.py`.

### D-52 · 2026-10-06 · Evaluation under the free-plan credit limit (user: "make it work with the credits which are available now")
- **Responses reused:** `data/eval.db` was seeded with every response already paid for (`demo.db` and the local cache), and the harness prefills its cache from it, so nothing is bought twice.
- **Cost dry run:** a replay of all 60 cases against what was already recorded showed 269 searches still needed. Not affordable.
- **Recorded live:** 13 cases for 41 searches. The cheapest per category, plus the campaign pair F-CMP-01a/b: `F-RPT-10,F-RPT-03,F-RPT-04,F-RPT-09,F-SCH-01,G-OFF-03,G-OFF-07,G-OFF-08,F-CMP-01a,F-CMP-01b,G-OFF-02,G-JOB-02,G-SUP-01`.
  - The guard `--max-credits` stops before a case once the cap is reached.
  - After the D-51 fixes, only the P07/P08 queries for the official-template genuine cases were re-recorded (6 searches). Other changed queries are left unrecorded and show `skipped_replay_miss` (lower coverage).
- **`eval/report.md`** has Part 1 (B0, B3 on all 60) and Part 2 (S26, B0, B3, 5 ablations on the 13). `eval/notes.md` holds the reading and the error analysis.
- **Harness fix:** campaign membership is read after all cases have run (F-CMP-01a joins only when 01b links to it).
- **Remaining SerpApi searches:** 18, kept for the live site (deployed daily cap 15).
**Files:** `eval/run_eval.py`, `eval/report.md`, `eval/notes.md`, `data/eval.db`, `.gitignore`.

### D-53 · 2026-10-06 · Constructed domains must be unregistered; README and GIF
- **RDAP check (2026-10-06) of every constructed lookalike domain:**
  - `techmahindra-careers.in`, `infosys-careers.co`, `hcltech-hiring.in`, `infosys-hr.xyz`, `tcs-careers.in`, `accenture-jobs.co`, `cognizant-hiring.in`, `drreddys-careers.com` and `aicte-internship-portal.in` are unregistered (404).
  - `de1oitte.com` (registered 2024) and `capgemini.co.in` (registered 2004, likely Capgemini's own) were in eval cases F-LKF-05/06. They were replaced by `de1oitte.co.in` (homoglyph) and `capgemini.net.in` (tld_swap), both unregistered, so `14` §3's rule ("constructed domains must be unregistered") holds.
  - Neither case was in the recorded subset, so no recordings changed and the report numbers are identical.
- **Recorded subset list** saved in `eval/recorded_subset.txt`.
- **`README.md`** covers `12` §5: the problem with sources, the GIF, live and replay run instructions, the engine-to-claim table, the eval table, limitations.
- **`docs/demo.gif`:** 24 frames at 390 px, captured from a local server in replay mode (no credits). It shows G1: confirm, verdict, employer-notice receipt, Google receipt, per-claim evidence, next steps.
- **Copy audit (T4.3):** no em dash in `frontend/src`, `README.md` or `docs/` status files, and no banned words in UI string literals. The backend copy is covered by `test_copy_rules`.
**Files:** `eval/build_cases.py`, `eval/cases/F-LKF-05.json`, `eval/cases/F-LKF-06.json`, `eval/recorded_subset.txt`, `README.md`, `docs/demo.gif`.

### D-54 · 2026-10-06 · Amber wording when only minor flags exist (user request)
**Context:** The user found "Could not verify this offer. Confirm through the official channel before you share documents or pay." on most offers, and inaccurate for offers where the official site was found and the only flag was minor. Their check of "Quantis Sphere": official site found, office not on Maps, only flag `P11_URGENCY` (+0.5), S = 0.5.
**Decision:**
- Tier and score are unchanged. Only the amber headline and sub line differ.
- When no finding has an effective weight of +1.0 or more, the headline reads "No serious warning signs, but this offer is not fully confirmed." The sub line is "Some details matched {org}, others could not be checked. Confirm through {official_contact} before you share ID documents."
- Any concern of at least +1.0 (no official presence, freemail sender, fee ask, lookalike domain, ...) keeps the `09` S4 amber copy exactly. G4 keeps it.
- The new strings pass the same copy-rule test (no "scam", "safe", "guaranteed", no em dash).
**Files:** `scoring/copy.py`, `scoring/nextsteps.py`, `api/checks.py`, `tests/unit/test_scoring.py`.

### D-55 · 2026-10-06 · P08: places must be at the offer's address
**Context:** Same check. The Maps query for "7/38c/1 Devicode, Tholady, ..., Tamil Nadu 629170" returned three unrelated places matched on words in the address: "7" (PIN 629178), "THOLADY" (housing society, 629152) and "Moovottukonam" (beauty parlour, 629152). Nothing matched, so the UI said "Google Maps gave nothing conclusive". Had the housing society ranked first, `P08_RESIDENTIAL` would have fired on an unrelated building. 1 credit spent to inspect.
**Decision:**
- When the address claim has a PIN, a returned place counts as "at the address" only if its own address holds that PIN. A place with no address can't be ruled out, so it still counts.
- If no place is at the address, the result is `P08_NOT_FOUND` (`08`: "address query returns no place"); `08`'s weights are unchanged.
- MATCH, RESIDENTIAL and COWORKING are judged only on places at the address. RESIDENTIAL and COWORKING are not raised when the office matched.
- `outputs.places` (title, type, address, at_address) and `outputs.pincode` let the claims view say "Google Maps has no listing at PIN 629170. It matched words in the address to other places instead: ...".
- A Google web result showing the address (company site, registry) is not Maps evidence and isn't claimed as such.
**Files:** `probes/p08_office.py`, `frontend/src/components/ClaimsChecked.tsx`, `tests/unit/test_probes_m3.py`.

### D-56 · 2026-10-06 · No emoji; laptop and phone layouts (user request)
- **Icons:** tier and timeline emoji/glyphs (stop sign, warning, check, question, ✓, !, –) are replaced by inline SVG icons (`components/Icon.tsx`, no icon library). `09` §5 still holds: the tier shows as icon plus headline text, never colour alone.
- **Laptop (≥ 1024 px):**
  - Full-width header with a "Check an offer" link, and the content area widened from 40rem to 72rem.
  - Home: intro and "what we check" list beside the form card.
  - Confirm: fieldsets in two columns.
  - Verdict and share: the verdict card and per-claim evidence on the left, a sticky side column with campaign link, next steps and checks run.
  - Campaign: facts and member list side by side.
  - The receipt slip is a centred card.
- **Phones:** checked at 360 and 390 px with no horizontal scroll on home, verdict, share and campaign. The verdict band puts the icon beside the headline from 640 px up.
- **README GIF** re-recorded from replay with the new UI.
**Files:** `frontend/src/**`, `docs/demo.gif`.
