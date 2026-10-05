"""Build eval/cases/*.json (11 §2). Every case is constructed; fraud cases follow a cited public report or pattern.

Run: .venv/bin/python eval/build_cases.py   (deterministic; rewrites eval/cases/)
No real person's data. Identifiers are constructed demo samples (D-49).
"""
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).parent / "cases"
REPORTS = {
    "dinamalar": "https://www.dinamalar.com/news/kalvimalar-news-en/fraudsters-target-college-students-with-fake-internship-offers-warn-cyber-experts/57787",
    "bt_jaipur": "https://www.businesstoday.in/latest/trends/story/company-ko-pocket-money-chahiye-techie-shares-rs23000-internship-offer-letter-but-with-an-unexpected-demand-533454-2026-05-27",
    "techenclave": "https://techenclave.com/t/beware-of-scam-wipro-recruitment/161897",
    "cc_hcl": "https://www.consumercomplaints.in/complaints/hcl-technologies-fake-job-offer-c809999.html",
    "drreddys": "https://www.drreddys.com/caution-notice-recruitment-fraud",
    "hrkatha_al": "https://www.hrkatha.com/news/the-case-of-fake-ashok-leyland-appointment-letters/",
    "pib_msme": "https://newsonair.gov.in/government-debunks-fake-internship-claim-circulating-on-social-media/",
    "aicte_2026": "https://www.careerindia.com/features/aicte-internship-scams-new-2026-rules-to-identify-fake-offers-and-protect-your-career-011-65999.html",
    "airasia": "https://morungexpress.com/airasia-india-cautions-job-seekers-against-frauds",
    "ncs": "https://www.republicworld.com/india/fake-job-scam-in-karnataka-fraudsters-dupe-candidates-on-national-career-service-portal-articleshow",
    "jobrise": "https://jobrise.io/en/blog/job-scams-india-avoid-2026/",
    "careerindia": "https://www.careerindia.com/features/internship-scams-2026-how-to-spot-fake-job-offers-and-avoid-paying-fees-011-66049.html",
    "quickheal": "https://www.quickheal.co.in/knowledge-centre/fake-job-offer-scams-how-fraudsters-use-linkedin-and-whatsapp/",
    "tm_notice": "https://careers.techmahindra.com/CPDOC/Recruitment_Fraud.pdf",
}
CASES: list[dict] = []


def case(case_id, label, category, group, text, expected, source=None, notes=""):
    CASES.append({"case_id": case_id, "label": label, "category": category, "template_group": group,
                  "source_url": source, "provenance": "constructed", "text": text.strip(), "files": [],
                  "confirmed_claims": None, "expected_tier": expected, "notes": notes})


# ---- fraud: public_report (patterns from cited reports; text constructed) ------------------------------------------
case("F-RPT-01", "fraud", "public_report", "tg-police-clearance", """
Dear <RECIPIENT>,
Congratulations, you are shortlisted for the Zoho Summer Internship 2026 with a stipend of Rs 15,000 per month.
Before we release your offer letter you must get a Police Clearance Certificate through our verification partner.
Kindly pay the PCC charges of Rs 2,000 to UPI ID zoho.intern.pcc@ybl within 24 hours and share the screenshot.
Regards,
Deepa R
HR Executive
zoho.internships.desk@gmail.com""", "red", REPORTS["dinamalar"])
case("F-RPT-02", "fraud", "public_report", "tg-internship-fee-form", """
Dear <RECIPIENT>,
We are pleased to offer you a remote internship as a Software Development Intern at Codexa Labs. Your monthly stipend
will be Rs 23,000 in hand. To confirm your enrollment please pay the internship fees of Rs 1,594 through the form
link: https://forms.gle/cdxIntern2026 within 48 hours. Your offer letter will be shared after payment.
Team HR, Codexa Labs""", "red", REPORTS["bt_jaipur"])
case("F-RPT-03", "fraud", "public_report", "tg-cash-deposit-hrd", """
Dear Candidate,
With reference to your application you have been shortlisted for the post of Process Associate at Wipro, Pune.
You have to deposit the (Cash) as an initial amount in favor of Company HRD Department for Rs. 4,250/-.
Kindly deposit within 24 hours, 18 candidates have already paid. Send the slip to wipro.hrd.pune@gmail.com.
HR Department""", "red", REPORTS["techenclave"])
case("F-RPT-04", "fraud", "public_report", "tg-new-plant", """
Your Resume has been selected from TIMESJOBS.COM for our new plant of HCLTech. The Company selected 65 candidates
shortlist for Senior Engineer, Administration and Production. You have to deposit the (Cash) as an initial amount in
favor of our company accountant for Rs.6,725/- which is refundable with your first salary.
Contact HR: hcl.newplant.recruit@yahoo.com""", "red", REPORTS["cc_hcl"])
case("F-RPT-05", "fraud", "public_report", "tg-airfare-deposit", """
Dear <RECIPIENT>,
You have cleared the preliminary rounds at Dr. Reddy's Laboratories and are invited for the final interview in
Hyderabad. The company will provide return air-fare. To book tickets pay a refundable security deposit of
Rs 7,500 to UPI drreddys.travel@okaxis today. Talent Acquisition Team
talent@drreddys-careers.com""", "red", REPORTS["drreddys"], "Dr. Reddy's is not in the seed dictionary; P01 must find it.")
case("F-RPT-06", "fraud", "public_report", "tg-appointment-deposit", """
Congratulations <RECIPIENT>!
You are selected as Graduate Engineer Trainee at Ashok Leyland, Chennai. Your appointment letter is ready.
As per company policy every new joinee has to submit a security deposit of Rs 8,000 which will be returned with the
first salary. Transfer to our placement consultant and send the screenshot on WhatsApp +91 98765 11002.
ashokleyland.placements@gmail.com""", "red", REPORTS["hrkatha_al"])
case("F-RPT-07", "fraud", "public_report", "tg-msme-form", """
Ministry of MSME approved 2-month Internship Programme 2026 for medical, healthcare and B.Tech students.
Certificate will be issued by the Government of India. Register through the Google Form: https://forms.gle/msmeIntern26
A processing fee of Rs 750 is applicable for the government certificate. Last date to apply is this Sunday.""",
     "red", REPORTS["pib_msme"])
case("F-RPT-08", "fraud", "public_report", "tg-aicte-fee", """
Subject: Mandatory Internship Fee for AICTE Approved Internship
Dear Student, as per the new guidelines of AICTE the National Internship Portal requires every nominated student to
pay the mandatory internship fee of Rs 2,499 to activate the account. Pay now at https://aicte-internship-portal.in/pay
before Friday or your internship credits will not be awarded.""", "red", REPORTS["aicte_2026"])
case("F-RPT-09", "fraud", "public_report", "tg-cabin-crew", """
AirAsia India walk-in recruitment for Cabin Crew and Ground Staff, freshers welcome, salary Rs 35,000 to 55,000.
You are shortlisted on the basis of your profile. Pay the registration and uniform charges of Rs 2,800 to confirm your
interview slot. Contact the recruitment officer on WhatsApp +91 90031 22045 immediately, limited seats.""",
     "red", REPORTS["airasia"])
case("F-RPT-10", "fraud", "public_report", "tg-ncs-portal", """
Dear Jobseeker,
Your profile on the National Career Service portal has been shortlisted for a government contract job with salary of
Rs 28,000. Please pay the application processing fee of Rs 1,500 and document verification fee of Rs 2,000 through
https://bit.ly/ncs-verify26 to receive the interview call letter. Do not share this message.""", "red", REPORTS["ncs"])

# ---- fraud: lookalike_fee ------------------------------------------------------------------------------------------
LOOK = [
    ("F-LKF-01", "Infosys", "infosys-hr.xyz", "Systems Engineer Trainee", "Mysuru", "document verification", "1,500"),
    ("F-LKF-02", "Tata Consultancy Services", "tcs-careers.in", "Assistant System Engineer", "Chennai",
     "training kit", "3,000"),
    ("F-LKF-03", "Accenture", "accenture-jobs.co", "Associate Software Engineer", "Bengaluru",
     "refundable laptop deposit", "4,500"),
    ("F-LKF-04", "Cognizant", "cognizant-hiring.in", "Programmer Analyst Trainee", "Pune", "background verification",
     "2,200"),
    ("F-LKF-05", "Deloitte", "de1oitte.com", "Analyst", "Hyderabad", "registration", "999"),
    ("F-LKF-06", "Capgemini", "capgemini.co.in", "Software Engineer", "Noida", "offer letter charges", "1,800"),
]
for i, (cid, org, dom, role, city, purpose, amt) in enumerate(LOOK):
    style = i % 3
    if style == 0:
        text = f"""Dear <RECIPIENT>,
Congratulations! You have been selected for the position of {role} at {org}, {city}.
To release your offer letter please pay Rs {amt} towards {purpose} to UPI ID onboard.{i + 1}desk@ybl within 48 hours.
Regards,
HR Onboarding Team
hr@{dom}"""
    elif style == 1:
        text = f"""Hi <RECIPIENT>,
Greetings from {org}. You are selected as a {role} for our {city} office. Kindly complete the {purpose} formality
by paying Rs {amt} via the link shared. Joining date will be confirmed after payment.
Thanks,
Talent Acquisition
careers@{dom}"""
    else:
        text = f"""Dear Candidate,
This is to inform you that your candidature for {role} at {org} has been approved. A {purpose} payment of Rs {amt}
is mandatory before onboarding. Pay to the account below today itself to avoid cancellation.
Recruitment Cell
recruitment@{dom}"""
    case(cid, "fraud", "lookalike_fee", f"tg-lookalike-{style}", text, "red", REPORTS["tm_notice"],
         f"Constructed lookalike domain {dom}; RDAP-unregistered status to be confirmed when recording.")

# ---- fraud: scheme_impersonation -----------------------------------------------------------------------------------
case("F-SCH-01", "fraud", "scheme_impersonation", "tg-scheme-whatsapp", """
PM Internship Scheme Phase 3: get Rs 5,000 monthly and one time grant Rs 6,000. Registration charges Rs 599 for
slot booking. Apply on WhatsApp +91 90012 33456 and pay on pmis.slots@paytm. Limited seats, last date today.""",
     "red", REPORTS["careerindia"])
case("F-SCH-02", "fraud", "scheme_impersonation", "tg-scheme-form", """
Skill India NSDC Digital Internship 2026 for diploma and degree students. Stipend Rs 8,000 per month.
Enrol through https://forms.gle/nsdcSkill2026 and pay the enrolment fee of Rs 399. Certificate from Skill India.""",
     "red", REPORTS["careerindia"])
case("F-SCH-03", "fraud", "scheme_impersonation", "tg-scheme-form", """
NITI Aayog internship 2026 applications open for all streams. Fill the Google Form https://forms.gle/nitiIntern2026
and upload your resume. Selected candidates will be informed by email within a week.""", "red",
     REPORTS["careerindia"], "No fee: D2 via form; P11_SCHEME_OFF_PORTAL + FORM_OR_SHORTLINK.")
case("F-SCH-04", "fraud", "scheme_impersonation", "tg-scheme-telegram", """
Digital India Internship by MeitY: work from home, stipend Rs 10,000. Join our Telegram group https://t.me/dIndiaIntern
for the interview on Telegram. Registration fee Rs 300 payable to meity.intern@ybl.""", "red", REPORTS["careerindia"])

# ---- fraud: persona (documents first, free-mail, no upfront fee) ----------------------------------------------------
PERSONA = [
    ("F-PER-01", "Amazon", "Virtual Customer Service Associate", "amazon.vcs.hiring@gmail.com"),
    ("F-PER-02", "Flipkart", "Catalog Operations Intern", "flipkart.talent.team@outlook.com"),
    ("F-PER-03", "Paytm", "Business Development Associate", "paytm.hr.onboard@gmail.com"),
    ("F-PER-04", "IBM", "Associate Developer", "ibm.campus.connect@yahoo.com"),
]
for cid, org, role, sender in PERSONA:
    case(cid, "fraud", "persona", "tg-persona-docs", f"""
Hi <RECIPIENT>,
I am the hiring manager at {org}. We liked your resume and you are selected as {role} without interview.
Please send your Aadhaar, PAN, bank passbook copy and a cancelled cheque to {sender} today so that we can create your
employee ID. Your offer letter will follow.
Regards""", "amber", REPORTS["quickheal"], "No fee and no photo: expected amber (11 §2.1 persona); red needs Lens.")

# ---- fraud: campaign_variants (pairs share a UPI ID across brands) -------------------------------------------------
PAIRS = [("Infosys", "Wipro", "campaign.alpha.desk@ybl"), ("Tata Consultancy Services", "HCLTech", "verify.beta.cell@ybl"),
         ("Flipkart", "Swiggy", "onboard.gamma.hr@okaxis")]
for n, (a, b, upi) in enumerate(PAIRS, 1):
    for side, org in (("a", a), ("b", b)):
        case(f"F-CMP-0{n}{side}", "fraud", "campaign_variants", f"tg-campaign-{n}", f"""
Dear <RECIPIENT>,
You are selected for the Graduate Trainee programme at {org}. Kindly pay the ID card and joining kit charges of
Rs 1,{n}00 to UPI ID {upi} within 24 hours to block your joining date.
Thanks, Onboarding Desk""", "red", REPORTS["jobrise"], f"Pair {n}: same UPI across {a} and {b} (campaign edge).")

# ---- genuine: official_template (real employers, real domains, no fee) ----------------------------------------------
OFFICIAL = [
    ("G-OFF-01", "Tata Consultancy Services", "tcs.com", "Assistant System Engineer", "Chennai"),
    ("G-OFF-02", "Infosys", "infosys.com", "Systems Engineer", "Mysuru"),
    ("G-OFF-03", "Wipro", "wipro.com", "Project Engineer", "Bengaluru"),
    ("G-OFF-04", "Accenture", "accenture.com", "Associate Software Engineer", "Hyderabad"),
    ("G-OFF-05", "Cognizant", "cognizant.com", "Programmer Analyst Trainee", "Chennai"),
    ("G-OFF-06", "Capgemini", "capgemini.com", "Analyst", "Mumbai"),
    ("G-OFF-07", "HCLTech", "hcltech.com", "Graduate Engineer Trainee", "Noida"),
    ("G-OFF-08", "Tech Mahindra", "techmahindra.com", "Associate Software Engineer", "Pune"),
]
for i, (cid, org, dom, role, city) in enumerate(OFFICIAL):
    case(cid, "genuine", "official_template", f"tg-official-{i % 2}", f"""
Dear <RECIPIENT>,
We are pleased to offer you the position of {role} at {org}, {city}, following your campus selection process.
Your joining details, background verification steps and onboarding schedule are available on the official
candidate portal. {org} does not charge any fee at any stage of recruitment.
Warm regards,
Campus Recruitment Team
campus.hiring@{dom}""" if i % 2 == 0 else f"""
Hi <RECIPIENT>,
Congratulations on clearing the interview for {role} with {org}. Please log in to the careers portal to accept the
offer and upload your documents. Our {city} office will contact you about the joining date.
Regards,
Talent Acquisition, {org}
careers@{dom}""", "green", None, "Constructed message from the employer's real domain; no fee.")

# ---- genuine: jobs_listing_message (consented_real substitute, D-49) ------------------------------------------------
LISTINGS = [
    ("G-JOB-01", "Amazon", "amazon.com", "Software Development Engineer Intern", "Bengaluru"),
    ("G-JOB-02", "Flipkart", "flipkart.com", "Data Analyst", "Bengaluru"),
    ("G-JOB-03", "Zoho", "zoho.com", "Member Technical Staff", "Chennai"),
    ("G-JOB-04", "Swiggy", "swiggy.in", "Business Analyst", "Bengaluru"),
    ("G-JOB-05", "Paytm", "paytm.com", "Product Analyst", "Noida"),
    ("G-JOB-06", "Deloitte", "deloitte.com", "Analyst", "Hyderabad"),
    ("G-JOB-07", "PwC", "pwc.com", "Associate", "Kolkata"),
    ("G-JOB-08", "EY", "ey.com", "Tax Analyst", "Gurugram"),
    ("G-JOB-09", "KPMG", "kpmg.com", "Analyst", "Bengaluru"),
    ("G-JOB-10", "IBM", "ibm.com", "Associate Developer", "Pune"),
    ("G-JOB-11", "Oracle", "oracle.com", "Associate Consultant", "Hyderabad"),
    ("G-JOB-12", "Adobe", "adobe.com", "Product Intern", "Noida"),
    ("G-JOB-13", "Samsung", "samsung.com", "Software Engineer", "Bengaluru"),
    ("G-JOB-14", "Bosch", "bosch.com", "Graduate Apprentice Trainee", "Coimbatore"),
    ("G-JOB-15", "Siemens", "siemens.com", "Graduate Trainee Engineer", "Pune"),
    ("G-JOB-16", "HDFC Bank", "hdfc.bank.in", "Relationship Manager", "Mumbai"),
]
for i, (cid, org, dom, role, city) in enumerate(LISTINGS):
    style = i % 3
    body = [f"""Hello <RECIPIENT>,
Thank you for applying for the {role} role at {org} in {city}. We would like to schedule your first interview round
next week. Please pick a slot using the link in your candidate account on our careers site.
Best,
Recruiting Team
recruiting@{dom}""", f"""Dear <RECIPIENT>,
Your application for {role} ({city}) at {org} has moved to the next stage. The hiring manager will meet you for a
technical discussion. No payment is required at any stage of our hiring process.
Regards,
University Relations, {org}
university.relations@{dom}""", f"""Hi <RECIPIENT>,
I am reaching out from {org} regarding the {role} opening in {city}. Your profile matches the role and we would like
to invite you to an online assessment followed by interviews. Details are on our official careers page.
Thanks,
Talent Partner
talent@{dom}"""][style]
    case(cid, "genuine", "jobs_listing_message", f"tg-listing-{style}", body, "green", None,
         "Constructed recruiter message for a real employer, real domain (consented_real substitute, D-49).")

# ---- genuine: small_startup (fictional, little web presence; amber is correct) -------------------------------------
STARTUPS = [
    ("G-SUP-01", "Brightloom Analytics", "brightloom-analytics.in", "Data Science Intern", "Coimbatore"),
    ("G-SUP-02", "Kavya Robotics", "kavyarobotics.in", "Embedded Systems Intern", "Pune"),
    ("G-SUP-03", "Tidewell Labs", "tidewelllabs.com", "Frontend Developer Intern", "Kochi"),
    ("G-SUP-04", "Quillmark Studio", "quillmarkstudio.in", "UX Design Intern", "Bengaluru"),
    ("G-SUP-05", "Saffron Grid Energy", "saffrongrid.in", "Research Intern", "Jaipur"),
    ("G-SUP-06", "Mintpath Fintech", "mintpath.co.in", "Backend Developer Intern", "Hyderabad"),
]
for cid, org, dom, role, city in STARTUPS:
    case(cid, "genuine", "small_startup", "tg-startup", f"""
Hi <RECIPIENT>,
Thanks for the conversation last week. We are happy to offer you the {role} position at {org}, {city}, for six months
with a monthly stipend of Rs 12,000. Please reply to accept and we will share the internship agreement.
Cheers,
Founder, {org}
founder@{dom}""", "amber", None, "Fictional small company (11 §2.2 small_startup): amber or grey is correct, not red.")


def assign_splits(cases: list[dict]) -> None:
    """Deterministic ~40/60 dev/holdout per label, whole template_groups only (11 §2.3)."""
    for label in ("fraud", "genuine"):
        mine = [c for c in cases if c["label"] == label]
        sizes: dict[str, int] = {}
        for c in mine:
            sizes[c["template_group"]] = sizes.get(c["template_group"], 0) + 1
        dev, target = set(), 0.4 * len(mine)
        for g in sorted(sizes, key=lambda g: hashlib.sha256(g.encode()).hexdigest()):
            if sum(sizes[x] for x in dev) + sizes[g] <= target + 1:
                dev.add(g)
        for c in mine:
            c["split"] = "dev" if c["template_group"] in dev else "holdout"


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for f in OUT.glob("*.json"):
        f.unlink()
    assign_splits(CASES)
    for c in CASES:
        (OUT / f"{c['case_id']}.json").write_text(json.dumps(c, indent=1, ensure_ascii=False) + "\n")
    by = {}
    for c in CASES:
        by.setdefault((c["label"], c["split"]), 0)
        by[(c["label"], c["split"])] += 1
    print(len(CASES), "cases", by)
