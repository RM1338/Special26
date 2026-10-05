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
