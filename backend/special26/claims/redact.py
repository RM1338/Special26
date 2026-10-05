"""Redaction before storage (03 §4.2). FR-16."""
import re

GREETING = re.compile(r"\b(Dear|Hi|Hello|Congratulations)\b[ \t]+(?!<)([^\W\d_][^,.!?:;\n<]{0,40}?)(?=\s*[,.!?:;\n])")
AADHAAR = re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")
PAN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")


def redact(text: str, mine_emails=(), mine_phones=()) -> tuple[str, str | None]:
    """Returns (redacted_text, recipient_name). Rules 1 and 3 always; rule 2 for 'This is mine' items."""
    recipient = None
    m = GREETING.search(text)
    if m:
        recipient = m.group(2).strip()
        text = text[:m.start(2)] + "<RECIPIENT>" + text[m.end(2):]
    text = AADHAAR.sub("<ID>", text)
    text = PAN.sub("<ID>", text)
    for e in mine_emails:
        text = re.sub(re.escape(e), "<RECIPIENT_EMAIL>", text, flags=re.IGNORECASE)
    for p in mine_phones:
        digits = re.sub(r"\D", "", p)[-10:]
        if len(digits) == 10:
            # tolerate spaces/dashes and a +91/91/0 prefix in the original text
            loose = r"[\s\-]?".join(digits)
            text = re.sub(rf"(?:\+?91[\s\-]?|0)?{loose}(?!\d)", "<RECIPIENT_PHONE>", text)
    return text, recipient
