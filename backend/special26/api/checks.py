"""POST/GET/PUT/run/events for checks (07 §2 to §5). FR-01 to FR-03, FR-14, FR-15, FR-40, NFR-07."""
import asyncio
import base64
import hashlib
import json
import os
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse, ServerSentEvent

from special26.claims import amounts, org
from special26.claims.extract import extract_claims
from special26.claims.models import Claim, ClaimSet, ClaimType
from special26.claims.redact import redact
from special26.domains.classify import host_of, platform_kind, reg
from special26.errors import (
    BadRequest,
    BudgetExhausted,
    ConflictState,
    Expired,
    NotFound,
    RateLimited,
    ValidationError,
)
from special26.intake.ingest import Upload, ingest, validate
from special26.pipeline.runner import TERMINAL, run_check
from special26.scoring.aggregate import strength
from special26.scoring.mask import mask_email, mask_phone, mask_text, mask_upi
from special26.scoring.nextsteps import headline, next_steps
from special26.storage.repo import iso, now

router = APIRouter(prefix="/api")
MAX_TEXT = 20_000
IDLE = timedelta(minutes=30)


def new_check_id() -> str:
    return "chk_" + base64.b32encode(os.urandom(8)).decode().lower()[:12]


def _ip_hash(request: Request, salt: str) -> str:
    ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (request.client.host if request.client
                                                                               else "")
    return hashlib.sha256(f"{ip}|{salt}|{iso(now())[:10]}".encode()).hexdigest()


def _rate_limit(state, request: Request) -> str | None:
    s = state.settings
    ip_hash = _ip_hash(request, s.share_salt)
    if s.mode != "live":
        return ip_hash
    count, oldest = state.repo.count_checks_from_ip(ip_hash, now() - timedelta(hours=1))
    if count >= s.rate_limit_per_hour:
        retry = int((datetime.fromisoformat(oldest) + timedelta(hours=1) - now())
                    .total_seconds()) + 1
        raise RateLimited(f"Too many checks from this connection. Try again in {max(1, retry // 60)} minutes.",
                          {"retry_after": max(1, retry)})
    return ip_hash


def _daily_cap(state) -> None:
    s = state.settings
    if s.mode == "live" and state.repo.credits_today() >= s.daily_credit_cap:
        raise BudgetExhausted("We've hit today's search limit. Try again after 5:30 AM IST, or use the demo examples.",
                              {"cap": s.daily_credit_cap})


def _claim_json(c: Claim) -> dict:
    return {"id": c.id, "type": c.type.value, "value": c.value, "raw": c.raw, "source": c.source,
            "confidence": c.confidence}


def _created_view(state, check_id: str, status_code: int = 201) -> JSONResponse:
    check = state.repo.get_check(check_id)
    body = {"check_id": check_id, "status": check["status"], "mode": check["mode"],
            "claims": [_claim_json(c) for c in state.repo.claims(check_id)], "warnings": check["warnings"],
            "links": {"self": f"/api/checks/{check_id}", "events": f"/api/checks/{check_id}/events"}}
    return JSONResponse(body, status_code=status_code)


def _load(state, check_id: str, for_update: bool = False) -> dict:
    check = state.repo.get_check(check_id)
    if check is None:
        raise NotFound("This check does not exist.")
    if for_update and check["status"] == "awaiting_confirmation":
        idle = now() - datetime.fromisoformat(check["updated_at"])
        if idle > IDLE:
            state.repo.update_check(check_id, status="expired")
            state.repo.purge_raw(check_id)
            check["status"] = "expired"
    if for_update and check["status"] == "expired":
        raise Expired("This check expired. Start again, it only takes a minute.")
    return check


def _start(state, check_id: str) -> None:
    state.repo.update_check(check_id, status="running")
    state.tasks.add(t := asyncio.create_task(run_check(state, check_id)))
    t.add_done_callback(state.tasks.discard)


# ---- POST /api/checks -------------------------------------------------------------------------------------------
@router.post("/checks")
async def create_check(request: Request, text: Annotated[str | None, Form()] = None,
                       files: Annotated[list[UploadFile] | None, File()] = None,
                       file_roles: Annotated[str | None, Form()] = None, auto_run: Annotated[bool, Form()] = False):
    state = request.app.state.s26
    uploads = [Upload(f.filename or "", f.content_type or "", await f.read()) for f in (files or []) if f.filename]
    if not (text or "").strip() and not uploads:
        raise BadRequest("Paste the offer text or upload a file.")
    if text and len(text) > MAX_TEXT:                                                          # FR-01
        raise ValidationError(f"text is longer than {MAX_TEXT} characters", {"field": "text", "max": MAX_TEXT})
    try:
        roles = json.loads(file_roles) if file_roles else None
        assert roles is None or isinstance(roles, list)
    except (ValueError, AssertionError):
        raise ValidationError("file_roles must be a JSON array", {"field": "file_roles"}) from None
    checked = validate(uploads, roles)                                                          # FR-02, FR-03
    ip_hash = _rate_limit(state, request)
    if auto_run:
        _daily_cap(state)

    repo, events = state.repo, state.events
    check_id = new_check_id()
    repo.create_check(check_id, state.settings.mode, ip_hash, "", "", auto_run, [])
    repo.update_check(check_id, status="extracting")
    events.publish(check_id, "check.extracting", {})
    got = ingest(repo, check_id, checked, state.settings.uploads_dir)
    raw = "\n\n".join(p for p in [text or "", *got.text_parts] if p.strip())
    redacted, _ = redact(raw)
    claims = extract_claims(redacted, eml=got.eml, images=got.images)
    repo.save_claims(check_id, claims.claims)
    repo.update_check(check_id, raw_text=raw, redacted_text=redacted, warnings=got.warnings,
                      status="awaiting_confirmation")
    events.publish(check_id, "claims.ready", {"claim_count": len(claims.claims), "warnings": got.warnings})
    if auto_run:
        _start(state, check_id)
    return _created_view(state, check_id)


# ---- PUT /api/checks/{id}/claims --------------------------------------------------------------------------------
class ClaimIn(BaseModel):
    id: str | None = None
    type: ClaimType
    value: dict


class Mine(BaseModel):
    phones: list[str] = []
    emails: list[str] = []


class ClaimsIn(BaseModel):
    claims: list[ClaimIn]
    mine: Mine = Mine()
    org_unknown: bool = False


def _derive(c: ClaimIn, old: Claim | None) -> dict:
    """Recompute derived fields; purpose/payer only when the client omits them (D-15)."""
    v = {**(old.value if old else {}), **c.value}
    t = c.type
    if t in (ClaimType.sender_email, ClaimType.reply_to) and v.get("address"):
        v["address"] = v["address"].strip().lower()
        v["registrable_domain"] = reg(v["address"].split("@")[-1])
        if t == ClaimType.sender_email:
            v.setdefault("display_name", None)
            v.setdefault("from_headers", False)
    elif t == ClaimType.url and v.get("url"):
        h = host_of(v["url"])
        v.update(host=h or None, registrable_domain=reg(h) if h else None, kind=platform_kind(v["url"]) or "other")
    elif t == ClaimType.phone and v.get("e164"):
        digits = "".join(ch for ch in v["e164"] if ch.isdigit())[-10:]
        v["e164"] = "+91" + digits
        v.setdefault("role", "unknown")
    elif t == ClaimType.upi_id and v.get("vpa"):
        v["vpa"] = v["vpa"].strip().lower()
        v["handle"] = v["vpa"].split("@")[-1]
    elif t == ClaimType.amount:
        if "purpose" not in c.value or "payer" not in c.value:
            raw = str(v.get("raw") or v.get("value_inr") or "")
            purpose, payer, _ = amounts.classify(raw, 0, len(raw)) if raw else (None, "employer", "")
            v.setdefault("purpose", purpose)
            v.setdefault("payer", payer)
    elif t == ClaimType.org and v.get("name"):
        hit = org.by_dictionary(v["name"])
        v["entity_id"] = hit[0]["entity_id"] if hit else None
        if hit:
            v["name"] = hit[0]["name"]
        v.setdefault("legal_suffix", None)
    return v


@router.put("/checks/{check_id}/claims")
async def put_claims(check_id: str, body: ClaimsIn, request: Request):
    state = request.app.state.s26
    check = _load(state, check_id, for_update=True)
    if check["status"] != "awaiting_confirmation":
        raise ConflictState("Claims can only be edited before the checks run.")
    old = {c.id: c for c in state.repo.claims(check_id)}
    mine_phones = {"+91" + "".join(ch for ch in p if ch.isdigit())[-10:] for p in body.mine.phones}
    mine_emails = {e.strip().lower() for e in body.mine.emails}
    out: list[Claim] = []
    for c in body.claims:
        prev = old.get(c.id) if c.id else None
        if c.id and prev is None:
            raise ValidationError(f"unknown claim id {c.id}", {"field": "claims.id"})
        if prev is not None and prev.type != c.type:
            raise ValidationError("a claim's type cannot change", {"field": "claims.type"})
        v = _derive(c, prev)
        if c.type in (ClaimType.sender_email, ClaimType.reply_to) and v.get("address") in mine_emails:
            continue                                                                         # D-09
        if c.type == ClaimType.phone and v.get("e164") in mine_phones:
            v["role"] = "recipient"
        if body.org_unknown and c.type == ClaimType.org:
            continue
        if prev is not None and v == prev.value:
            out.append(prev)
        else:
            raw = prev.raw if prev else str(next(iter(v.values()), ""))
            made = Claim.make(c.type, v, raw, "user", 1.0)
            out.append(made.model_copy(update={"id": prev.id}) if prev else made)
    state.repo.save_claims(check_id, out)
    warnings = [w for w in check["warnings"] if w != "ORG_UNKNOWN"] + (["ORG_UNKNOWN"] if body.org_unknown else [])
    redacted, _ = redact(check["redacted_text"] or "", mine_emails=mine_emails, mine_phones=mine_phones)
    raw, _ = redact(check["raw_text"] or "", mine_emails=mine_emails, mine_phones=mine_phones)
    state.repo.update_check(check_id, warnings=warnings, redacted_text=redacted, raw_text=raw)
    return _created_view(state, check_id, status_code=200)


# ---- POST /api/checks/{id}/run ----------------------------------------------------------------------------------
@router.post("/checks/{check_id}/run", status_code=202)
async def run(check_id: str, request: Request):
    state = request.app.state.s26
    check = _load(state, check_id, for_update=True)
    if check["status"] != "awaiting_confirmation":
        raise ConflictState(f"This check is {check['status']}.")
    _daily_cap(state)
    claims = state.repo.claims(check_id)
    state.repo.save_claims(check_id, claims, confirmed=True)          # frozen for the run (08 §2.7)
    _start(state, check_id)
    return {"check_id": check_id, "status": "running"}


# ---- GET /api/checks/{id} ---------------------------------------------------------------------------------------
def check_view(state, check_id: str, public: bool = False) -> dict:
    repo = state.repo
    check = _load(state, check_id)
    claims = repo.claims(check_id)
    view = {"check_id": check_id, "status": check["status"], "mode": check["mode"],
            "created_at": check["created_at"], "warnings": check["warnings"],
            "claims": [_claim_json(c) for c in claims],
            "probes": [{"probe_id": p["probe_id"], "status": p["status"], "credits_used": p["credits_used"],
                        "cache_hits": p["cache_hits"], "duration_ms": p["duration_ms"], "outputs": p["outputs"]}
                       for p in repo.probe_runs(check_id)],
            "findings": [{k: f[k] for k in ("id", "probe_id", "code", "family", "weight", "effective_weight",
                                            "decisive_flag", "message", "claim_ids", "receipt")}
                         for f in repo.findings(check_id)],
            "verdict": None, "campaign": None}
    v = repo.verdict(check_id)
    if v:
        cs = ClaimSet(claims=claims)
        head, sub = headline(v["tier"], v["red_kind"], cs.org_name, v["official_contacts"])
        view["verdict"] = {
            "tier": v["tier"], "red_kind": v["red_kind"], "headline": head, "sub_line": sub, "score": v["score"],
            "family_scores": v["family_scores"], "decisive": v["decisive"], "coverage": v["coverage"],
            "strength": strength(v["score"]), "reasons": v["reasons"], "official_contacts": v["official_contacts"],
            "next_steps": next_steps(v["tier"], cs, v["official_contacts"]), "ruleset_version": v["ruleset_version"]}
    if public:
        return mask_view(view)
    used, hits = repo.credits_for_check(check_id)
    view["credits"] = {"used": used, "cache_hits": hits, "budget": state.settings.credit_budget_per_check}
    return view


def mask_view(view: dict) -> dict:
    """07 §6: no raw, masked identifiers, no credits, no probe outputs."""
    for c in view["claims"]:
        c.pop("raw", None)
        v = c["value"]
        if c["type"] == "phone":
            v["e164"] = mask_phone(v["e164"])
        elif c["type"] == "upi_id":
            v["vpa"] = mask_upi(v["vpa"])
        elif c["type"] in ("sender_email", "reply_to") and v.get("address"):
            v["address"] = mask_email(v["address"])
    for p in view["probes"]:
        p.pop("outputs", None)
    for f in view["findings"]:
        f["receipt"]["snippet"] = mask_text(f["receipt"].get("snippet"))
    view.pop("warnings", None)
    return view


@router.get("/checks/{check_id}")
async def get_check(check_id: str, request: Request):
    return check_view(request.app.state.s26, check_id)


# ---- GET /api/checks/{id}/events (SSE) --------------------------------------------------------------------------
@router.get("/checks/{check_id}/events")
async def events(check_id: str, request: Request):
    state = request.app.state.s26
    _load(state, check_id)
    try:
        last = int(request.headers.get("last-event-id") or request.query_params.get("last_event_id") or 0)
    except ValueError:
        last = 0
    final = ("verdict.ready", "check.failed")

    async def stream():
        q = state.events.subscribe(check_id)            # subscribe first, then replay: nothing is missed
        try:
            seen = last
            for seq, t, d in state.repo.events_after(check_id, last):
                seen = seq
                yield ServerSentEvent(id=str(seq), event=t, data=json.dumps(d, ensure_ascii=False))
                if t in final:
                    return
            if state.repo.get_check(check_id)["status"] in TERMINAL:
                return
            while True:
                seq, t, d = await q.get()
                if seq <= seen:
                    continue
                yield ServerSentEvent(id=str(seq), event=t, data=json.dumps(d, ensure_ascii=False))
                if t in final:
                    return
        finally:
            state.events.unsubscribe(check_id, q)

    return EventSourceResponse(stream(), ping=15)

