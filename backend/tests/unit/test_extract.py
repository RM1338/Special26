"""FR-10 (>= 3 positive, 2 negative per claim type), FR-11, FR-13, FR-16, NFR-02."""
import time
from pathlib import Path

import pytest

from special26.claims.amounts import classify as purpose_payer
from special26.claims.extract import extract_claims
from special26.claims.redact import redact

GOLDEN = Path(__file__).parents[1] / "golden/inputs"


def claims_of(text, t):
    return [c.value for c in extract_claims(text).all(t)]


def one(text, t):
    vals = claims_of(text, t)
    return vals[0] if vals else None


# ---- type-by-type: (text, expected or None) -------------------------------------------------------------------
@pytest.mark.parametrize("text,addr", [
    ("Regards,\nAsha\nhr@acme-careers.in", "hr@acme-careers.in"),
    ("From: talent@infosys.com\nSubject: offer", "talent@infosys.com"),
    ("Thanks\nmail us at jobs.desk@gmail.com", "jobs.desk@gmail.com"),
    ("Pay to techm.hr@ybl now", None),                       # UPI, not an email
    ("Visit our office in Pune", None),
])
def test_sender_email(text, addr):
    v = one(text, "sender_email")
    assert (v["address"] if v else None) == addr


@pytest.mark.parametrize("text,rt", [
    ("From: a@acme.com\nPlease reply to hr.acme@gmail.com with documents", "hr.acme@gmail.com"),
    ("Regards a@acme.com. Send your documents to docs.acme@outlook.com", "docs.acme@outlook.com"),
    ("Regards a@acme.com\nKindly send your Aadhaar and PAN to x.hire@yahoo.com", "x.hire@yahoo.com"),
    ("Reply to this message on WhatsApp", None),
    ("Regards,\nhr@acme.com", None),
])
def test_reply_to(text, rt):
    v = one(text, "reply_to")
    assert (v["address"] if v else None) == rt


@pytest.mark.parametrize("text,kind", [
    ("Register now: https://forms.gle/abc123", "form"),
    ("Pay here https://rzp.io/l/fee", "payment"),
    ("Join https://t.me/hrgroup today", "messaging"),
    ("Apply at www.acme-careers.in.", "other"),
    ("See bit.ly/abc", None),                                 # bare shortener without scheme is not a URL token
])
def test_url(text, kind):
    v = one(text, "url")
    assert (v["kind"] if v else None) == kind


def test_url_not_from_email_domain():
    assert claims_of("Regards\nhr@techmahindra-careers.in", "url") == []
    assert claims_of("Rs. 2,000 p.m.", "url") == []


@pytest.mark.parametrize("text,e164,role", [
    ("Call HR on +91 98765 43210", "+919876543210", "sender"),
    ("WhatsApp 9876543210 for details", "+919876543210", "sender"),
    ("Number: 09123456789", "+919123456789", "unknown"),
])
def test_phone_positive(text, e164, role):
    assert one(text, "phone") == {"e164": e164, "role": role}


@pytest.mark.parametrize("text", ["Order 1234567890 shipped", "Ref 98765 4321"])
def test_phone_negative(text):
    assert claims_of(text, "phone") == []


@pytest.mark.parametrize("text,vpa,known", [
    ("Pay to techm.hr@ybl", "techm.hr@ybl", True),
    ("UPI: fees.desk@okhdfcbank", "fees.desk@okhdfcbank", True),
    ("Scan and pay on GPay to hrteam@abcd", "hrteam@abcd", False),
])
def test_upi_positive(text, vpa, known):
    v = one(text, "upi_id")
    assert (v["vpa"], v["handle_known"]) == (vpa, known)


@pytest.mark.parametrize("text", ["Mail hr.onboarding@techmahindra-careers.in", "Write to team@unknownhandle today"])
def test_upi_negative(text):
    assert claims_of(text, "upi_id") == []


@pytest.mark.parametrize("text,value,purpose,payer", [
    ("pay ₹2,000 for police clearance", 2000, "verification", "candidate"),       # FR-13 acceptance
    ("stipend ₹15,000/month", 15000, "stipend", "employer"),
    ("Pay Rs. 3,500/- for the joining kit", 3500, "equipment", "candidate"),
    ("Deposit Rs 5000 refundable security deposit via UPI", 5000, "deposit", "candidate"),
    ("CTC of Rs 4.5 lpa", 450000, "salary", "employer"),
    ("Registration fee Rs 499 (non-refundable) to x@paytm", 499, "registration", "candidate"),  # D-23
])
def test_amount_positive(text, value, purpose, payer):
    assert {k: one(text, "amount")[k] for k in ("value_inr", "purpose", "payer")} == \
        {"value_inr": value, "purpose": purpose, "payer": payer}


@pytest.mark.parametrize("text", ["Mrs. 5 kids", "Batch of 2026 starts in 12 months"])
def test_amount_negative(text):
    assert claims_of(text, "amount") == []


def test_amount_window_stops_at_sentence():  # D-23
    t = "Selected candidates get Rs 5,000 per month for 12 months. Register now. Registration fee Rs 499 to x@paytm"
    assert purpose_payer(t, t.index("Rs 499"), t.index("Rs 499") + 6)[0] == "registration"


@pytest.mark.parametrize("text,name,source", [
    ("Welcome to Infosys Limited", "Infosys", "dictionary"),                      # FR-11 acceptance
    ("Offer from TCS for freshers", "Tata Consultancy Services", "dictionary"),
    ("We at Nimbleleaf Analytics Pvt Ltd liked your resume.", "Nimbleleaf Analytics", "legal_line"),  # D-24
    ("Brightpath Technologies Pvt Ltd\nOffer letter", "Brightpath Technologies", "legal_line"),
    ("You are invited to join Quantasoft Labs as an intern", "Quantasoft Labs", "pattern"),
])
def test_org_positive(text, name, source):
    c = extract_claims(text).first("org")
    assert (c.value["name"], c.source) == (name, source)


@pytest.mark.parametrize("text", [
    "Fill the Google Form and pay via Paytm",          # product and payment-rail guards (D-31)
    "In reliance on your resume we write to you",      # lowercase brand word
    "Dear Team, regards from HR",
])
def test_org_negative(text):
    assert extract_claims(text).first("org") is None


@pytest.mark.parametrize("text,key", [
    ("PM Internship Scheme 2026", "pm_internship"),
    ("apply on the National Internship Portal", "aicte_internship"),
    ("Ministry of MSME internship form", "msme_internship"),
])
def test_scheme(text, key):
    assert one(text, "scheme") == {"scheme_key": key}


def test_scheme_negative():
    assert claims_of("Internship at Infosys", "scheme") == [] and claims_of("Skilled India", "scheme") == []


@pytest.mark.parametrize("text,name,title", [
    ("Regards,\nRitika Sharma\nHR Onboarding Executive", "Ritika Sharma", "HR Onboarding Executive"),
    ("Thanks\nVikram Menon\nTalent Partner", "Vikram Menon", "Talent Partner"),
    ("Best,\nA. Iyer\nRecruiter", "A. Iyer", "Recruiter"),
])
def test_hr_person(text, name, title):
    assert one(text, "hr_person") == {"name": name, "title": title}


@pytest.mark.parametrize("text", ["Regards,\nHR Team", "Thanks,\nKaran"])
def test_hr_person_negative(text):
    assert claims_of(text, "hr_person") == []


@pytest.mark.parametrize("text,city,pin", [
    ("Office: Plot 45, Sector 62, Noida 201309", "Noida", "201309"),
    ("Report to 3rd Floor, MG Road, Bengaluru - 560001", "Bengaluru", "560001"),
    ("at Infosys Limited, Mysuru.", "Mysuru", None),
])
def test_address(text, city, pin):
    v = one(text, "address")
    assert (v["city"], v["pincode"]) == (city, pin)


@pytest.mark.parametrize("text", ["Call 9876543210 now", "Thanks, Anand"])
def test_address_negative(text):
    assert claims_of(text, "address") == []


@pytest.mark.parametrize("text,title", [
    ("selected for the position of Data Analyst Intern at Acme", "Data Analyst Intern"),
    ("You are selected as a Business Development Intern (remote)", "Business Development Intern"),
    ("join us as an Associate", "Associate"),
])
def test_role(text, title):
    assert one(text, "role") == {"title": title}


@pytest.mark.parametrize("text", ["We are hiring.", "selected for the next round"])
def test_role_negative(text):
    assert claims_of(text, "role") == []


@pytest.mark.parametrize("text,hours", [("within 24 hours", 24), ("within 3 days", 72), ("Last date: today", 24),
                                        ("pay before 6 PM", 24)])
def test_deadline(text, hours):
    assert one(text, "deadline") == {"hours": hours}


@pytest.mark.parametrize("text", ["Joining in 2 months", "the day after"])
def test_deadline_negative(text):
    assert claims_of(text, "deadline") == []


@pytest.mark.parametrize("text,flag", [
    ("You are selected directly without interview", "no_interview"),
    ("Interview on WhatsApp at 5", "chat_only_interview"),
    ("Last date: today. Limited seats!", "urgent"),
    ("join our Telegram group", "telegram"),
])
def test_process(text, flag):
    assert one(text, "process")[flag] is True


@pytest.mark.parametrize("text", ["Interview on 5 Oct at our office", "Please read the offer"])
def test_process_negative(text):
    assert claims_of(text, "process") == []


@pytest.mark.parametrize("text,cin,gstin", [
    ("CIN: L45200MH1995PLC093713", "L45200MH1995PLC093713", None),
    ("GSTIN 27AAACT2727Q1ZW", None, "27AAACT2727Q1ZW"),
    ("CIN U72200KA2010PTC054321 GST 29AABCU9603R1ZM", "U72200KA2010PTC054321", "29AABCU9603R1ZM"),
])
def test_legal_id(text, cin, gstin):
    assert one(text, "legal_id") == {"cin": cin, "gstin": gstin}


@pytest.mark.parametrize("text", ["cin l45200mh1995plc093713", "GST 27AAACT2727"])
def test_legal_id_negative(text):
    assert claims_of(text, "legal_id") == []


# ---- redaction (FR-16) -----------------------------------------------------------------------------------------
def test_redact_recipient_and_ids():
    t, who = redact("Dear Priya Sharma,\nAadhaar 1234 5678 9012 PAN ABCDE1234F")
    assert who == "Priya Sharma" and "Priya" not in t and "<RECIPIENT>" in t and t.count("<ID>") == 2


def test_redact_mine():
    t, _ = redact("Mail priya.s@college.edu.in or call +91 90000 00001", mine_emails=["priya.s@college.edu.in"],
                  mine_phones=["+919000000001"])
    assert t == "Mail <RECIPIENT_EMAIL> or call <RECIPIENT_PHONE>"


def test_redact_keeps_placeholder():
    assert redact("Dear <RECIPIENT>,")[0] == "Dear <RECIPIENT>,"


# ---- golden extraction -----------------------------------------------------------------------------------------
def test_g1_claims():
    cs = extract_claims((GOLDEN / "g1.txt").read_text())
    assert cs.org_name == "Tech Mahindra"
    assert cs.first("sender_email").value["registrable_domain"] == "techmahindra-careers.in"
    fee = [c.value for c in cs.all("amount") if c.value["payer"] == "candidate"]
    assert fee == [{"value_inr": 2000, "purpose": "verification", "payer": "candidate", "raw": "Rs. 2,000"}]
    assert cs.first("upi_id").value["vpa"] == "techm.hr@ybl"
    assert cs.process["no_interview"] and cs.process["urgent"]
    assert cs.first("deadline").value == {"hours": 24}


def test_g2_g4_claims():
    g2 = extract_claims((GOLDEN / "g2.txt").read_text())
    assert g2.first("scheme").value["scheme_key"] == "pm_internship" and g2.first("url").value["kind"] == "form"
    g4 = extract_claims((GOLDEN / "g4.txt").read_text())
    assert g4.org_name == "Nimbleleaf Analytics" and g4.first("sender_email").value["registrable_domain"] == "gmail.com"
    assert g4.process["no_interview"] and not g4.all("upi_id")


def test_extraction_is_fast():  # NFR-02
    text = ((GOLDEN / "g1.txt").read_text() + "\n") * 40
    t = time.perf_counter()
    extract_claims(text[:20000])
    assert time.perf_counter() - t < 1.5


def test_claim_ids_stable():
    t = (GOLDEN / "g1.txt").read_text()
    assert [c.id for c in extract_claims(t).claims] == [c.id for c in extract_claims(t).claims]
