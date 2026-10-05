# 08. Core Algorithm and Intelligence Design

This file is authoritative for probe IDs, finding weights, caps, thresholds and verdict rules. Ruleset version: `2026.10.1`. Weights live in `backend/special26/rules/weights.yaml` and must match the tables below.

## 1. Pipeline in one picture

```
offer (text, pdf, image, eml, hr_photo)
  -> intake (pdf text, OCR, eml headers)
  -> claim extraction (regex + dictionaries, optional LLM) -> student confirms
  -> probes P01..P12 (6 SerpApi engines + local rules + RDAP) -> findings with receipts
  -> scorer: family caps -> decisive rules -> tier rules -> reasons + coverage
  -> template signature + campaign linking
  -> verdict card
```

Design principle: **the offer is a list of claims, and each claim can be checked against the outside world.** We never ask "does this text sound like a scam". We ask "is the sender domain the company's domain", "does the employer's own site say it never charges fees", "is this HR photo a stock photo", and so on. Text style is used only for template reuse, where the question is again factual: "has this exact wording been reported before".

## 2. Claim extraction

### 2.1 Claim types

| Type | Fields | Extraction |
|------|--------|-----------|
| `org` | `name`, `legal_suffix`, `source` (`dictionary`, `legal_line`, `pattern`, `display_name`, `llm`, `user`) | §2.3 |
| `scheme` | `scheme_key` (e.g. `pm_internship`) | Dictionary, §2.4 |
| `sender_email` | `address`, `display_name`, `registrable_domain`, `from_headers` (bool) | `.eml` From, else first email after "from:", "regards", or in signature block (last 12 lines) |
| `reply_to` | `address`, `registrable_domain` | `.eml` Reply-To, else "reply to / send your documents to X" |
| `url` | `url`, `host`, `registrable_domain`, `kind` (`form`, `shortener`, `payment`, `messaging`, `document`, `other`) | Regex, §2.2 |
| `phone` | `e164`, `role` (`sender`, `recipient`, `unknown`) | Regex; role from ±6 tokens ("call", "WhatsApp", "contact HR" → sender) |
| `upi_id` | `vpa`, `handle`, `handle_known` (bool) | Regex, §2.2 |
| `amount` | `value_inr`, `purpose`, `payer`, `raw` | Regex plus window classifier, §2.5 |
| `hr_person` | `name`, `title` | Signature block: line before a title word (HR, Talent, Recruiter, Manager, Executive) |
| `address` | `raw`, `city`, `pincode` | Lines with a 6 digit PIN (`\b[1-9]\d{5}\b`) or a city from the 500-city list |
| `role` | `title` | "selected for the (position|role|post) of X", "as an? X (Intern|Trainee|Engineer|Analyst|Executive|Associate)" |
| `stipend` | `value_inr`, `period` | Amount classified as `stipend` or `salary` |
| `deadline` | `hours` | "within N hours", "today", "by tonight", "EOD", "before 6 PM" → hours ≤ 24; "within N days" → N*24 |
| `process` | flags: `no_interview`, `chat_only_interview`, `telegram`, `whatsapp` | Phrase lists, §2.6 |
| `legal_id` | `cin`, `gstin` | Regex, format validity only |
| `image` | `artifact_id`, `role` (`hr_photo`, `offer_image`) | From intake |

### 2.2 Regexes (Python `re`, IGNORECASE unless stated)

```python
EMAIL   = r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"
URL     = r"(?:https?://|www\.)[^\s<>\"')\]]+"
BARE_DOMAIN = r"\b(?:[a-z0-9\-]+\.)+(?:com|in|co\.in|org|net|io|xyz|online|site|top|info|co|live|work|careers|jobs)\b"
PHONE_IN = r"(?<!\d)(?:\+?91[\s\-]?|0)?([6-9]\d{4})[\s\-]?(\d{5})(?!\d)"
UPI     = r"\b([a-z0-9.\-_]{2,256})@([a-z]{2,64})\b(?!\.[a-z])"   # handle has no dot, so not an email
AMOUNT  = r"(?:₹|rs\.?|inr|rupees)\s?(\d{1,3}(?:,\d{2,3})+|\d+)(?:\.\d+)?\s?(k|lakh|lakhs|lpa)?|(\d{1,3}(?:,\d{2,3})+|\d+)\s?(?:/-|rs\b|rupees)"
CIN     = r"\b[LU]\d{5}[A-Z]{2}\d{4}(?:PLC|PTC|OPC|LLC|NPL|GOI|SGC|FTC|GAP|GAT)\d{6}\b"   # case-sensitive
GSTIN   = r"\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b"                                # case-sensitive
PIN     = r"\b[1-9]\d{5}\b"
```

Known UPI handles (sets `handle_known = true`): `ybl, ibl, axl, okaxis, okhdfcbank, okicici, oksbi, paytm, pthdfc, ptsbi, ptyes, ptaxis, upi, apl, yapl, axisbank, sbi, icici, hdfcbank, kotak, federal, rbl, idfcfirst, indus, freecharge, fam, waicici, wahdfcbank, wasbi, waaxis, jupiteraxis, naviaxis`. A UPI match with an unknown handle is kept with `handle_known = false` only if within 8 tokens of "UPI", "GPay", "PhonePe", "Paytm" or "scan".

URL `kind`: `form` for `forms.gle`, `docs.google.com/forms`, `forms.office.com`, `typeform.com`, `jotform.com`; `shortener` for `bit.ly`, `tinyurl.com`, `cutt.ly`, `rb.gy`, `t.ly`, `is.gd`; `payment` for `rzp.io`, `razorpay.me`, `paytm.me`, `upi://`, `instamojo.com`, `cashfree.com/...`; `messaging` for `wa.me`, `t.me`, `chat.whatsapp.com`, `telegram.me`; `document` for `drive.google.com`, `docs.google.com/document`.

Registrable domain: `tldextract.TLDExtract(suffix_list_urls=())` (bundled snapshot, no network), `registered_domain` field. Punycode decoded for display, encoded for comparison.

### 2.3 Organisation resolution

Run in order, stop at the first hit:

1. **Dictionary**: Aho-Corasick over names and aliases in `data/seeds/known_entities.json` (≈ 80 top recruiters and 6 government schemes). Longest match wins; ties broken by earliest position.
2. **Legal line**: a line matching `^(.{2,60}?)\s+(Private Limited|Pvt\.?\s?Ltd\.?|Limited|Ltd\.?|LLP|Technologies|Solutions|Services|Consultancy|Infotech|Softech|Inc\.?)\b` in the first 8 or last 12 lines.
3. **Pattern**: `(?:at|with|join(?:ing)?|from|welcome to|behalf of)\s+([A-Z][\w&.\-]*(?:\s+[A-Z][\w&.\-]*){0,4})`, case-sensitive, rejecting matches in a stop list (`Dear`, `Team`, `HR`, `India`, `Monday`...).
4. **Display name**: From header display name minus words `HR`, `Team`, `Careers`, `Recruitment`.
5. **LLM** (only if enabled): schema in `05-LLD.md` §6. Output must quote a substring that exists verbatim in the text, else rejected.

### 2.4 Government schemes

| `scheme_key` | Triggers | Official domains (verify at seed time) |
|--------------|----------|----------------------------------------|
| `pm_internship` | "PM Internship", "PMIS", "Prime Minister Internship" | `pminternship.mca.gov.in`, `mca.gov.in` |
| `aicte_internship` | "AICTE internship", "National Internship Portal" | `internship.aicte-india.org`, `aicte-india.org` |
| `msme_internship` | "MSME internship", "Ministry of MSME" | `msme.gov.in` |
| `skill_india` | "Skill India", "NSDC" | `skillindiadigital.gov.in`, `nsdcindia.org` |
| `niti_internship` | "NITI Aayog internship" | `niti.gov.in` |
| `digital_india` | "Digital India internship", "MeitY internship" | `meity.gov.in`, `digitalindia.gov.in` |

Any domain ending in `.gov.in` or `.nic.in` is accepted as government for any scheme.

### 2.5 Amount purpose and payer

Window = 12 tokens either side of the amount. First matching purpose wins in this order:

| Purpose | Keywords (lowercase, any) |
|---------|---------------------------|
| `stipend` | stipend, per month, /month, p.m., monthly |
| `salary` | salary, ctc, lpa, package, per annum |
| `verification` | background verification, bgv, police verification, police clearance, pcc, document verification, medical test, verification charges |
| `deposit` | security deposit, refundable, caution, deposit |
| `equipment` | laptop, device, joining kit, id card, uniform, kit |
| `training` | training fee, training charges, course fee, certification, lms, workshop fee |
| `registration` | registration, enrolment, enrollment, application fee, form fee, slot booking |
| `document` | offer letter charges, appointment letter, stamp paper, notary, agreement |
| `other_fee` | processing fee, onboarding fee, service charge, insurance, charges, fee |

Payer = `candidate` if purpose is not `stipend`/`salary` AND the window contains any of: pay, payment, deposit, transfer, send, submit, scan, upi, gpay, phonepe, paytm, jama, bhugtan, fee, charges. Otherwise `employer`.

### 2.6 Process phrases

- `no_interview`: "without interview", "no interview", "selected directly", "direct selection", "on the basis of your profile", "shortlisted from your resume", "liked your resume", "based on your resume"
- `chat_only_interview`: "interview on whatsapp", "interview on telegram", "chat interview", "text interview"
- `urgent`: deadline hours ≤ 48, or "limited seats", "last date today", "immediately", "urgent joining"

### 2.7 Confirmation

Extracted claims go to the student with each field editable. Fields with `source = pattern` or `llm` are highlighted "Please check". The student can mark any phone or email as "This is mine" (sets `role = recipient`, removed from probes, redacted). Once confirmed, claims are frozen for the run; that freeze is what makes the verdict deterministic.

## 3. Domain classification (used by P02, P06, P12)

```
classify(d, official_set) -> one of:
  official | official_subdomain | typosquat | combosquat | tld_swap | homoglyph | freemail | platform | unrelated
```

Let `L(d)` = registrable domain without suffix, lowercased, hyphens kept. For each `o` in `official_set`:

| Class | Rule | Example (claimed: Tech Mahindra, `o = techmahindra.com`) |
|-------|------|------------------------------------------------------------|
| `official` | `registrable(d) == o` | `techmahindra.com` |
| `official_subdomain` | `d` ends with `.` + `o` | `careers.techmahindra.com` |
| `homoglyph` | `d` has `xn--`, or `skeleton(L(d)) == L(o)` using Unicode confusables, or applying the swaps `rn→m, vv→w, 0→o, 1→l, 3→e, 5→s, l→i` (in that order) to both labels makes them equal | `techrnahindra.com` |
| `tld_swap` | `L(d) == L(o)` and suffix differs | `techmahindra.co.in`, `techmahindra.org` |
| `typosquat` | Damerau-Levenshtein(`L(d)`, `L(o)`) ≤ max(1, len(`L(o)`) // 8) | `techmahindara.com`, `tecmahindra.com` |
| `combosquat` | `L(o)` (hyphens removed) is a substring of `L(d)` (hyphens removed), and the leftover tokens are all in the lure list; or `L(o)` appears as a label of a non-official domain (`techmahindra.hr-portal.in`) | `techmahindra-careers.in`, `careers-techmahindra.com` |
| `freemail` | `registrable(d)` in `data/seeds/freemail.txt` | `gmail.com`, `rediffmail.com`, `outlook.com`, `yahoo.co.in`, `proton.me` |
| `platform` | Forms, shorteners, messaging, docs hosts from §2.2 | `forms.gle` |
| `unrelated` | none of the above | `hiringdesk-global.com` |

Lure tokens: `careers, career, jobs, job, hr, hiring, recruit, recruitment, talent, india, in, official, team, onboarding, offer, offers, intern, internship, global, group, corp, services, portal, apply, hire, placement, mail, info, support`.

Leftover-token check: remove `L(o)` once from `L(d)`, split the remainder on `-` and on boundaries of known lure words (greedy longest match). If every piece is a lure token or empty, it is a combosquat.

Damerau-Levenshtein from `rapidfuzz.distance.DamerauLevenshtein`.

## 4. Probes

Status values: `ok` (ran, produced findings or none), `skipped_no_input`, `skipped_no_official_domain`, `skipped_budget`, `skipped_replay_miss`, `skipped_no_public_url`, `skipped_forwarded`, `unsupported`, `timeout`, `error`.

Every finding has: `probe_id`, `code`, `family`, `weight` (positive = toward fraud), `decisive_flag` (optional), `message` (rendered copy), `receipt`.

### P01_ENTITY: who is the real employer? (Google Search, 1 to 2 calls)

Query Q1: `engine=google, q="{org}", gl=in, hl=en, num=10`.

Candidate scoring for each registrable domain `c` seen in `knowledge_graph.website` and `organic_results[*].link`:

```
score(c) = 3.0 * [c == registrable(knowledge_graph.website)]
         + sum over organic results r with registrable(r.link) == c of 1 / r.position
         + 2.0 * name_sim(c, org)

name_sim(c, org) = rapidfuzz.fuzz.partial_ratio(L(c).replace("-", ""), squash(org)) / 100
squash(org) = org lowercased, legal suffixes and spaces and punctuation removed
```

Domains in `data/seeds/aggregator_domains.txt` are excluded (`linkedin.com, naukri.com, glassdoor.co.in, glassdoor.com, ambitionbox.com, indeed.com, wikipedia.org, facebook.com, instagram.com, x.com, twitter.com, youtube.com, justdial.com, zaubacorp.com, tofler.in, crunchbase.com, internshala.com, foundit.in, quora.com, reddit.com`).

Accept `c` if (`c` is the knowledge graph website) or (`score(c) ≥ 2.0` and `name_sim ≥ 0.6`). Keep at most 3 accepted domains. Union with `known_entities.official_domains` if the org came from the dictionary.

If nothing accepted, run Q2: `q="{org}" careers` and repeat.

Also collect `official_contacts`: knowledge graph `phone`, any organic link whose path contains `/careers` or `/jobs` on an accepted domain.

| Code | Condition | Weight | Family |
|------|-----------|--------|--------|
| `P01_OFFICIAL_FOUND` | ≥ 1 accepted domain | 0.0 (enables P02, P04, P07, P08) | identity |
| `P01_NO_PRESENCE` | nothing accepted after Q2 | +1.0 | identity |

### P02_SENDER: is the sender the employer? (local, uses P01)

Inputs: `sender_email`, `reply_to`, every `url` whose kind is `other` or `document`.

| Code | Condition | Weight |
|------|-----------|--------|
| `P02_SENDER_OFFICIAL` | sender class `official` or `official_subdomain` | -1.0 |
| `P02_HOMOGLYPH` | any input domain `homoglyph` | +3.5 |
| `P02_TYPOSQUAT` | any input domain `typosquat` | +3.0 |
| `P02_COMBOSQUAT` | any input domain `combosquat` | +3.0 |
| `P02_TLD_SWAP` | any input domain `tld_swap` | +2.5 |
| `P02_FREEMAIL` | sender `freemail` and P01 found an official domain | +1.5 |
| `P02_FREEMAIL_NO_PRESENCE` | sender `freemail` and P01 found nothing | +0.8 |
| `P02_UNRELATED` | sender `unrelated` | +1.0 |
| `P02_REPLY_DIVERTED` | `reply_to` registrable differs from sender registrable and `reply_to` is `freemail` or `unrelated` | +2.0 |

Only the single largest of {HOMOGLYPH, TYPOSQUAT, COMBOSQUAT, TLD_SWAP} counts at full weight; others from that set count at 0.25x. `P02_SENDER_OFFICIAL` is weak (-1.0) because a pasted "From:" line is not authenticated; P03 supplies the strong negative.

### P03_HEADERS: is the email authenticated? (local, `.eml` only)

Parse every `Authentication-Results` header, take the topmost (added by the recipient's provider). Extract `dkim=<res> header.d=<d>`, `spf=<res> smtp.mailfrom=<m>`, `dmarc=<res> header.from=<f>`.

If Subject starts with `Fwd:`/`Fw:` or the From address is marked as the recipient's own, status `skipped_forwarded` and the UI says: "This looks forwarded. In Gmail open the original email, then More (⋮) > Download message, and upload that .eml file."

| Code | Condition | Weight |
|------|-----------|--------|
| `P03_DKIM_ALIGNED_OFFICIAL` | `dkim=pass`, `registrable(header.d)` in official set, and From registrable in official set | -3.0 |
| `P03_AUTH_FAIL` | `dmarc=fail`, or (`dkim` ∈ {fail, none} and `spf=fail`) | +2.0 |
| `P03_REPLY_DIVERTED` | header Reply-To registrable ≠ From registrable, Reply-To is `freemail` or `unrelated` | +2.0 (replaces `P02_REPLY_DIVERTED`, never both) |

### P04_FRAUD_NOTICE: has the employer warned about this? (Google Search, 1 call)

Query: `engine=google, q=(site:{o1} OR site:{o2}) (fraud OR fraudulent OR "fake job" OR "fake offer" OR scam OR "recruitment fraud")`, using up to 2 official domains.

A result is a **notice** if title + snippet match `(recruit|job|offer|hiring|employment).{0,40}(fraud|scam|fake)|(fraud|scam|fake).{0,40}(recruit|job|offer|hiring|employment)`.
A notice has a **no-fee statement** if the snippet matches `(never|not|do not|does not)\s+(ask|charge|collect|seek|request|demand).{0,40}(fee|money|payment|deposit|amount)`.

| Code | Condition | Weight |
|------|-----------|--------|
| `P04_NOTICE_FOUND` | ≥ 1 notice | +0.3 (the employer is a known impersonation target) |
| `P04_NOTICE_NO_FEE` | notice with no-fee statement | 0.0 by itself, enables `D1` |

Notices are also the best source of the official HR contact, shown in Next steps.

### P05_CHATTER: are people complaining about this? (Google, Google News, Google Forums, 3 calls)

| Call | Params |
|------|--------|
| A | `engine=google, q="{org}" (internship OR "offer letter" OR job) (scam OR fraud OR fake) -site:{o1}` |
| B | `engine=google_news, q="{org}" fake job offer, gl=in, hl=en` |
| C | `engine=google_forums, q={org} offer letter fee scam, gl=in` (optional, skipped quietly on error) |

A result counts as a **complaint** if title + snippet contain the org (fuzzy partial ≥ 85), a scam word (lexicon §9) and one of `job|intern|offer|placement|hiring`, and its date (if any) is within 24 months of the check.

| Code | Condition | Weight |
|------|-----------|--------|
| `P05_COMPLAINTS_GENERAL` | ≥ 3 complaints | +0.7 |
| `P05_COMPLAINT_NAMES_SENDER` | ≥ 1 complaint whose title, snippet or link contains the sender's non-official domain or the HR person's full name | +2.0 |
| `P05_PIB_FACTCHECK` | `scheme` claim and ≥ 1 result from `pib.gov.in` or with "PIB Fact Check" in title | +1.5 |

Big employers always have general complaints, which is why `P05_COMPLAINTS_GENERAL` is small.

### P06_IDENTIFIER_TRACE: has this UPI ID, phone or domain been reported? (Google 1 to 2 calls, plus local memory)

Identifiers: all `upi_id`, `phone` with role ≠ recipient (10-digit form), `sender_email` and `reply_to` if not official and not freemail, registrable domains classified `typosquat|combosquat|tld_swap|homoglyph|unrelated`.

Query: `engine=google, q="{id1}" OR "{id2}" OR "{id3}" OR "{id4}"` (max 4 per call, max 2 calls, priority: upi, phone, domain, email).

For each organic result, an identifier is **present** if its normalised form is in the normalised title + snippet + link (phones: digits only comparison). **Scam context** = title or snippet contains a scam word.

Local memory: look up the same identifiers in the `identifiers` table among earlier checks with tier `red`.

| Code | Condition | Weight |
|------|-----------|--------|
| `P06_ID_REPORTED` | identifier present with scam context; one finding per distinct source domain | +3.0 each, probe cap +4.0 |
| `P06_ID_ON_OFFICIAL` | phone or email present on a page of an official domain | -1.5 |
| `P06_ID_SEEN_LOCALLY` | identifier in ≥ 1 earlier red check | +2.0 (receipt links to the campaign) |

### P07_ROLE: does the role exist? (Google Jobs, 1 call)

Query: `engine=google_jobs, q={role} {org}, location={city or "India"}, gl=in, hl=en`.

Match rule for `jobs_results[i]`: `fuzz.token_set_ratio(company_name, org) ≥ 85` and `fuzz.token_set_ratio(title, role) ≥ 60`.

| Code | Condition | Weight | Family |
|------|-----------|--------|--------|
| `P07_ROLE_LISTED` | ≥ 1 match | -1.0 | existence |
| `P07_COMPANY_LISTS_OTHER_ROLES` | company matches but no title matches | +0.2 | existence |
| (none) | no listings at all | 0.0 (absence is not evidence) | |

### P08_OFFICE: is the office real? (Google Maps, 1 call)

Query: `engine=google_maps, type=search, q={address raw}` if an address was extracted, else `q={org} office {city}`; skip if neither address nor city.

Take `place_results` if present, else `local_results[0..2]`.

| Code | Condition | Weight | Family |
|------|-----------|--------|--------|
| `P08_OFFICE_MATCH` | place title fuzzy ≥ 80 with org, and (website registrable in official set or `type` contains Corporate office, Company, Software company, Consultant, Business management consultant, IT company) | -1.0 | existence |
| `P08_RESIDENTIAL` | address query resolves to a place whose `type`/`types` contain Apartment building, Housing society, Residential, Hostel, PG | +1.0 | existence |
| `P08_COWORKING` | type contains Coworking space, Business center, Virtual office | +0.5 | existence |
| `P08_NOT_FOUND` | address query returns no place | +0.5 | existence |
| `P08_REVIEWS_SCAM` | any review snippet on the matched place contains a scam word | +1.5 | reputation |

### P09_IMAGE: is the HR photo or letter reused? (Google Lens, 1 to 2 calls)

Calls: `hr_photo` with `engine=google_lens, type=exact_matches`; `offer_image` (letter) with `type=visual_matches` only if budget has ≥ 3 calls left after all other probes are reserved.

Stock domains (`data/seeds/stock_photo_domains.txt`): `shutterstock.com, istockphoto.com, gettyimages.com, gettyimages.in, freepik.com, pexels.com, unsplash.com, stock.adobe.com, dreamstime.com, 123rf.com, depositphotos.com, alamy.com, vecteezy.com, pngtree.com, pixabay.com`.

| Code | Condition | Weight |
|------|-----------|--------|
| `P09_STOCK_PHOTO` | `hr_photo` exact match on a stock domain | +3.0 |
| `P09_PHOTO_OTHER_NAMES` | exact matches on ≥ 3 distinct domains whose titles contain a capitalised two-word name with `fuzz.ratio < 70` to `hr_person.name` | +2.5 |
| `P09_PHOTO_OFFICIAL` | exact match on an official domain or `linkedin.com/in/` with title fuzzy ≥ 80 to `hr_person.name` | -1.0 |
| `P09_LETTER_REPORTED` | `offer_image` visual match whose title or source contains a scam word | +2.5 |

Family: artifact.

### P10_TEMPLATE: has this wording been seen in scams? (local MinHash + Google, 1 call)

Local: compute the template signature (§7). Query LSH over `templates` where `label = scam` (seed corpus plus earlier red checks).

Google: pick the distinctive sentence (§7.4) and search `engine=google, q="{sentence}"`.

| Code | Condition | Weight |
|------|-----------|--------|
| `P10_TEMPLATE_MATCH_HIGH` | estimated Jaccard ≥ 0.6 with a scam template | +3.0 |
| `P10_TEMPLATE_MATCH_MED` | 0.4 ≤ J < 0.6 | +1.5 |
| `P10_PHRASE_REPORTED` | quoted sentence returns ≥ 1 result with scam context | +2.0 |
| `P10_PHRASE_OFFICIAL` | quoted sentence returns a result on an official domain | -0.5 |

Family: artifact. If the normalised text has fewer than 30 tokens, local part is skipped.

### P11_POLICY: does the process break known rules? (local)

| Code | Condition | Weight |
|------|-----------|--------|
| `P11_CANDIDATE_PAYS` | ≥ 1 amount with `payer = candidate` | +2.5 |
| `P11_REFUNDABLE_BAIT` | that amount's purpose is `deposit` or window contains "refundable" | +0.5 |
| `P11_PERSONAL_UPI` | a `upi_id` claim exists, or a `payment` URL, or text mentions "scan the QR" | +1.0 |
| `P11_SCHEME_OFF_PORTAL` | `scheme` claim and sender or any application URL is not on that scheme's official domains or `.gov.in`/`.nic.in` | +3.0 |
| `P11_FORM_OR_SHORTLINK` | application via `form`, `shortener` or `messaging` URL | +0.7 |
| `P11_URGENCY` | `urgent` flag | +0.5 |
| `P11_NO_INTERVIEW` | `no_interview` flag | +1.0 |
| `P11_CHAT_INTERVIEW` | `chat_only_interview` flag | +0.7 |

Family: process. Receipt for `P11_CANDIDATE_PAYS` cites the AICTE no-fee rule and, if available, the employer's own no-fee notice from P04.

### P12_DOMAIN_AGE: how new is the domain? (RDAP, optional)

For each registrable domain classified `typosquat|combosquat|tld_swap|homoglyph|unrelated`: `GET https://rdap.org/domain/{d}`, read `events[eventAction="registration"].eventDate`. Age = `check.created_at - eventDate`.

| Code | Condition | Weight |
|------|-----------|--------|
| `P12_VERY_NEW` | age < 90 days | +1.5 |
| `P12_NEW` | 90 ≤ age < 365 days | +0.7 |

If RDAP has no service for the TLD, status `unsupported`. Family: identity.

## 5. Aggregation

### 5.1 Families and caps

| Family | Probes | Lower cap | Upper cap |
|--------|--------|-----------|-----------|
| `identity` | P01, P02, P03, P12 | -3.5 | +4.0 |
| `process` | P11 | 0.0 | +4.0 |
| `reputation` | P04, P05, P06, P08 `REVIEWS_SCAM` | -1.5 | +4.0 |
| `artifact` | P09, P10 | -1.5 | +4.0 |
| `existence` | P07, P08 (others) | -2.0 | +2.0 |

```
S_f = clamp( sum(w for findings in family f), lower_f, upper_f )
S   = sum(S_f for f in families)          # range [-8.5, +18.0]
```

Why caps: findings within a family are correlated (a combosquat domain is also likely new, and also likely unrelated). Capping per family stops one root cause from being counted three times, while independent families still add up.

The weights are log-odds-style (natural log scale, so +3.0 ≈ 20x more likely under fraud). They are set by hand from the reasoning in each table and fixed before the eval holdout is opened. Only thresholds in §6 may be tuned on the dev split (see `11-evaluation.md`).

### 5.2 Decisive rules (checked before thresholds)

| ID | Condition | Why it is decisive |
|----|-----------|---------------------|
| `D1_FEE_VS_NOTICE` | `P11_CANDIDATE_PAYS` and `P04_NOTICE_NO_FEE` | The employer itself states it never charges candidates |
| `D2_SCHEME_IMPERSONATION` | `P11_SCHEME_OFF_PORTAL` and (`P11_CANDIDATE_PAYS` or `P11_FORM_OR_SHORTLINK`) | Government schemes run only on official portals and do not charge |
| `D3_LOOKALIKE_PLUS_FEE` | any of `P02_HOMOGLYPH`, `P02_TYPOSQUAT`, `P02_COMBOSQUAT`, `P02_TLD_SWAP` and `P11_CANDIDATE_PAYS` | Fake identity plus a money ask |
| `D4_IDENTIFIER_REPORTED` | `P06_ID_REPORTED` from ≥ 2 distinct source domains | The same UPI, phone or domain is already publicly reported |

### 5.3 Coverage

Probe weights for coverage: P01 3, P02 2, P03 1, P04 2, P05 1, P06 2, P07 1, P08 1, P09 1.5, P10 1, P11 2, P12 0.5.

A probe is **applicable** unless its status is `skipped_no_input` or `unsupported`, or (P03 with no `.eml`). A probe is **covered** if status is `ok`.

```
coverage = sum(weight of covered probes) / sum(weight of applicable probes)
```

## 6. Verdict rules

Evaluate in order, first match wins:

```
1. if any decisive rule fired:                    tier = red
2. if coverage < 0.40 and S < 3.0:                tier = grey
3. if S >= 3.0:                                   tier = red
4. if S <= -2.0
      and not P11_CANDIDATE_PAYS
      and no identity finding with weight >= +2.5
      and green_anchor:                           tier = green
5. otherwise:                                     tier = amber

green_anchor = P03_DKIM_ALIGNED_OFFICIAL
            or (P02_SENDER_OFFICIAL and (P07_ROLE_LISTED or P08_OFFICE_MATCH or P09_PHOTO_OFFICIAL))
```

Red subtype (changes the headline only):

```
red_kind = "impersonation" if (D1 or D2 or D3 or D4 fired) or S_identity >= 2.5 or S_artifact >= 2.5
           else "fee_risk"
```

Evidence strength bar shown to the user: `clamp((S + 8.5) / 26.5, 0, 1)`, labelled "Evidence leans genuine ← → Evidence leans fraudulent". We do not show a probability.

### 6.1 Worked example (golden case G1)

Offer: WhatsApp text plus PDF. "Tech Mahindra", sender `hr.onboarding@techmahindra-careers.in` (constructed demo domain), ₹2,000 "police clearance certificate" to `techm.hr@ybl`, "complete within 24 hours", no interview.

| Finding | Family | Weight |
|---------|--------|--------|
| P01_OFFICIAL_FOUND (`techmahindra.com`) | identity | 0.0 |
| P02_COMBOSQUAT (`techmahindra-careers.in`) | identity | +3.0 |
| P04_NOTICE_FOUND + P04_NOTICE_NO_FEE | reputation | +0.3 |
| P05_COMPLAINTS_GENERAL | reputation | +0.7 |
| P11_CANDIDATE_PAYS | process | +2.5 |
| P11_PERSONAL_UPI | process | +1.0 |
| P11_URGENCY | process | +0.5 |
| P11_NO_INTERVIEW | process | +1.0 |

`S_identity = 3.0`; `S_process = clamp(5.0, 0, 4.0) = 4.0`; `S_reputation = 1.0`. `S = 8.0`. (P12 adds nothing here: the constructed demo domain is unregistered, so RDAP returns no registration date.) Decisive: `D1` and `D3`. Tier `red`, kind `impersonation`.

Top 3 reasons (decisive first, then by |contribution|):
1. "Tech Mahindra's own recruitment fraud notice says it never charges candidates. This offer asks for ₹2,000." (D1, receipt: P04 result)
2. "The sender domain techmahindra-careers.in is not Tech Mahindra's. Tech Mahindra uses techmahindra.com." (D3 / P02, receipt: P01 knowledge graph)
3. "You are asked to pay a personal UPI ID (te****@ybl) within 24 hours." (P11)

## 7. Template fingerprinting

### 7.1 Normalisation

1. Lowercase, Unicode NFKC.
2. Replace with placeholders, in this order: emails `<email>`, URLs `<url>`, UPI `<upi>`, phones `<phone>`, amounts `<amt>`, dates `<date>`, the org name and aliases `<org>`, `hr_person.name` `<per>`, recipient `<recipient>`, remaining digits `<num>`.
3. Remove punctuation except placeholders, collapse whitespace, split on spaces.

### 7.2 Signature

```
shingles = { " ".join(tokens[i:i+5]) for i in range(len(tokens) - 4) }
x(s)     = int.from_bytes(blake2b(s.encode(), digest_size=8).digest(), "big")
P        = 2**61 - 1
rng      = random.Random(26)                      # fixed seed, part of ruleset
A, B     = [rng.randrange(1, P) for _ in range(128)], [rng.randrange(0, P) for _ in range(128)]
sig[i]   = min( (A[i] * x(s) + B[i]) % P for s in shingles )
```

### 7.3 LSH

32 bands x 4 rows. Band key = `blake2b(band_index || sig[4b:4b+4], digest_size=8)`. Candidates are templates sharing ≥ 1 band key. Estimated Jaccard = `mean(sig_a[i] == sig_b[i])`. The 50% detection point of this banding is `(1/32)^(1/4) ≈ 0.42`, which matches the 0.4 lower threshold in P10.

### 7.4 Distinctive sentence for P10

Split the original text into sentences. Keep sentences with 8 to 25 tokens and at most 1 placeholder after normalisation. Score each by mean rarity `7 - wordfreq.zipf_frequency(w, "en")` over non-placeholder tokens. Take the highest; trim to 20 words; send quoted. Sentences containing the recipient's name are never sent.

### 7.5 Seed corpus

`data/seeds/scam_templates/*.txt`: at least 25 public scam texts transcribed from news reports, employer notices and PIB fact-checks (source URL in the first line as `# source: ...`), plus every check that ends `red` (stored as signature only, not text).

## 8. Campaign clustering

After a verdict of `red` or `amber`, link the check to earlier `red`/`amber` checks with union-find. Edges:

| Edge type | Condition |
|-----------|-----------|
| `upi` | same normalised VPA |
| `phone` | same 10-digit number, role ≠ recipient, not on an official page |
| `domain` | same registrable domain classified non-official, non-freemail, non-platform |
| `email` | same non-official sender or reply-to address |
| `image` | 64-bit pHash Hamming distance ≤ 6 on `hr_photo` or `offer_image` |
| `template` | estimated Jaccard ≥ 0.6 |

Campaign ID = the lowest `campaign_id` among merged sets (stable). A campaign records: member count, distinct claimed orgs, first and last seen, edge-type counts, tier distribution. The campaign view is what makes Special26 useful to a placement officer: "these 14 offers impersonating 5 different companies all pay the same UPI ID".

## 9. Lexicons

Scam words: `scam, scammer, fraud, fraudulent, fake, cheated, cheat, duped, beware, warning, alert, complaint, lost money, extortion, fact check, phishing, not affiliated, do not pay, impersonat`.

All lexicons live in `data/seeds/lexicons.yaml` and are part of the ruleset version.

## 10. Where an LLM is allowed

| Step | LLM allowed? | Guard |
|------|--------------|-------|
| Claim extraction fallback | Yes, optional | JSON schema, verbatim-substring check, student confirms |
| Probe logic, weights, verdict | No | |
| Reason copy | No, template strings per finding code | |
