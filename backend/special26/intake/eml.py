"""Parse .eml (FR-06): From, Reply-To, Return-Path, Subject, Date, Authentication-Results, body."""
import html
import re
from email import policy
from email.parser import BytesParser
from email.utils import getaddresses, parseaddr

AUTH_KV = re.compile(r"\b(dkim|spf|dmarc)\s*=\s*(\w+)([^;]*)", re.IGNORECASE)
PROP = re.compile(r"\b(header\.d|header\.i|smtp\.mailfrom|header\.from)\s*=\s*([^\s;()]+)", re.IGNORECASE)


def _strip_html(s: str) -> str:
    s = re.sub(r"(?is)<(script|style).*?</\1>", " ", s)
    s = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</tr>", "\n", s)
    return html.unescape(re.sub(r"<[^>]+>", " ", s))


def parse_auth(header: str) -> dict:
    """'dkim=pass header.d=x.com; spf=pass smtp.mailfrom=...; dmarc=pass header.from=x.com' -> dict."""
    out = {}
    for m in AUTH_KV.finditer(header):
        kind = m.group(1).lower()
        if kind in out:
            continue
        props = {k.lower(): v.strip(".").lower() for k, v in PROP.findall(m.group(3))}
        out[kind] = {"result": m.group(2).lower(), **props}
    return out


def parse_eml(raw: bytes) -> dict:
    msg = BytesParser(policy=policy.default).parsebytes(raw)
    display, addr = parseaddr(str(msg.get("From", "")))
    reply = getaddresses([str(msg.get("Reply-To", ""))])
    body_part = msg.get_body(preferencelist=("plain", "html"))
    body = ""
    if body_part is not None:
        body = body_part.get_content()
        if body_part.get_content_type() == "text/html":
            body = _strip_html(body)
    auth = [str(h) for h in msg.get_all("Authentication-Results", [])]   # topmost first = recipient's provider
    attachments = [(p.get_filename() or "", p.get_content_type(), p.get_payload(decode=True) or b"")
                   for p in msg.iter_attachments()]
    return {
        "from_address": addr.lower() or None,
        "from_display": display or None,
        "reply_to": (reply[0][1].lower() or None) if reply else None,
        "return_path": parseaddr(str(msg.get("Return-Path", "")))[1].lower() or None,
        "subject": str(msg.get("Subject", "")),
        "date": str(msg.get("Date", "")),
        "auth_results": auth,
        "auth": parse_auth(auth[0]) if auth else {},
        "body": body.strip(),
        "attachments": attachments,
    }
