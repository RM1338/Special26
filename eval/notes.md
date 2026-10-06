# Evaluation notes (read with `report.md`)

## What was run, and why it is small

- **The SerpApi account is on the Free Plan** (250 searches a month). After development and the golden demo recording, 54 searches were left. Recording all 60 cases would have taken about 269 new searches, even reusing every response already paid for.
- **So the report has two parts:**
  - **Part 1:** all 60 cases with the systems that need no searches: B0 (fee keyword rule) and B3 (Special26 local only).
  - **Part 2:** 13 cases recorded live for 41 searches. The subset was chosen as the cheapest cases from each category, plus one complete campaign pair. On these, S26 is compared with B0 and B3, and five ablations are computed by masking engines in replay (no extra searches).
- **Every case is constructed** (`eval/build_cases.py`). Fraud cases follow patterns described in the cited public reports. Genuine cases are messages from real employers' real domains, or from fictional small startups. No real student data was available.
- **Treat the numbers as a smoke test, not a benchmark.** With 13 cases the 95% intervals are very wide.

## What the subset shows

- **S26:** no false reds (0 of 6 genuine); red recall 1.00 on the 7 fraud cases; green yield 0.40 (2 of 5 non-startup genuine offers).
- **B0 and B3 never produce green.** That's the point of the searches: positive anchors from Maps (office match) and Jobs (role listing) are the only way a genuine offer earns "Consistent with a genuine offer".
- **Masking `google` raises green yield (+0.40) and lowers red recall (-0.14).**
  - Big employers always have general complaint chatter (`P05_COMPLAINTS_GENERAL`, +0.7) and a published fraud notice (`P04_NOTICE_FOUND`, +0.3). Both push genuine big-brand offers from S ≈ -2 to amber.
  - This is the asymmetric caution `02` §7 asks for: amber ("could not verify") rather than an unearned green.
  - Weights are frozen, and thresholds may only be tuned on dev (`11` §2.3). These genuine cases are holdout, so nothing was tuned on them.
- **Masking `google_maps` lowers green yield (-0.20).** The Maps office match was a green anchor.
- **Lens has no effect on this subset**, because none of the 13 cases has an image. The Lens result rests on the golden case G5 (stock photo found on pexels.com).

## Error analysis (11 §8)

- **F-RPT-03 (fraud) was amber before an extraction fix.** "deposit" sat 14 tokens before the amount, outside the 12-token window. Fixed by a whole-sentence fallback (D-51). Extraction fix, allowed.
- **Genuine offers did not reach green because no role was extracted.** `08`'s two role patterns miss "offer you the position of X" and similar. Extra patterns added (D-51).
- **For Infosys and Tech Mahindra, Google Jobs returned no listings** for the role in the stated city. Absence is not evidence (`08` P07), so these stay amber. That's correct behaviour for an unverifiable offer, not an error.
- **Wipro's P07 match is loose:** "Project Leader" against "Project Engineer" scores 61, just over the `08` threshold of 60. The threshold is spec, not tuned.
