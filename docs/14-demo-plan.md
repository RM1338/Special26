# 14. Demo Plan

Video limit: under 3 minutes. Target 2:50. Recorded in **replay mode** from `demo.db` so it is identical on every take; the replay banner stays visible and the voiceover says once that results were recorded live on 9 Oct.

## 1. What the video must prove (mapped to judging)

| Judging criterion | Shot that proves it |
|-------------------|---------------------|
| Idea strength | 0:00 hook with a real 2026 news headline and the ₹2,000 "police clearance" pattern |
| Originality | Employer's own fraud notice contradicting the offer (D1); campaign across two brands |
| Technical complexity | Live timeline of 11 probes; lookalike classification; family-capped scoring shown in the findings panel |
| Usefulness | Next steps with the official careers link and 1930; share to WhatsApp |
| SerpApi usage | Receipts from 6 engines on screen: Google, News, Jobs, Maps, Lens, Forums |

## 2. Script

| Time | Screen | Voiceover (approx.) |
|------|--------|---------------------|
| 0:00 to 0:15 | Phone screenshot of a WhatsApp offer (G1), then a news headline (Dinamalar, Chennai students, ₹2,000 police clearance) | "Students in India are getting offers like this every week. Real company name, real logo, and a small fee. Most pay because they can't check." |
| 0:15 to 0:28 | Special26 home on a phone frame | "Special26 checks the offer itself. Not whether it sounds fake, but whether each claim in it is true." |
| 0:28 to 0:45 | Paste G1, Confirm screen: org, sender domain, ₹2,000 verification, UPI. Tap "This is mine" on the student's number | "It pulls out the claims: who it says it's from, who sent it, how much, and where the money goes." |
| 0:45 to 1:00 | Timeline running, engine badges lighting up | "Then it checks each one: Google for Tech Mahindra's real domain and its own fraud notice, News and Forums for complaints, Jobs for the role, Maps for the office, Lens for the HR photo." |
| 1:00 to 1:20 | Red verdict; tap reason 1 → receipt drawer showing Tech Mahindra's notice; tap reason 2 → `techmahindra-careers.in` vs `techmahindra.com` | "Strong signs of impersonation. Tech Mahindra's own notice says it never charges candidates, and the sender domain isn't theirs. Every reason links to its source." |
| 1:20 to 1:35 | G5: HR photo; P09 receipt showing the same face on a stock photo site | "This 'HR manager' is a stock photo. Google Lens finds it on a stock site. No text classifier can see that." |
| 1:35 to 1:52 | G3: green verdict; receipts: DKIM pass, Google Jobs listing, Maps office | "And it doesn't cry wolf. A real offer gets green only with positive proof: the email is authenticated by the company's domain, the role is on Google Jobs, the office is on Maps." |
| 1:52 to 2:12 | G6: second offer from a different brand; P06 local hit; campaign page "2 offers linked to the same UPI ID", orgs Infosys and HCLTech | "Scammers reuse payment IDs across brands. Special26 links them into campaigns, so a placement officer can warn everyone at once." |
| 2:12 to 2:30 | `eval/report.md` table: S26 vs fee-rule vs local-only; ablation row "without Lens" | "On {n} labelled offers: red precision {x}, {y}% of fraud caught, {z}% false reds on real offers. Removing Lens or Maps measurably hurts, so every engine is earning its place." |
| 2:30 to 2:45 | Next steps panel, Share → WhatsApp preview | "Then it tells you what to do: confirm on the official careers page, call 1930 if you've paid, and share the verdict with your family." |
| 2:45 to 2:50 | Logo + URL + "#BuiltWithSerpApi" | "Special26. Check before you pay." |

Fill `{n}`, `{x}`, `{y}`, `{z}` from the holdout run. Do not round in our favour.

## 3. Golden cases

All live in `tests/golden/inputs/`. Constructed domains must be checked as unregistered via RDAP when the case is created, never registered by us, and labelled "constructed demo sample" in the case file and the README.

### G1: Tech Mahindra lookalike with UPI fee (headline case)

```
Dear <RECIPIENT>,

Congratulations! You have been selected for the position of Data Analyst Intern at
Tech Mahindra Limited, Noida, with a stipend of Rs. 15,000/- per month. You were
shortlisted on the basis of your profile; no further interview is required.

To issue your offer letter, please complete your Police Clearance Certificate
verification by paying Rs. 2,000/- to UPI ID techm.hr@ybl within 24 hours and
share the screenshot on WhatsApp +91 98765 43210.

Regards,
Ritika Sharma
HR Onboarding Executive
hr.onboarding@techmahindra-careers.in
```

Expected: `red`, `impersonation`, decisive `{D1_FEE_VS_NOTICE, D3_LOOKALIKE_PLUS_FEE}`, reason 1 code `D1_FEE_VS_NOTICE`. Worked score in `08-algorithm.md` §6.1.

### G2: PM Internship Scheme Google Form with fee

```
PM Internship Scheme 2026: Registration Open
Selected candidates will receive Rs 5,000 per month for 12 months.
Register now: https://forms.gle/<constructed>
Registration fee Rs 499 (non-refundable) to pmis.registration@paytm
Last date: today 11:59 PM. Limited seats.
```

Expected: `red`, `impersonation`, decisive includes `D2_SCHEME_IMPERSONATION`, reason 1 code `D2_SCHEME_IMPERSONATION`, next steps show `pminternship.mca.gov.in`.

### G3: Genuine offer email with DKIM (consented)

A real internship or job offer `.eml` from a team member or friend, used with written consent, recipient details redacted. Must contain the company's real sender domain and an `Authentication-Results` header with `dkim=pass`.

Expected: `green`, findings include `P03_DKIM_ALIGNED_OFFICIAL` and at least one of `P07_ROLE_LISTED`, `P08_OFFICE_MATCH`; no `P11_CANDIDATE_PAYS`; reason 1 code `P03_DKIM_ALIGNED_OFFICIAL`.

If P07 and P08 both miss for the real company, the case stays green only through P03 + P02; if the score is not ≤ -2.0, pick a different consented offer rather than change weights.

### G4: Unknown startup, free-mail sender, documents first, no fee

```
Hi <RECIPIENT>,
We at Nimbleleaf Analytics Pvt Ltd liked your resume. You are selected as a
Business Development Intern (remote), stipend Rs 8,000 per month. Please send
your Aadhaar, PAN and a cancelled cheque to nimbleleaf.hiring@gmail.com to
proceed with onboarding.
Thanks,
Karan
```

(Fictional company name; confirm no real company uses it when creating the case.)

Expected: `amber`. `P01_NO_PRESENCE` (+1.0), `P02_FREEMAIL_NO_PRESENCE` (+0.8), `P11_NO_INTERVIEW` (+1.0), S = 2.8 < 3.0. This shows Special26 does not call everything a scam: it says "could not verify" and tells the student not to send ID documents yet.

### G5: Stock-photo HR persona with training kit fee

Text claims Wipro, sender `wipro.hrteam@gmail.com`, training kit fee ₹3,500 to a UPI ID. HR photo: a freely licensed stock portrait downloaded from a stock site (record the URL and license in the case file).

Expected: `red`, `impersonation` (artifact family ≥ 2.5 from `P09_STOCK_PHOTO`), findings include `P02_FREEMAIL`, `P09_STOCK_PHOTO`, `P11_CANDIDATE_PAYS`. Decisive set is whatever the recording shows for P04 (assert it after recording, then freeze).

### G6: Two brands, one UPI ID (campaign)

- G6a: claims Infosys, sender `onboarding@infosys-careers.co` (constructed), ₹1,500 "document verification" to `hrdesk.onboard@ybl`.
- G6b: claims HCLTech, sender `talent@hcltech-hiring.in` (constructed), ₹1,800 "ID card charges" to `hrdesk.onboard@ybl`.

Run G6a then G6b. Expected: both `red`; G6b has `P06_ID_SEEN_LOCALLY`; both in one campaign with `edge_counts.upi ≥ 1`, `orgs = ["Infosys", "HCLTech"]`.

## 4. Recording checklist

- [ ] `SPECIAL26_MODE=replay`, `demo.db` recorded on 9 Oct, banner visible.
- [ ] Browser zoom 125%, phone frame for mobile shots, notifications off.
- [ ] Fake recipient data only; no real student names, numbers or emails anywhere on screen.
- [ ] Every receipt opened on screen has a working link (check the night before).
- [ ] Captions burned in (judges may watch muted).
- [ ] Final length checked ≤ 2:55.
- [ ] Video public, plays logged out, link tested on mobile data.

## 5. Live backup for judges

- Public URL in live mode with a daily cap.
- `docker run -e SPECIAL26_MODE=replay -p 8000:8000 <image>` reproduces every golden case without a key.
- The three example chips on the home page load G1, G2, G3 instantly.
