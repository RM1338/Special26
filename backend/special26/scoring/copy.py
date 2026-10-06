"""Reason copy per finding code, decisive rule and rule receipt (D-01), plus 09 headlines.

Rules (09 §4): name the evidence source; never "scam", "fraudster", "fake company", "safe", "guaranteed", "100%";
"fraud" only when quoting a source's own notice; amounts as ₹2,000; identifiers masked; no em dashes.
"""

COPY = {
    "P01_OFFICIAL_FOUND": "Google Search shows {org}'s official website is {official}.",
    "P01_NO_PRESENCE": "Google Search found no official website for {org}.",
    "P02_SENDER_OFFICIAL": "The sender uses {org}'s own domain {domain}. A pasted sender line is not proof on its own.",
    "P02_HOMOGLYPH": "The {what} {domain} imitates {org}'s domain {official} with lookalike characters.",
    "P02_TYPOSQUAT": "The {what} {domain} is a misspelling of {org}'s domain. {org} uses {official}.",
    "P02_COMBOSQUAT": "The {what} {domain} is not {org}'s. {org} uses {official}.",
    "P02_TLD_SWAP": "The {what} {domain} copies {org}'s name with a different ending. {org} uses {official}.",
    "P02_FREEMAIL": "The offer comes from a personal {provider} address, not {org}'s domain {official}.",
    "P02_FREEMAIL_NO_PRESENCE": "The offer comes from a personal {provider} address, and Google Search found no "
                                "website for {org}.",
    "P02_UNRELATED": "Google Search does not link the sender domain {domain} to {org}.",
    "P02_REPLY_DIVERTED": "Replies go to {reply}, a different address from the sender.",
    "P03_DKIM_ALIGNED_OFFICIAL": "The email passed authentication (DKIM) for {org}'s domain {domain}.",
    "P03_AUTH_FAIL": "The email failed its authentication checks ({detail}).",
    "P03_REPLY_DIVERTED": "The email's Reply-To header sends replies to {reply}, not to the sender's domain.",
    "P04_NOTICE_FOUND": "{org} has published a recruitment fraud notice on its own website.",
    "P05_COMPLAINTS_GENERAL": "{n} news and forum results report fake offers that use {org}'s name.",
    "P05_COMPLAINT_NAMES_SENDER": "A public complaint on {source} names {identifier} from this offer.",
    "P05_PIB_FACTCHECK": "PIB Fact Check has published a warning about offers using this scheme's name.",
    "P06_ID_REPORTED": "{identifier} from this offer appears in a public warning on {source}.",
    "P06_ID_ON_OFFICIAL": "{identifier} appears on {org}'s official website.",
    "P06_ID_SEEN_LOCALLY": "{identifier} appeared in {count_text} marked high risk.",
    "P07_ROLE_LISTED": "Google Jobs lists a {role} role at {org}.",
    "P07_COMPANY_LISTS_OTHER_ROLES": "Google Jobs lists roles at {org}, but none like {role}.",
    "P08_OFFICE_MATCH": "Google Maps shows {org}'s office at this location.",
    "P08_RESIDENTIAL": "Google Maps shows the office address as a {place_type}, not a company office.",
    "P08_COWORKING": "Google Maps shows the office address as a {place_type}.",
    "P08_NOT_FOUND": "Google Maps could not find the office address given in the offer.",
    "P08_REVIEWS_SCAM": "Google Maps reviews of this place warn people about job offers.",
    "P09_STOCK_PHOTO": "Google Lens finds the HR photo on the stock photo site {source}.",
    "P09_PHOTO_OTHER_NAMES": "Google Lens finds the HR photo on {n} other websites under other people's names.",
    "P09_PHOTO_OFFICIAL": "Google Lens finds the HR photo on {source} with the name {name}.",
    "P09_LETTER_REPORTED": "Google Lens finds this letter image in a public warning on {source}.",
    "P10_TEMPLATE_MATCH_HIGH": "This offer's wording closely matches a known fake offer text.",
    "P10_TEMPLATE_MATCH_MED": "This offer's wording partly matches a known fake offer text.",
    "P10_PHRASE_REPORTED": "Google Search finds a sentence from this offer in a public warning on {source}.",
    "P10_PHRASE_OFFICIAL": "Google Search finds a sentence from this offer on {org}'s official website.",
    "P11_CANDIDATE_PAYS": "The offer asks you to pay {amount} for {purpose}. Genuine employers do not charge "
                          "candidates.",
    "P11_REFUNDABLE_BAIT": "The payment is called refundable, a common way to make a fee look harmless.",
    "P11_PERSONAL_UPI": "You are asked to pay {target}{deadline}.",
    "P11_SCHEME_OFF_PORTAL": "{scheme} runs only on {portal}. This offer uses {where}.",
    "P11_FORM_OR_SHORTLINK": "The application goes through a {kind} ({host}), not an official careers site.",
    "P11_URGENCY": "The offer pushes you to act {when}.",
    "P11_NO_INTERVIEW": "The offer says you were selected without an interview.",
    "P11_CHAT_INTERVIEW": "The offer says the interview happens only over chat.",
    "P12_VERY_NEW": "The domain {domain} was registered {days} days ago.",
    "P12_NEW": "The domain {domain} was registered {days} days ago.",
}

DECISIVE_COPY = {
    "D1_FEE_VS_NOTICE": "{org}'s own recruitment fraud notice says it never charges candidates. This offer asks for "
                        "{amount}.",
    "D2_SCHEME_IMPERSONATION": "{scheme} runs only on {portal} and does not charge. This offer uses {where}{ask}.",
    "D3_LOOKALIKE_PLUS_FEE": "{lookalike_message}",          # 08 §6.1: the lookalike finding's own sentence
    "D4_IDENTIFIER_REPORTED": "{identifier} from this offer is already reported on {n} different websites.",
}

# Shown in the receipt drawer for kind = "rule" (09 S5)
RULE_COPY = {   # plain language, no internal codes (D-57)
    "P02_SENDER": "We compared the domains in the offer with the official websites Google Search shows for the "
                  "company.",
    "P11_CANDIDATE_PAYS": "Real employers do not charge candidates for a job or internship. AICTE's internship portal "
                          "terms forbid any fee.",
    "P11_REFUNDABLE_BAIT": "Calling a payment refundable is a common way to make a fee feel harmless. Real employers do "
                           "not take deposits from candidates.",
    "P11_PERSONAL_UPI": "Companies do not collect money through personal UPI IDs, payment links or QR codes sent in a "
                        "message.",
    "P11_SCHEME_OFF_PORTAL": "Government internship schemes run only on official .gov.in or .nic.in portals and their "
                             "listed websites.",
    "P11_FORM_OR_SHORTLINK": "Real hiring happens on the employer's own careers website, not through online forms, "
                             "short links or chat links.",
    "P11_URGENCY": "A very short deadline is meant to make you pay before you can check. Real offers give you time.",
    "P11_NO_INTERVIEW": "Real employers interview candidates before they make an offer.",
    "P11_CHAT_INTERVIEW": "Interviews held only over WhatsApp or Telegram chat are a common sign of a fake offer.",
    "P03_HEADERS": "Your email provider records whether a message really came from the domain it claims. We read that "
                   "record from the .eml file.",
    "P10_TEMPLATE": "We compare the offer's wording with fake offer texts described in public reports.",
}

HEADLINES = {   # 09 S4, exact
    ("red", "impersonation"): "Strong signs of impersonation. Do not pay.",
    ("red", "fee_risk"): "High risk: this offer asks you to pay. Do not pay.",
    ("amber", None): "Could not verify this offer. Confirm through the official channel before you share documents "
                     "or pay.",
    ("amber", "minor"): "No serious warning signs, but this offer is not fully confirmed.",   # D-54
    ("green", None): "Consistent with a genuine offer from {org}.",
    ("grey", None): "Not enough information to judge.",
}
SUBLINES = {
    ("red", "impersonation"): "This offer claims to be from {org}, but the evidence below says otherwise.",
    ("red", "fee_risk"): "Genuine employers and government internship schemes do not charge candidates.",
    ("amber", None): "Some details could not be matched to {org}.",
    ("amber", "minor"): "Some details matched {org}, others could not be checked. Confirm through "
                        "{official_contact} before you share ID documents.",
    ("green", None): "Still confirm through {official_contact} before you share ID documents.",
    ("grey", None): "Add the sender's email, the full offer text, or the original .eml file.",
}


def inr(value: float) -> str:
    """Indian digit grouping: 150000 -> ₹1,50,000."""
    s = str(round(value))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        s = ",".join(([head] if head else []) + groups + [tail])
    return f"₹{s}"


def render(template: str, **vars) -> str:
    return template.format(**vars)            # a missing variable raises: caught by the per-code copy tests
