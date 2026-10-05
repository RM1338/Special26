# 12. MVP Scope

MVP = what must be working, deployed and in the video by **9 Oct 2026, 12:00 IST** (feature freeze).

## 1. In scope (MVP)

| Area | In MVP | Detail |
|------|--------|--------|
| Intake | Text paste, PDF text, `.eml`, HR photo, offer screenshot | OCR only if Tesseract is in the image; otherwise paste text |
| Claims | All claim types in `08` §2.1 by regex and dictionary | LLM fallback off by default |
| Claim editor | Yes | Edit, delete, add, "This is mine", org required |
| Probes | P01, P02, P03, P04, P05 (Google + News; Forums if it works), P06 (web + local memory), P07, P08, P09 (HR photo exact matches), P10 (local MinHash + phrase search), P11 | 6 SerpApi engines live |
| Scoring | Full: families, caps, D1 to D4, tiers, red_kind, reasons, coverage | |
| UI | Home, Confirm, Live timeline, Verdict card, Receipt drawer, Next steps | Mobile layout |
| Share | Share token + masked share page + WhatsApp preview tags | |
| Campaigns | Union-find on UPI, phone, domain, email, template; campaign page (simple) | pHash edge if time |
| Replay | `demo.db` with the 6 golden cases; replay banner | |
| Eval | ≥ 60 cases, S26 + B0 + B3 + 3 ablations, report.md | B1, B2 if time |
| Deploy | Docker on Render/Railway, public URL, replay fallback image | |
| Seeds | ≥ 40 known entities, 6 schemes, ≥ 25 scam templates | 80 entities is the target |

## 2. Out of scope (do not start)

- User accounts, login, history across devices.
- Inbox integration (Gmail API), WhatsApp or Telegram bots.
- Browser extension.
- Hindi or other language UI (copy keys are structured so this is easy later).
- MCA company registry or GSTIN live lookup (format validation only).
- Any machine-learned classifier inside the verdict.
- Payment of any kind, employer dashboards.

## 3. Stretch (only after freeze criteria are met, in this order)

1. `P12_DOMAIN_AGE` via RDAP.
2. `P09` letter image visual matches.
3. pHash image edge in campaigns.
4. B1 (EMSCAD TF-IDF) and B2 (LLM only) baselines in the eval report.
5. LLM extraction fallback.
6. TPO bulk view: upload a ZIP of up to 20 offers, get a table and the campaigns among them.
7. Hindi verdict headline and next steps.

## 4. Cut order if behind schedule

Cut from the bottom first. Never cut the top 5.

| Rank | Item | Never cut? |
|------|------|------------|
| 1 | P01 + P02 + P11 + scoring + verdict card with receipts | yes |
| 2 | P04 fraud notice and D1 | yes |
| 3 | Replay mode with golden cases | yes |
| 4 | P09 Lens on HR photo | yes (the most visual SerpApi moment in the demo) |
| 5 | P08 Maps and P07 Jobs | yes (green anchors) |
| 6 | Share page | |
| 7 | P10 template (local + phrase) | |
| 8 | P06 identifier trace | |
| 9 | Campaign page | |
| 10 | P05 chatter | |
| 11 | P03 headers | |
| 12 | Eval beyond 40 cases | |

## 5. Definition of done for MVP

- [ ] All 6 golden cases return the expected tier, red_kind, decisive set and first reason in replay, in CI.
- [ ] One live check end to end on the deployed URL in ≤ 45 s.
- [ ] Every reason on every golden verdict opens a receipt with a working link.
- [ ] Share page renders on a 360 px phone and shows a WhatsApp preview.
- [ ] `eval/report.md` exists with S26 vs B0 vs B3 and at least 3 ablations on ≥ 60 cases.
- [ ] README has: problem with sources, one GIF, how to run (live and replay), SerpApi engine table, eval table, limitations.
- [ ] No em dashes in UI copy or README (`grep -rnP '\x{2014}' frontend/src README.md` returns nothing).
