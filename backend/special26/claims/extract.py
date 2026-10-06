"""extract_claims(text, ...) -> ClaimSet (08 §2). Regex and dictionaries only, no network. FR-10, FR-11, FR-13."""
import re
from functools import lru_cache

from special26 import seeds
from special26.claims import amounts, org
from special26.claims.models import Claim, ClaimSet
from special26.claims.models import ClaimType as T
from special26.claims.regexes import (
    AMOUNT,
    BARE_DOMAIN,
    CIN,
    EMAIL,
    GSTIN,
    PHONE_IN,
    PIN,
    UPI,
    UPI_URI,
    URL,
    amount_value,
    flat,
    norm_phone,
    overlaps,
    strip_url,
    word_rx,
)
from special26.domains.classify import host_of, platform_kind, reg

TOKEN = re.compile(r"\S+")
FROM_LINE = re.compile(r"\bfrom\s*:", re.IGNORECASE)
REGARDS = re.compile(r"\b(?:regards|thanks|thank you|sincerely)\b", re.IGNORECASE)
REPLY = re.compile(rf"(?:reply(?:\s+back)?\s+to|send\s+(?:your\s+|all\s+|the\s+)?[^.\n]{{0,60}}?\s+to)\s*:?\s*({EMAIL.pattern})",
                   re.IGNORECASE)
ROLE_1 = re.compile(r"selected for the (?:position|role|post) of\s+(?:an?\s+)?([A-Z][\w&/\-]*(?:[ \t]+[A-Z][\w&/\-]*){0,6})")
_ROLE_WORDS = r"([A-Z][\w&/\-]*(?:[ \t]+[A-Z][\w&/\-]*){0,6})"
ROLE_3 = re.compile(rf"(?:offer you the|for the|interview for(?: the)?)[ \t]+(?:position|role|post)[ \t]+of[ \t]+"
                    rf"(?:an?[ \t]+)?{_ROLE_WORDS}")                                                       # D-51
ROLE_4 = re.compile(rf"(?:applying for|application for|regarding|interview for|clearing the interview for|offer you the)"
                    rf"[ \t]+(?:the[ \t]+)?{_ROLE_WORDS}(?=[ \t]+(?:role|position|opening|with|at)\b|[ \t]*\()")
ROLE_2 = re.compile(r"\bas an?\s+((?:[A-Z][\w&/\-]*[ \t]+){0,5}(?:Intern|Trainee|Engineer|Analyst|Executive|Associate))\b")
DEADLINE_HOURS = re.compile(r"within\s+(\d{1,3})\s*(?:hours?|hrs?)\b", re.IGNORECASE)
DEADLINE_DAYS = re.compile(r"within\s+(\d{1,2})\s*days?\b", re.IGNORECASE)
DEADLINE_TODAY = re.compile(r"\b(?:today|by tonight|tonight|eod|end of (?:the )?day|before\s+\d{1,2}(?::\d{2})?\s*[ap]\.?m)\b",
                            re.IGNORECASE)
ADDR_LEAD = re.compile(r"^(?:(?:at|in|for|our|from|of|the|based|located|office)\s+)+", re.IGNORECASE)
NAME_LINE = re.compile(r"^[A-Z][a-zA-Z.'\-]+(?:[ \t]+[A-Z][a-zA-Z.'\-]+){0,3}$")


@lru_cache
def _city_rx() -> re.Pattern:
    cities = sorted(seeds.lines("cities.txt"), key=len, reverse=True)
    return re.compile(r"(?<![\w-])(" + "|".join(re.escape(c) for c in cities) + r")(?![\w-])")


def _near(text: str, start: int, end: int, rx: re.Pattern, n: int) -> bool:
    before = " ".join(TOKEN.findall(text[:start])[-n:])
    after = " ".join(TOKEN.findall(text[end:])[:n])
    return bool(rx.search(f"{before} {after}".lower()))


def _line_bounds(text: str, pos: int) -> tuple[int, int]:
    lo = text.rfind("\n", 0, pos) + 1
    hi = text.find("\n", pos)
    return lo, (len(text) if hi < 0 else hi)


def extract_claims(text: str, eml: dict | None = None, images: list[tuple[int, str]] = ()) -> ClaimSet:
    """text is already redacted (spans index it). eml: parsed headers from intake.eml. images: (artifact_id, role)."""
    lex = seeds.lexicons()
    claims: list[Claim] = []
    add = claims.append

    # ---- emails, urls --------------------------------------------------------------------------------------
    emails = [(m.group(), m.span()) for m in EMAIL.finditer(text)]
    email_spans = [s for _, s in emails]
    url_hits: list[tuple[str, tuple[int, int]]] = []
    for rx in (UPI_URI, URL):
        for m in rx.finditer(text):
            u = strip_url(m.group())
            span = (m.start(), m.start() + len(u))
            if not overlaps(span, email_spans) and not overlaps(span, [s for _, s in url_hits]):
                url_hits.append((u, span))
    for m in BARE_DOMAIN.finditer(text):
        if not overlaps(m.span(), email_spans + [s for _, s in url_hits]):
            url_hits.append((m.group(), m.span()))
    for u, span in sorted(url_hits, key=lambda x: x[1]):
        host = "" if u.lower().startswith("upi:") else host_of(u)
        add(Claim.make(T.url, {"url": u, "host": host or None, "registrable_domain": reg(host) if host else None,
                               "kind": platform_kind(u) or "other"}, u, "regex", 0.9, span))

    # ---- sender, reply-to ----------------------------------------------------------------------------------
    sender = None
    if eml and eml.get("from_address"):
        a = eml["from_address"]
        add(Claim.make(T.sender_email, {"address": a, "display_name": eml.get("from_display"),
                                        "registrable_domain": reg(a.split("@")[1]), "from_headers": True},
                       a, "eml_header", 1.0))
        sender = a
    else:
        sig_start = sum(len(ln) + 1 for ln in text.splitlines()[:-12]) if text.count("\n") >= 12 else 0
        anchors = [m.end() for m in FROM_LINE.finditer(text)] + [m.end() for m in REGARDS.finditer(text)]
        pick = next(((a, s) for a, s in emails if any(s[0] >= x and text.count("\n", x, s[0]) <= 4 for x in anchors)),
                    None) or next(((a, s) for a, s in emails if s[0] >= sig_start), None)
        if pick:
            a, s = pick
            add(Claim.make(T.sender_email, {"address": a, "display_name": None,
                                            "registrable_domain": reg(a.split("@")[1]), "from_headers": False},
                           a, "regex", 0.9, s))
            sender = a
    if eml and eml.get("reply_to"):
        a = eml["reply_to"]
        add(Claim.make(T.reply_to, {"address": a, "registrable_domain": reg(a.split("@")[1])}, a, "eml_header", 1.0))
    else:
        m = REPLY.search(text)
        if m and m.group(1).lower() != (sender or "").lower():
            add(Claim.make(T.reply_to, {"address": m.group(1), "registrable_domain": reg(m.group(1).split("@")[1])},
                           m.group(1), "regex", 0.85, m.span(1)))

    # ---- phones --------------------------------------------------------------------------------------------
    sender_rx = word_rx(lex["phone_sender_words"])
    seen = set()
    for m in PHONE_IN.finditer(text):
        e164 = norm_phone(m.group(1), m.group(2))
        if e164 in seen:
            continue
        seen.add(e164)
        role = "sender" if _near(text, m.start(), m.end(), sender_rx, 6) else "unknown"
        add(Claim.make(T.phone, {"e164": e164, "role": role}, m.group().strip(), "regex", 0.9, m.span()))

    # ---- UPI -----------------------------------------------------------------------------------------------
    known = set(lex["known_upi_handles"])
    ctx_rx = word_rx(lex["upi_context_words"])
    seen = set()
    for m in UPI.finditer(text):
        if overlaps(m.span(), email_spans):                                  # D-24
            continue
        vpa, handle = m.group().lower(), m.group(2).lower()
        handle_known = handle in known
        if vpa in seen or not (handle_known or _near(text, m.start(), m.end(), ctx_rx, 8)):
            continue
        seen.add(vpa)
        add(Claim.make(T.upi_id, {"vpa": vpa, "handle": handle, "handle_known": handle_known}, m.group(), "regex",
                       0.95 if handle_known else 0.7, m.span()))

    # ---- amounts and stipend -------------------------------------------------------------------------------
    for m in AMOUNT.finditer(text):
        value = amount_value(m)
        purpose, payer, _ = amounts.classify(text, m.start(), m.end())
        add(Claim.make(T.amount, {"value_inr": value, "purpose": purpose, "payer": payer, "raw": m.group()},
                       m.group(), "regex", 0.85, m.span()))
        if purpose in ("stipend", "salary"):
            w = amounts.window(text, m.start(), m.end())
            period = "year" if re.search(r"annum|lpa|ctc|per year|yearly", w) else "month"
            add(Claim.make(T.stipend, {"value_inr": value, "period": period}, m.group(), "regex", 0.8, m.span()))

    # ---- organisation and schemes --------------------------------------------------------------------------
    hit = org.by_dictionary(text)
    if hit:
        e, s, t = hit
        add(Claim.make(T.org, {"name": e["name"], "legal_suffix": org.trailing_legal(text, t) or org.ending_legal(text[s:t]),
                               "entity_id": e["entity_id"]}, text[s:t], "dictionary", 0.95, (s, t)))
    elif ll := org.by_legal_line(text):
        name, legal, span = ll
        add(Claim.make(T.org, {"name": name, "legal_suffix": legal, "entity_id": None}, name, "legal_line", 0.8, span))
    elif pt := org.by_pattern(text):
        name, span = pt
        add(Claim.make(T.org, {"name": name, "legal_suffix": None, "entity_id": None}, name, "pattern", 0.6, span))
    elif eml and (dn := org.by_display_name(eml.get("from_display"))):
        add(Claim.make(T.org, {"name": dn, "legal_suffix": None, "entity_id": None}, dn, "display_name", 0.6))
    for e, s, t in org.schemes(text):
        add(Claim.make(T.scheme, {"scheme_key": e["scheme_key"]}, text[s:t], "dictionary", 0.95, (s, t)))

    # ---- HR person (signature block) -----------------------------------------------------------------------
    lines = text.splitlines()
    title_rx = re.compile(r"\b(?:" + "|".join(lex["hr_title_words"]) + r")\b")
    stop = {w.lower() for w in lex["org_stop_words"]} | {"regards", "thanks", "sincerely", "warm regards"}
    for i in range(max(1, len(lines) - 12), len(lines)):
        cand, title = lines[i - 1].strip(), lines[i].strip()
        if title_rx.search(title) and NAME_LINE.match(cand) and cand.lower().rstrip(",") not in stop \
                and not any(w.lower() in stop for w in cand.split()[:1]):
            pos = text.find(cand)
            add(Claim.make(T.hr_person, {"name": cand, "title": title}, cand, "pattern", 0.7,
                           (pos, pos + len(cand)) if pos >= 0 else None))
            break

    # ---- address -------------------------------------------------------------------------------------------
    addr = None
    for m in PIN.finditer(text):
        lo, hi = _line_bounds(text, m.start())
        if not overlaps(m.span(), [c.span for c in claims if c.span and c.type in (T.phone, T.amount)]):
            cities = _city_rx().findall(text, lo, hi)          # last one: "Sector 62, Noida 201309" -> Noida
            addr = (text[lo:hi].strip(), cities[-1] if cities else None, m.group(), (lo, hi))
            break
    if addr is None and (cm := _city_rx().search(text)):
        lo, _ = _line_bounds(text, cm.start())
        # D-31: the clause ending at the city ("Infosys Limited, Mysuru"), without leading prepositions
        seg_start = max([lo] + [text.rfind(ch, lo, cm.start()) + 1 for ch in ".!?(:;"])
        seg = ADDR_LEAD.sub("", text[seg_start:cm.end()].strip(" ,"))
        parts = [p.strip() for p in seg.split(",")]
        if len(parts) > 1:                  # D-51: keep only the capitalised name before the city: "Wipro, Pune"
            name = re.search(r"((?:[A-Z][\w&.\-]*[ \t]*)+)$", parts[-2])
            seg = f"{name.group(1).strip()}, {parts[-1]}" if name else parts[-1]
        else:
            seg = cm.group()                # a city inside a sentence is just the city
        seg_start = cm.end() - len(seg)
        addr = (seg, cm.group(), None, (seg_start, cm.end()))
    if addr:
        raw, city, pin, span = addr
        add(Claim.make(T.address, {"raw": raw, "city": city, "pincode": pin}, raw, "pattern", 0.7, span))

    # ---- role ----------------------------------------------------------------------------------------------
    for rx in (ROLE_1, ROLE_2, ROLE_3, ROLE_4):
        if m := rx.search(text):
            title = re.sub(r"[ \t]+(?:at|with|in|for)$", "", m.group(1).strip())
            add(Claim.make(T.role, {"title": title}, title, "pattern", 0.7, m.span(1)))
            break

    # ---- deadline, process ---------------------------------------------------------------------------------
    hours = [int(m.group(1)) for m in DEADLINE_HOURS.finditer(text)]
    hours += [int(m.group(1)) * 24 for m in DEADLINE_DAYS.finditer(text)]
    hours += [24 for _ in DEADLINE_TODAY.finditer(text)]
    if hours:
        add(Claim.make(T.deadline, {"hours": min(hours)}, f"{min(hours)} hours", "regex", 0.8))
    ft = f" {flat(text)} "
    p = lex["process"]
    flags = {k: any(f" {flat(ph)} " in ft for ph in p[k]) for k in ("no_interview", "chat_only_interview",
                                                                     "telegram", "whatsapp")}
    flags["urgent"] = bool(hours and min(hours) <= 48) or any(f" {flat(ph)} " in ft for ph in p["urgent"])
    if any(flags.values()):
        add(Claim.make(T.process, flags, ", ".join(k for k, v in flags.items() if v), "regex", 0.8))

    # ---- legal ids, images ---------------------------------------------------------------------------------
    cin, gst = CIN.search(text), GSTIN.search(text)
    if cin or gst:
        add(Claim.make(T.legal_id, {"cin": cin.group() if cin else None, "gstin": gst.group() if gst else None},
                       (cin or gst).group(), "regex", 0.9))
    for artifact_id, role in images:
        add(Claim.make(T.image, {"artifact_id": artifact_id, "role": role}, f"{role}:{artifact_id}", "regex", 1.0))

    return ClaimSet(claims=claims, warnings=[])
