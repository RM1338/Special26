# 02. Product Requirements Document: Special26

## 1. Problem statement

A student holds an offer that claims to come from a real employer or government scheme. They need to decide within hours whether to pay, reply, or ignore. Today they have no tool that checks *this specific offer's* claims against the employer's real domains, real offices, real job listings, published fraud notices and existing scam reports.

## 2. Goal

Give a student a verdict on a specific offer in under 30 seconds, backed by receipts they can click, plus the exact next action (official contact to confirm through, and where to report).

## 3. Non-goals

- Not a job board, not a resume tool, not a general phishing filter.
- Not a legal determination. We report evidence of impersonation; we do not accuse.
- Not a model trained to classify job post text. Text style is a weak signal; claims are the strong signal.
- Not monitoring a student's inbox. The student brings the offer to us.

## 4. Users and jobs to be done

| User | Situation | Job to be done | What they need from us |
|------|-----------|----------------|------------------------|
| Priya, 3rd-year B.Tech, Coimbatore | WhatsApp message: "Selected for Data Analyst Intern at Tech Mahindra, ₹15,000/month, pay ₹2,000 for police verification in 24 hours" | "Tell me if I should pay" | A clear red/amber/green answer, why, and the real Tech Mahindra careers contact |
| Arjun, final-year BCA, Indore | Email offer letter PDF from a startup he applied to on a job board, no fee asked | "Is this company real before I give my Aadhaar and bank details?" | Evidence the company and office exist, and the role is listed |
| Mrs. Sharma, parent | Daughter forwarded a "PM Internship Scheme" Google Form with ₹499 registration | "Is this government scheme real?" | Official portal link and a plain statement that the scheme does not run on Google Forms |
| Placement officer, tier-2 college | 40 students forwarded similar offers this week | "Which of these are the same scam?" | Campaign view: all checks sharing a UPI ID or template, with counts |

## 5. Core user story

> As a student who received an offer, I paste or upload it, confirm the details Special26 pulled out, and within 30 seconds see a verdict card that lists each claim, what the web says about it, and what I should do next.

## 6. Features (MVP)

| ID | Feature | Detail |
|----|---------|--------|
| F1 | Offer intake | Paste text, upload PDF, upload screenshot (OCR), upload `.eml`, optional HR profile photo. Max 4 files, 5 MB each |
| F2 | Claim extraction and confirmation | Pull out company, sender email and domain, Reply-To, URLs, phones, UPI IDs, amounts with purpose, HR name, address, role, stipend, deadlines. Student can edit before the run |
| F3 | Live probes | 12 probes (`P01` to `P12`, see `08-algorithm.md`), 6 SerpApi engines, progress streamed live |
| F4 | Verdict card | Tier (red, amber, green, grey), headline, top 3 reasons, evidence strength bar, coverage meter |
| F5 | Evidence receipts | Every finding opens the exact SerpApi result (engine, query, link, snippet) or is labelled "rule" |
| F6 | Next steps panel | Official careers contact from the employer's own site; report links: cybercrime.gov.in, helpline 1930, Sanchar Saathi Chakshu |
| F7 | Share link | Redacted read-only verdict page to send to parents or the placement cell; scammer identifiers masked |
| F8 | Campaign detection | Links this check to earlier checks sharing a UPI ID, phone, domain, image or template |
| F9 | Replay mode | All demo and eval runs work offline from recorded SerpApi responses |

Stretch (only after MVP is frozen): TPO bulk view, Telegram bot intake, browser extension for Gmail. See `12-mvp-scope.md`.

## 7. What makes the answer trustworthy

1. **Receipts, not opinions.** No finding without a source link or an explicit rule label.
2. **Asymmetric caution.** Green requires positive proof from at least two independent sources and no fee ask. Lack of evidence gives amber or grey, never green.
3. **Deterministic core.** Given the same confirmed claims and the same SerpApi responses, the verdict is identical. LLM use is limited to optional claim extraction, which the student confirms.
4. **Employer's own words first.** If the employer's own fraud notice contradicts the offer, that outweighs everything else.

## 8. Success metrics

### Product metrics (measured in eval, see `11-evaluation.md`)

| Metric | Target |
|--------|--------|
| Red precision (of red verdicts, share that are truly fraudulent) | ≥ 0.95 |
| Fraud catch rate (fraud cases given red or amber) | ≥ 0.90 |
| Genuine offers wrongly given red | ≤ 5% |
| Green precision | ≥ 0.90 |
| p50 time to verdict, live | ≤ 25 s |
| p50 time to verdict, replay | ≤ 2 s |
| Mean SerpApi calls per check | ≤ 12 (hard cap 14) |

### Demo metrics

- All 6 golden cases in `14-demo-plan.md` produce the expected tier in replay mode, every run.
- Each verdict card in the video shows at least one receipt from Lens, Maps or Jobs, not only Google Search.

## 9. Copy principles

- Headlines by tier (exact strings in `09-user-flow.md`):
  - red: "Strong signs of impersonation. Do not pay."
  - amber: "Could not verify this offer. Confirm through the official channel before you share documents or pay."
  - green: "Consistent with a genuine offer from {company}. Still confirm through {official_contact}."
  - grey: "Not enough information to judge. Add the sender email or the full offer text."
- Never the words "scam", "fraudster", "safe" or "guaranteed" in verdict headlines.
- Hindi translation of the verdict headline and next steps is a stretch goal.

## 10. Constraints

- Build window: 5 Oct to 10 Oct 2026. Submit by 10 Oct 18:00 IST; 18:00 to 23:59 is buffer for video or link fixes only.
- SerpApi credits are finite: cache-first, budget per check, replay for demo and eval.
- No paid third-party data sources besides SerpApi. RDAP for domain age is free and optional.
- Must run as one Docker container for judges.

## 11. Open questions (with default answers so work is not blocked)

| Question | Default until decided |
|----------|------------------------|
| Do we store raw offer text? | No. Store redacted text only; raw text discarded when the check finishes |
| Do campaign pages show scammer phone numbers in full? | No. Last 4 digits only on any public page |
| LLM provider for extraction fallback | `none` by default; `anthropic` or `openai` via env |
| OCR | Tesseract in the Docker image; if missing, ask the student to paste text |
