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
