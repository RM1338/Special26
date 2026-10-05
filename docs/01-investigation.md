# 01. Investigation: fake internship and job offers aimed at Indian students

## 1. The problem in one paragraph

Every placement season, students in India get WhatsApp messages, Telegram DMs, emails and "offer letter" PDFs that say they have been selected for an internship or a fresher job at a real, well known organisation. The offer looks right: the logo is correct, the letterhead is copied from a real template, the HR person has a LinkedIn-style photo. Then comes the ask: ₹499 registration, ₹2,000 for a "police clearance certificate", ₹3,500 for a "training kit", a "refundable" laptop deposit. Students pay because the amount is small relative to the stipend promised, the deadline is a few hours away, and they have no fast way to check. Placement cells warn about this every year, but the warning is generic ("never pay a fee"), and the student is holding a specific offer that looks real.

## 2. Evidence that the pain is real and current

| Date | Where | What happened | Source |
|------|-------|---------------|--------|
| 2026 | Chennai | Students offered a ₹15,000 per month stipend, then told to pay ₹2,000 over UPI for a "police clearance certificate" | [Dinamalar Kalvimalar](https://www.dinamalar.com/news/kalvimalar-news-en/fraudsters-target-college-students-with-fake-internship-offers-warn-cyber-experts/57787) |
| Mar 2026 | National | LinkedIn research reported that 49% of Indian Gen Z job seekers nearly fell for a job scam | [Saarthi](https://joinsaarthi.com/blogs/how-to-find-paid-internship-india-2026-avoid-fake-listings) |
| 22 Sep 2026 | National | Ministry of Home Affairs flagged a surge in internship scams; the AICTE National Internship Portal terms were updated on 15 Sep 2026 to state that no fees may be charged | [CareerIndia](https://www.careerindia.com/features/internship-scams-2026-how-to-spot-fake-job-offers-and-avoid-paying-fees-011-66049.html) |
| 12 Jul 2026 | National | PIB Fact Check called out a fake "MSME internship" Google Form circulating among students | [NewsX](https://www.newsx.com/india/fact-check-did-the-government-really-release-internship-forms-for-students-heres-the-truth-247978/) |
| 2026 | Jabalpur | 45 students allegedly cheated in a fake placement scheme, about ₹6,000 each | [Free Press Journal](https://www.freepressjournal.in/bhopal/45-jabalpur-students-allegedly-cheated-in-fake-job-placement-scam-extorted-of-6k-each-in-delhi-video) |
| 2026 | Indore | A student lost ₹44,000 to a fake job offer | [Outlook Money](https://www.outlookmoney.com/news/student-duped-of-rs-44000-in-fake-job-offer-scam-how-to-stay-safe) |
| 2026 | Hyderabad | Fake internship scheme targeting college students | [Deccan Chronicle](https://deccanchronicle.com/southern-states/telangana/fake-internship-scam-loots-college-students-1830107) |
| Ongoing | Employer side | Tech Mahindra publishes standing recruitment fraud warnings, says it never charges candidates, and lists its official domains | [Tech Mahindra notice](https://careers.techmahindra.com/CPDOC/Recruitment_Fraud.pdf) |
| Ongoing | Lookalike domains | `careers-github.com` style combosquats that put a real brand next to a lure word | [MalwareTips scan](https://tools.malwaretips.com/url-scan/careers-github.com) |
| Ongoing | Awareness | Practitioner guide to spotting fake offers | [Akancha Srivastava Foundation](https://akanchasrivastava.org/that-job-offer-is-not-real/) |

Two observations drive the design:

1. **The scam is impersonation, not bad writing.** Scammers copy real templates. A text classifier trained on "fraudulent job post" language learns spelling mistakes and too-good salaries. It cannot tell that `hr@techmahindra-careers.in` is not Tech Mahindra. You need to check the claims against the outside world.
2. **The employer already published the truth.** Tech Mahindra, TCS, Infosys and others post fraud notices listing their real domains and stating they never charge fees. Government schemes run only on `.gov.in` or `.nic.in` portals. That truth is on the web, scattered across search results, Maps listings, job boards and forum threads. Nobody puts it next to the offer the student is holding. SerpApi makes that possible in one request fan-out.

## 3. Who has this problem and how many

- **Primary user**: Indian college students and fresh graduates looking for internships and first jobs. India's higher education enrolment is about 4.33 crore (AISHE 2021-22, Ministry of Education). Every one of them is a target during placement and internship season, every year.
- **Secondary users**: parents who are asked to pay, and college Training and Placement Officers (TPOs) who field "is this real?" questions from hundreds of students.
- **Why the market is not niche**: the PM Internship Scheme alone set a target of internships for 1 crore young people across top companies over five years. Every new legitimate scheme creates a new impersonation template within weeks (see the PIB MSME form case above).
- **Frequency**: recurring. A student may receive several unsolicited "offers" during one season. Each one is a separate check.

## 4. What students do today, and why it fails

| Current method | Why it fails |
|----------------|--------------|
| Ask a friend or senior | Slow, and they also cannot verify a domain or photo |
| Google the company name | Shows the real company, which makes the fake offer look more legitimate |
| Read generic "how to spot fake jobs" articles | Lists red flags, does not tell you whether *this* offer has them |
| Ask ChatGPT "is this a scam?" | No live lookup of the sender domain, office address, photo reuse or employer notice; produces a confident opinion without receipts |
| Text-based fake job detectors | Trained on job *postings* (EMSCAD), not on impersonated offers sent to individuals |
| Call the number in the offer | Reaches the scammer |

## 5. Why SerpApi is essential (not decorative)

Each claim in an offer maps to a SerpApi engine that can confirm or contradict it. Without these engines the product has nothing to compare the offer against.

| Claim in the offer | What we need to know | SerpApi engine | Probe |
|--------------------|----------------------|----------------|-------|
| "We are Tech Mahindra" | What domains does the real company use? | Google Search (`engine=google`, knowledge graph + organic) | `P01_ENTITY` |
| Employer policy | Has the employer published a recruitment fraud notice saying it never charges fees? | Google Search with `site:` the official domain | `P04_FRAUD_NOTICE` |
| Reputation of this offer | Are students complaining about this company plus "offer letter fee"? | Google Search, Google News, Google Forums | `P05_CHATTER` |
| Specific identifiers | Has this UPI ID, phone or domain already been reported? | Google Search (exact match queries) | `P06_IDENTIFIER_TRACE` |
| "Data Analyst Intern" role | Does the company list such a role publicly? | Google Jobs | `P07_ROLE` |
| Office address | Is it a real company office, or a house, a coworking desk, or nothing? | Google Maps | `P08_OFFICE` |
| HR photo and letterhead | Is this a stock photo or someone else's profile picture? Has this letter image appeared in scam reports? | Google Lens (`exact_matches`, `visual_matches`) | `P09_IMAGE` |
| The letter text itself | Has this exact wording been posted as a scam elsewhere? | Google Search (quoted distinctive sentence) | `P10_TEMPLATE` |

Six SerpApi engines carry the evidence. Local logic (domain similarity, email authentication headers, fee detection) interprets it, but local logic alone cannot produce a verdict for most offers.

## 6. Hackathon fit

The hackathon judges, unweighted: idea strength, originality, technical complexity, usefulness, and meaningful SerpApi usage. Submission requires a website entry, a public GitHub repository and a public demo video under three minutes.

| Criterion | How Special26 answers it |
|-----------|--------------------------|
| Idea strength | Real, recurring, money-losing pain for crores of students, with 2026 news evidence |
| Originality | Claim-by-claim verification against live web evidence plus cross-offer campaign detection. Closest open-source tool (JobVerify) has no Lens, Maps, Jobs, India context or campaign view; see `10-novelty.md` |
| Technical complexity | Claim extraction, lookalike domain detection (typosquat, combosquat, TLD swap, homoglyph), email authentication parsing, log-likelihood evidence aggregation with family caps and decisive rules, MinHash template fingerprinting, union-find campaign clustering |
| Usefulness | Answers a specific question in 30 seconds, tells the student exactly what to do next (official careers contact, cybercrime.gov.in, 1930, Sanchar Saathi Chakshu) |
| SerpApi usage | Six engines, each tied to a specific claim, with receipts shown in the UI |

## 7. Risks found during investigation

| Risk | Mitigation |
|------|-----------|
| Large companies always have some scam chatter, so `P05_CHATTER` could flag genuine offers | `P05` weight is low and capped; it only becomes strong when the chatter names the exact sender domain or HR name |
| Small startups have little web presence, so a genuine offer can look unverified | Verdict for such offers is `amber` ("Unverified"), never `red`, unless a fee or lookalike is present |
| Google Forums API uptime is around 83% | `P05` degrades gracefully: missing forum results reduce coverage, they do not fail the check |
| Google Lens needs a public image URL | Serve uploaded images from a short-lived signed URL on our backend, or use SerpApi's image upload flow; see `05-LLD.md` |
| Credits | Default budget 14 SerpApi calls per check, cache-first client, replay mode for demos and eval |
| Defaming a real person or company | Scammer identifiers are masked on public share pages; copy never says "scam", it says "signs of impersonation" with receipts |
