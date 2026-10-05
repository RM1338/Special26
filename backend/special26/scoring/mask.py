"""Masking for public pages and reason text (03 §4.3, D-20). Fixed widths so length is not leaked."""
import re


def mask_upi(vpa: str) -> str:
    user, _, handle = vpa.partition("@")
    return f"{user[:2]}****@{handle}"


def mask_email(addr: str) -> str:
    user, _, domain = addr.partition("@")
    return f"{user[:1]}***@{domain}"


def mask_phone(e164: str) -> str:
    digits = re.sub(r"\D", "", e164)
    return f"+91 ******{digits[-4:]}"


def mask_text(text: str | None) -> str | None:
    """Mask emails, UPI IDs and Indian phone numbers inside free text (receipt snippets)."""
    if not text:
        return text
    from special26.claims.regexes import EMAIL, PHONE_IN, UPI
    text = EMAIL.sub(lambda m: mask_email(m.group()), text)
    text = UPI.sub(lambda m: m.group() if "***" in m.group() else mask_upi(m.group()), text)
    return PHONE_IN.sub(lambda m: mask_phone(m.group(1) + m.group(2)), text)
