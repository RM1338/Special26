# Tasks for the second teammate

Special26's code is built and live (https://web-production-4b8c8.up.railway.app). What is left is mostly work only
a person can do: collect real material, verify facts by hand, test on real phones, and make the video. Each task says
what "done" means and where the output goes. Put files in the paths given and open a pull request, or send them to
Ronel.

Deadlines (IST): feature freeze **Fri 9 Oct 12:00**, submission **Sat 10 Oct 18:00**.

Read first (15 minutes): `README.md`, then `docs/14-demo-plan.md` (the video script) and `docs/09-user-flow.md`.

---

## 1. Employer fraud notices (highest value, start now, due Thu 8 Oct)

**Why:** when an offer asks for money and the employer's own website says "we never charge candidates", Special26
shows its strongest reason ("Tech Mahindra's own recruitment fraud notice says it never charges candidates").
Google search is unreliable for finding these notices, so we record them by hand. Today only Tech Mahindra has one.

**Do:** for each company below, find its own recruitment-fraud or "beware of fake offers" page **on the company's
own website**, and copy one sentence that says it never charges candidates.

Infosys, Tata Consultancy Services, Wipro, HCLTech, Cognizant, Accenture, Capgemini, IBM, Deloitte, LTIMindtree,
Mphasis, Zoho, Amazon, Flipkart, HDFC Bank, ICICI Bank, Larsen & Toubro, Dr. Reddy's, and Tech Mahindra (re-check
the existing one).

**Output:** one row per company in a sheet or `docs/fraud_notices.csv` with columns:
`company, notice_url, exact_quote, checked_on`

**Done when:** each quote is copied word for word from a page whose address is the company's own domain (not a news
site, not LinkedIn). If a company has no such page, write `none found`. Never paraphrase a quote.

## 2. More known companies (due Thu 8 Oct)

**Why:** the company dictionary has 54 companies; the target is 80 top campus recruiters. A company in the dictionary
gets its verified official domains even when Google is unclear.

**Do:** add 26 more companies students commonly get offers from (banks, Big 4, product companies, consulting, FMCG,
EdTech, startups with big hiring). For each: the official website domain(s) and the careers page URL, checked by
opening the company's own site.

**Output:** a sheet or `docs/new_companies.csv` with columns:
`name, other_names_people_use, official_domains, careers_url, checked_on`

**Done when:** every domain was opened in a browser and is the company's own (watch out for look-alike or reseller
sites).

## 3. Real offer messages, with consent (due Thu 8 Oct)

**Why:** our scam examples and evaluation cases are written from news reports, not real messages. Real ones make the
evaluation honest and the demo stronger.

**Do:** ask classmates, seniors and the placement cell for:

- **(a) Fake or suspicious offers** students received: WhatsApp, Telegram, email or PDF text. Screenshots are fine.
- **(b) One real offer email** from a known company, as an original `.eml` file (Gmail: open the email, tap the
  three dots, *Download message*). This is the missing golden case **G3** (`docs/14-demo-plan.md` §3).

**Rules, no exceptions:**

- Get written permission (a WhatsApp message saying "yes, you can use it" is enough; save a screenshot of it).
- Remove the student's own name, phone number, email, Aadhaar, PAN and photos before sharing with us. Keep the
  scammer's details (sender email, UPI ID, phone) exactly as they are: those are the evidence.
- Do not contact or reply to the scammers.

**Output:** a folder (shared drive) with one file per message, plus a note per file: where it came from, the date
received, and "consent: yes".

**Done when:** at least 10 suspicious messages and 1 genuine `.eml` with consent.

## 4. Real-phone testing and the WhatsApp preview (due Fri 9 Oct 10:00)

**Do:**

1. On an Android phone and (if anyone has one) an iPhone, open the live site on mobile data, not Wi-Fi.
2. Run the three example chips on the home page (each uses a little of our daily search budget; if you see "We've hit
   today's search limit", that is expected, note the time and continue with the other steps).
3. Open a finished check, tap every reason, open and close a few receipts, expand "All findings".
4. Tap **Share**, send the link to yourself on WhatsApp, and check the preview shows the headline (for example
   "Strong signs of impersonation. Do not pay.").
5. Open the shared link on the other phone.

**Output:** a short list of problems, each with: phone model, browser, what you did, what went wrong, a screenshot.

**Done when:** the list is sent (an empty list is a good result).

## 5. The demo video (script due Fri 9 Oct, video Sat 10 Oct 12:00)

**Why:** the hackathon needs a public video under 3 minutes. It is the most important judged item after the code.

**Do:**

1. Rehearse the script in `docs/14-demo-plan.md` §2 (target 2:50). Record in **replay mode** so every take is
   identical and costs no credits:
   ```bash
   docker build -t special26 .
   docker run -e SPECIAL26_MODE=replay -p 8000:8000 special26
   # open http://localhost:8000
   ```
   (If Docker is not available, ask Ronel for a replay link.)
2. Screen-record at browser zoom 125%, notifications off, with a phone-sized window for the mobile shots.
3. Voiceover in plain English; burn in captions (judges may watch muted).
4. Fill the eval numbers in the script from `eval/report.md` honestly (Part 2 table), and say it was a small
   evaluation; do not round in our favour.
5. Upload as public (YouTube, unlisted is not enough), check it plays when logged out, on mobile data.

**Done when:** the video is under 2:55, public, captioned, and the link works logged out.

## 6. Clean-machine Docker check (due Fri 9 Oct)

**Why:** judges without an API key will use replay mode in Docker. Nobody has tested that on a fresh machine yet.

**Do:** on your laptop (Docker installed):

```bash
git clone https://github.com/RM1338/Special26 && cd Special26
docker build -t special26 .
# now turn off Wi-Fi and mobile data, so the app has no internet at all
docker run -e SPECIAL26_MODE=replay -p 8000:8000 special26
```

Open http://localhost:8000 and run the "WhatsApp offer with a fee" and "PM Internship form" examples.

**Done when:** both examples reach a red verdict with no internet, and you tell us how long the build took and
whether anything failed.

## 7. Submission (Sat 10 Oct, 13:00 to 17:00)

**Do:** fill the hackathon submission form with: project name, one-line pitch (top of `README.md`), the live URL, the
GitHub URL, the video link, and the `#BuiltWithSerpApi` tag. Add GitHub topics to the repo (`serpapi`, `hackathon`,
`india`, `fraud-detection`). Open every link from a phone on mobile data before submitting.

**Done when:** submitted by 18:00 with every link checked.

---

## Also worth asking (anyone can do it)

- **More SerpApi searches.** Our free plan has about 18 searches left this month. Ask the hackathon organisers whether
  participants get extra credits. With about 400 more searches we can run the full evaluation on all 60 cases.

## What Ronel and Claude keep

Code changes and fixes, deploying, recording search results for the demo, turning task 1 to 3 outputs into data
files, re-running the evaluation, and the README.
