# 10. Novelty and Competitive Analysis

## 1. The question judges will ask

"Fake job detection" returns many GitHub projects. Why is this not one more?

Short answer: almost all of them classify **job postings by their text**. Special26 verifies **an offer sent to one person** by checking each of its **claims against the outside world**, and links offers that share infrastructure into **campaigns across impersonated brands**. Different input, different method, different output.

## 2. Landscape

| Tool | What it does | Input | Method | India specific | Receipts | Gap Special26 fills |
|------|--------------|-------|--------|----------------|----------|---------------------|
| **JobVerify** ([GitHub](https://github.com/yessGlory17/job-verify), MCP server) | Company registration, domain age, lookalike domains, email and phone checks, crypto wallet check, Internet Archive age, scam patterns | Company name, URL, email | API lookups exposed to an AI assistant | No | Partial (tool output to an LLM) | No Google Lens, Maps or Jobs; no employer fraud-notice contradiction; no Indian schemes, UPI or Indian phone logic; no campaign clustering; verdict depends on the LLM that calls it |
| **Text-ML fake job detectors** (dozens of EMSCAD Kaggle notebooks; e.g. [fake-job-detector](https://fake-job-detector-np6q.onrender.com/)) | Classify a job posting as fake or real | Posting text | TF-IDF or BERT on EMSCAD (~17,880 postings, mostly US, 2012-2014) | No | No | Impersonation offers copy real templates, so text looks genuine; the model cannot see that the sender domain is wrong |
| **GhostJob** ([extension](https://chromeboard.com/extension/ghostjob-ghost-job-detect-clbbopifmidceplphamfdfapgacgbhnd)), [Ghost Job Detector](https://ghostjobdetector.onrender.com/) | Flags stale or never-filled postings on job boards | Job board pages | Posting age and repost heuristics | No | No | Different problem: "ghost jobs" waste time, impersonation offers steal money |
| **Employer fraud notices** (e.g. [Tech Mahindra](https://careers.techmahindra.com/CPDOC/Recruitment_Fraud.pdf)) | Lists official domains, says no fees | none | Static PDF | Yes | n/a | Student must know the notice exists and compare manually. Special26 finds it automatically and cites it against the offer (`D1`) |
| **PIB Fact Check / news** | Debunks specific viral fakes | none | Manual journalism | Yes | Yes | Reactive, one template at a time, days later. Special26 uses these as evidence (`P05_PIB_FACTCHECK`) |
| **General chat assistants** ("is this a scam?") | Opinion on pasted text | Text | LLM reasoning without lookups, or with ad-hoc browsing | No | Rarely | No systematic checks; not deterministic; cannot run Lens on the HR photo or Maps on the address; no memory across students |
| **Website trust scorers** | Score a website's trustworthiness | URL | Domain signals | No | Partial | Score a site, not an offer; do not know which company the offer claims to be from, so cannot detect impersonation of that company |

## 3. What is new in Special26

| # | Contribution | Why it matters | Where |
|---|--------------|----------------|-------|
| 1 | **Claim-level verification**: the offer is decomposed into typed claims, each checked by the engine that can confirm or refute it | Impersonation is a mismatch between claims and reality, not a writing style | `08` §2, §4 |
| 2 | **Employer's own words as decisive evidence**: search the claimed employer's own domain for its fraud notice and contradict a fee ask with it (`D1_FEE_VS_NOTICE`) | The strongest possible evidence, and it is already public | `P04` |
| 3 | **Brand-aware lookalike detection** that knows which brand is claimed: typosquat, combosquat with an explicit lure-token grammar, TLD swap, homoglyph, subdomain abuse, with guardrails for real sister domains (`tcsion.com`) | Generic lookalike checkers need a reference brand; we get it from the claim and P01 | `08` §3 |
| 4 | **Image provenance of the HR persona** through Google Lens exact matches on stock and unrelated-name pages | Fake HR personas reuse stock or stolen photos; text tools cannot see this | `P09` |
| 5 | **Physical and role reality** via Google Maps and Google Jobs, with absence treated as non-evidence | Avoids penalising small genuine startups while rewarding confirmed offices and listings | `P07`, `P08` |
| 6 | **India-specific rules**: UPI VPA extraction with handle list, +91 phone normalisation, government scheme portal check (`.gov.in`, `.nic.in`), AICTE no-fee rule, Sanchar Saathi and 1930 next steps | The scams are Indian in mechanics: UPI, WhatsApp, schemes | `08` §2.2, §2.4, `P11` |
| 7 | **Cross-brand campaign clustering**: union-find over UPI, phone, domain, image pHash and MinHash template edges | One scam operation impersonates many brands. Linking them is what a placement officer needs, and no existing tool does it | `08` §7, §8 |
| 8 | **Asymmetric, auditable verdict**: capped log-odds families, decisive rules, a green gate that requires positive anchors, coverage meter, receipts for every reason | Students can trust it; judges can audit it | `08` §5, §6 |

## 4. What is not new (be honest in the README)

- Individual signals (domain age, free-mail sender, fee ask) are known and appear in JobVerify and awareness articles. The contribution is combining them with claim-specific web evidence and campaign linking, not inventing each signal.
- MinHash and union-find are textbook. Using them to cluster offers that impersonate *different* brands through shared payment rails is the applied idea.

## 5. Why SerpApi specifically

| Need | Without SerpApi |
|------|-----------------|
| Knowledge graph website for an arbitrary Indian company name | Scrape Google (blocked, against terms) or maintain a company database (impossible in 5 days) |
| Employer fraud notice on its own domain | Crawl every employer's site |
| Google Jobs listing for the role | No public Google Jobs API |
| Maps place type for an address | Google Places API (separate billing, different terms) |
| Lens exact matches for a photo | No public Lens API |
| Forums and News complaints | Separate news APIs, no forum search |

One key, one client, six engines, consistent JSON. That is the honest case for "meaningful SerpApi usage".

## 6. Defensibility after the hackathon

- **Campaign memory compounds**: every red check adds identifiers and templates that make the next check faster and more certain (`P06_ID_SEEN_LOCALLY`, `P10` local corpus).
- **Distribution through placement cells**: one TPO sharing the campaign page reaches hundreds of students.
- **Employer side**: companies already publish fraud notices; a verified-domain feed from employers would turn `P01` into an authoritative registry.
