# 05. Technical Design / Low Level Design

Python 3.11, FastAPI, Pydantic v2, httpx, SQLite (stdlib `sqlite3`, WAL), React 18 + Vite + TypeScript + Tailwind.

## 1. Repository layout

```
special26/
  backend/
    special26/
      __init__.py
      main.py                    # FastAPI app factory, static mount, lifespan
      config.py                  # Settings (pydantic-settings), reads SPECIAL26_* env
      errors.py                  # Special26Error + subclasses, error envelope
      api/
        checks.py                # POST /api/checks, GET, PUT claims, POST run, SSE
        campaigns.py
        share.py
        public_img.py            # GET /public/img/{token}
        health.py
      intake/
        pdf.py                   # pypdf text, embedded images
        ocr.py                   # pytesseract wrapper, optional
        eml.py                   # email.parser, Authentication-Results parsing
        images.py                # resize, EXIF strip, pHash (imagehash)
      claims/
        models.py                # Claim, ClaimSet (pydantic)
        regexes.py               # all patterns from 08 §2.2
        extract.py               # extract_claims(text, artifacts) -> ClaimSet
        org.py                   # Aho-Corasick dictionary + heuristics
        amounts.py               # purpose and payer classifier
        llm.py                   # optional fallback
        redact.py
      domains/
        classify.py              # classify(d, official_set) -> DomainClass
        confusables.py
        rdap.py
      serp/
        client.py                # SerpClient
        cache.py
        budget.py
        replay.py
      probes/
        base.py                  # Probe ABC, ProbeContext, ProbeResult, Finding, Receipt
        p01_entity.py ... p12_domain_age.py
        registry.py              # ordered list + dependency map
      scoring/
        weights.py               # loads rules/weights.yaml, validates against codes
        aggregate.py             # family caps, decisive, tiers, reasons, coverage
        copy.py                  # finding code -> message template
      template/
        normalize.py
        minhash.py
        lsh.py
        phrase.py                # distinctive sentence
      campaign/
        unionfind.py
        link.py
      pipeline/
        runner.py                # run_check(check_id)
        events.py                # in-process pub/sub for SSE
      storage/
        db.py                    # connection factory, pragmas
        migrations/001_init.sql
        repo.py                  # typed queries
        retention.py
      rules/
        weights.yaml
    tests/
      unit/ ...                  # one file per module
      golden/                    # G1..G6 replay tests
      conftest.py                # socket guard, temp DB
    requirements.txt
  frontend/
    src/
      api.ts                     # typed client from 07-api-contract
      pages/Home.tsx, Check.tsx, Share.tsx, Campaign.tsx
      components/ClaimEditor.tsx, ProbeTimeline.tsx, VerdictCard.tsx,
                 ReasonList.tsx, ReceiptDrawer.tsx, NextSteps.tsx, CoverageMeter.tsx
  data/
    seeds/known_entities.json, freemail.txt, aggregator_domains.txt,
          stock_photo_domains.txt, lexicons.yaml, cities.txt, scam_templates/*.txt
  eval/
    cases/*.json
    run_eval.py
    baselines/keyword.py, emscad_tfidf.py, llm_only.py
  scripts/
    record_demo.py               # live run of golden cases with SPECIAL26_RECORD_TO
    seed_db.py
  docs/                          # these files
  Dockerfile
  README.md
```

## 2. Core data classes (`probes/base.py`, `claims/models.py`)

```python
from __future__ import annotations
from enum import Enum
from typing import Literal, Optional
from pydantic import BaseModel, Field

class ClaimType(str, Enum):
    org = "org"; scheme = "scheme"; sender_email = "sender_email"; reply_to = "reply_to"
    url = "url"; phone = "phone"; upi_id = "upi_id"; amount = "amount"; hr_person = "hr_person"
    address = "address"; role = "role"; stipend = "stipend"; deadline = "deadline"
    process = "process"; legal_id = "legal_id"; image = "image"

class Claim(BaseModel):
    id: str                                  # "c_" + 8 hex, stable within a check
    type: ClaimType
    value: dict                              # type-specific fields, see 08 §2.1
    raw: str                                 # exact substring from the source
    span: Optional[tuple[int, int]] = None   # char offsets in redacted text
    source: Literal["regex", "dictionary", "legal_line", "pattern", "display_name",
                    "eml_header", "llm", "user"]
    confidence: float = Field(ge=0, le=1)

class ClaimSet(BaseModel):
    claims: list[Claim]
    warnings: list[str] = []
    def first(self, t: ClaimType) -> Optional[Claim]: ...
    def all(self, t: ClaimType) -> list[Claim]: ...

class Receipt(BaseModel):
    kind: Literal["serp", "rule", "rdap", "local_memory"]
    engine: Optional[str] = None             # google, google_news, google_forums, google_jobs, google_maps, google_lens
    query: Optional[str] = None
    position: Optional[int] = None
    title: Optional[str] = None
    link: Optional[str] = None
    snippet: Optional[str] = None
    serp_cache_key: Optional[str] = None
    rule_id: Optional[str] = None
    extra: dict = {}

class Finding(BaseModel):
    probe_id: str
    code: str                                # e.g. "P02_COMBOSQUAT"
    family: Literal["identity", "process", "reputation", "artifact", "existence"]
    weight: float                            # from weights.yaml, never computed ad hoc
    decisive_flag: Optional[str] = None      # e.g. "P04_NOTICE_NO_FEE"
    message: str
    claim_ids: list[str] = []
    receipt: Receipt

ProbeStatus = Literal["ok", "skipped_no_input", "skipped_no_official_domain", "skipped_budget",
                      "skipped_replay_miss", "skipped_no_public_url", "skipped_forwarded",
                      "unsupported", "timeout", "error"]

class ProbeResult(BaseModel):
    probe_id: str
    status: ProbeStatus
    findings: list[Finding] = []
    credits_used: int = 0
    cache_hits: int = 0
    duration_ms: int = 0
    outputs: dict = {}                       # e.g. P01: {"official_domains": [...], "official_contacts": [...]}
```

## 3. Probe contract

```python
class ProbeContext(BaseModel):
    check_id: str
    claims: ClaimSet
    created_at: datetime
    upstream: dict[str, ProbeResult]         # results of dependencies
    serp: "SerpClient"
    settings: "Settings"
    model_config = {"arbitrary_types_allowed": True}

class Probe(ABC):
    id: ClassVar[str]
    depends_on: ClassVar[tuple[str, ...]] = ()
    max_calls: ClassVar[int]                 # reserved from the budget up front

    @abstractmethod
    def applicable(self, ctx: ProbeContext) -> ProbeStatus | None: ...
        # return a skipped_* status if not applicable, None if it should run
    @abstractmethod
    async def run(self, ctx: ProbeContext) -> ProbeResult: ...

    def finding(self, code: str, message_vars: dict, receipt: Receipt,
                claim_ids: list[str] = (), decisive_flag: str | None = None) -> Finding:
        w = WEIGHTS[code]                    # KeyError at startup if yaml and code disagree
        return Finding(probe_id=self.id, code=code, family=w.family, weight=w.weight,
                       decisive_flag=decisive_flag, message=COPY[code].format(**message_vars),
                       claim_ids=list(claim_ids), receipt=receipt)
```

`registry.py`:

```python
PROBES: list[type[Probe]] = [P01Entity, P03Headers, P05Chatter, P06IdentifierTrace, P09Image,
                             P10Template, P11Policy, P12DomainAge,           # wave 1
                             P02Sender, P04FraudNotice, P07Role, P08Office]   # wave 2
DEPENDS = {"P02_SENDER": ("P01_ENTITY", "P03_HEADERS"), "P04_FRAUD_NOTICE": ("P01_ENTITY",),
           "P07_ROLE": ("P01_ENTITY",), "P08_OFFICE": ("P01_ENTITY",)}
```

## 4. SerpClient (`serp/client.py`)

```python
import hashlib, json, asyncio, httpx

SERP_URL = "https://serpapi.com/search.json"

def cache_key(params: dict) -> str:
    clean = {k: params[k] for k in sorted(params) if k not in ("api_key", "output", "no_cache")}
    return hashlib.sha256(json.dumps(clean, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

class BudgetExhausted(Special26Error): code = "BUDGET_EXHAUSTED"
class ReplayMiss(Special26Error): code = "REPLAY_MISS"

class SerpClient:
    def __init__(self, settings, repo, http: httpx.AsyncClient):
        self.s, self.repo, self.http = settings, repo, http
        self._sem = asyncio.Semaphore(4)

    async def search(self, check_id: str, params: dict) -> tuple[dict, str, bool]:
        """Returns (json, cache_key, cache_hit). Raises BudgetExhausted or ReplayMiss."""
        params = {"gl": self.s.gl, "hl": self.s.hl, **params}
        key = cache_key(params)
        if self.s.mode == "replay":
            row = self.repo.demo_get(key)                      # reads demo.db
            if row is None:
                raise ReplayMiss(f"no recording for {params.get('engine')}")
            return row, key, True
        hit = self.repo.cache_get(key, ttl_hours=self.s.cache_ttl_hours)
        if hit is not None:
            self.repo.ledger_add(check_id, params["engine"], key, cached=True)
            self._maybe_record(key, params, hit)
            return hit, key, True
        self.repo.budget_reserve(check_id, per_check=self.s.credit_budget_per_check,
                                 daily=self.s.daily_credit_cap)   # raises BudgetExhausted
        async with self._sem:
            data = await self._get_with_retry({**params, "api_key": self.s.serpapi_api_key})
        self.repo.cache_put(key, params["engine"], params, data)
        self.repo.ledger_add(check_id, params["engine"], key, cached=False)
        self._maybe_record(key, params, data)
        return data, key, False

    async def _get_with_retry(self, params: dict) -> dict:
        for attempt in (0, 1):
            r = await self.http.get(SERP_URL, params=params, timeout=10.0)
            if r.status_code == 429:
                raise BudgetExhausted("SerpApi rate or plan limit")
            if r.status_code >= 500 and attempt == 0:
                await asyncio.sleep(1.0); continue
            r.raise_for_status()
            data = r.json()
            if "error" in data and not data.get("search_metadata"):
                raise UpstreamError(data["error"])
            return data
        raise UpstreamError("SerpApi 5xx after retry")
```

Note: SerpApi returns `"error": "Google hasn't returned any results for this query."` for empty result sets. Treat that string as an empty, successful result (`ok` with no findings), not an upstream error. `_get_with_retry` must special-case it.

`budget_reserve` is one SQL transaction:

```sql
BEGIN IMMEDIATE;
SELECT COUNT(*) FROM credit_ledger WHERE check_id = ? AND cached = 0;          -- must be < per_check
SELECT COUNT(*) FROM credit_ledger WHERE cached = 0 AND day_utc = ?;           -- must be < daily
INSERT INTO credit_ledger (check_id, engine, cache_key, cached, day_utc, status) VALUES (?, ?, ?, 0, ?, 'reserved');
COMMIT;
```

## 5. Domain classification (`domains/classify.py`)

```python
import tldextract
from rapidfuzz.distance import DamerauLevenshtein

_EXT = tldextract.TLDExtract(suffix_list_urls=())   # offline snapshot
LURE = set(load_lines("lure_tokens"))              # 08 §3
FREEMAIL = set(load_lines("freemail.txt"))
PLATFORM = set(load_lines("platform_hosts"))
SWAPS = [("rn", "m"), ("vv", "w"), ("0", "o"), ("1", "l"), ("3", "e"), ("5", "s"), ("l", "i")]  # order matters

def reg(d: str) -> str:
    e = _EXT(d.lower().strip("."))
    return e.registered_domain or d.lower()

def label(d: str) -> str:
    return _EXT(d.lower()).domain

def _swap_norm(s: str) -> str:
    for a, b in SWAPS:
        s = s.replace(a, b)
    return s

def _is_combo(lab: str, olab: str) -> bool:
    a, o = lab.replace("-", ""), olab.replace("-", "")
    if o not in a or a == o:
        return False
    rest = a.replace(o, " ", 1)
    pieces = [p for p in re.split(r"[\s\-]+", rest) if p]
    return all(_segment_into_lures(p) for p in pieces)

def _segment_into_lures(p: str) -> bool:
    # greedy longest-match segmentation of p into lure tokens
    i = 0
    while i < len(p):
        for L in range(len(p) - i, 0, -1):
            if p[i:i + L] in LURE:
                i += L; break
        else:
            return False
    return True

def classify(d: str, official: set[str]) -> tuple[str, str | None]:
    """Returns (class, matched_official)."""
    r = reg(d)
    if r in official:
        return ("official" if d.lower() in (r, "www." + r) else "official_subdomain", r)
    if r in FREEMAIL:
        return ("freemail", None)
    if r in PLATFORM:
        return ("platform", None)
    lab = label(d)
    best = None
    for o in official:
        ol = label(o)
        if "xn--" in d or confusable_skeleton(lab) == ol or (lab != ol and _swap_norm(lab) == _swap_norm(ol)):
            return ("homoglyph", o)
        if lab == ol:
            return ("tld_swap", o)
        if DamerauLevenshtein.distance(lab, ol) <= max(1, len(ol) // 8):
            best = best or ("typosquat", o)
        if _is_combo(lab, ol) or ol in _EXT(d.lower()).subdomain.split("."):
            best = ("combosquat", o)
    return best or ("unrelated", None)
```

Unit tests (`tests/unit/test_classify.py`) must include at least:

| Input | Official | Expected |
|-------|----------|----------|
| `careers.techmahindra.com` | `techmahindra.com` | `official_subdomain` |
| `techmahindra-careers.in` | `techmahindra.com` | `combosquat` |
| `careers-github.com` | `github.com` | `combosquat` |
| `techmahindra.co.in` | `techmahindra.com` | `tld_swap` |
| `tecmahindra.com` | `techmahindra.com` | `typosquat` |
| `infosys-hr.xyz` | `infosys.com` | `combosquat` |
| `lnfosys.com` | `infosys.com` | `homoglyph` |
| `tcs.hr-onboarding.in` | `tcs.com` | `combosquat` |
| `gmail.com` | `tcs.com` | `freemail` |
| `forms.gle` | `tcs.com` | `platform` |
| `hiringdesk-global.com` | `tcs.com` | `unrelated` |
| `tcsion.com` | `tcs.com` | `unrelated` (do not flag: "ion" not a lure token) |

The last row matters: TCS iON is a real TCS business on a different domain. False combosquats on short brands are the main risk, which is why leftovers must be lure tokens only. Seed `known_entities.json` with `tcsion.com` as an official TCS domain.

## 6. Optional LLM extraction (`claims/llm.py`)

Called only when no `org` was found by rules and `SPECIAL26_LLM_PROVIDER != none`.

System prompt (exact):

```
You extract facts from a job or internship offer. Output JSON only, matching the schema.
Copy each value exactly as it appears in the text. If a field is not present, use null.
Do not guess. Do not judge whether the offer is genuine.
```

Schema:

```json
{
  "type": "object",
  "additionalProperties": false,
  "required": ["org", "role", "hr_name", "address"],
  "properties": {
    "org":     {"type": ["string", "null"], "maxLength": 80},
    "role":    {"type": ["string", "null"], "maxLength": 80},
    "hr_name": {"type": ["string", "null"], "maxLength": 60},
    "address": {"type": ["string", "null"], "maxLength": 200}
  }
}
```

Validation: `jsonschema.validate`; every non-null value must be a substring of the redacted text (case-insensitive); else the field is dropped and warning `LLM_EXTRACTION_INVALID` is added. Temperature 0, max tokens 200, timeout 8 s.

## 7. Scorer (`scoring/aggregate.py`)

```python
FAMILY_CAPS = {"identity": (-3.5, 4.0), "process": (0.0, 4.0), "reputation": (-1.5, 4.0),
               "artifact": (-1.5, 4.0), "existence": (-2.0, 2.0)}
COVERAGE_W = {"P01_ENTITY": 3, "P02_SENDER": 2, "P03_HEADERS": 1, "P04_FRAUD_NOTICE": 2,
              "P05_CHATTER": 1, "P06_IDENTIFIER_TRACE": 2, "P07_ROLE": 1, "P08_OFFICE": 1,
              "P09_IMAGE": 1.5, "P10_TEMPLATE": 1, "P11_POLICY": 2, "P12_DOMAIN_AGE": 0.5}
LOOKALIKE = {"P02_HOMOGLYPH", "P02_TYPOSQUAT", "P02_COMBOSQUAT", "P02_TLD_SWAP"}
RULESET_VERSION = "2026.10.1"

def _effective(findings: list[Finding]) -> list[tuple[Finding, float]]:
    out, la = [], sorted([f for f in findings if f.code in LOOKALIKE], key=lambda f: -f.weight)
    keep_full = la[0].code if la else None
    for f in findings:
        w = f.weight
        if f.code in LOOKALIKE and f.code != keep_full:
            w *= 0.25
        out.append((f, w))
    # P06_ID_REPORTED probe cap
    rep = [(f, w) for f, w in out if f.code == "P06_ID_REPORTED"]
    excess = sum(w for _, w in rep) - 4.0
    if excess > 0:
        out = [(f, w) for f, w in out if f.code != "P06_ID_REPORTED"] + _scale(rep, 4.0)
    return out

def score(results: dict[str, ProbeResult], claims: ClaimSet) -> Verdict:
    findings = [f for r in results.values() for f in r.findings]
    eff = _effective(findings)
    fam = {k: 0.0 for k in FAMILY_CAPS}
    for f, w in eff:
        fam[f.family] += w
    fam = {k: min(max(v, FAMILY_CAPS[k][0]), FAMILY_CAPS[k][1]) for k, v in fam.items()}
    S = round(sum(fam.values()), 4)
    codes = {f.code for f in findings}
    flags = {f.decisive_flag for f in findings if f.decisive_flag}
    reported_sources = {urlparse(f.receipt.link).netloc for f in findings if f.code == "P06_ID_REPORTED"}

    decisive = []
    if "P11_CANDIDATE_PAYS" in codes and "P04_NOTICE_NO_FEE" in flags: decisive.append("D1_FEE_VS_NOTICE")
    if "P11_SCHEME_OFF_PORTAL" in codes and ({"P11_CANDIDATE_PAYS", "P11_FORM_OR_SHORTLINK"} & codes):
        decisive.append("D2_SCHEME_IMPERSONATION")
    if (LOOKALIKE & codes) and "P11_CANDIDATE_PAYS" in codes: decisive.append("D3_LOOKALIKE_PLUS_FEE")
    if len(reported_sources) >= 2: decisive.append("D4_IDENTIFIER_REPORTED")

    cov = coverage(results)
    green_anchor = ("P03_DKIM_ALIGNED_OFFICIAL" in codes) or (
        "P02_SENDER_OFFICIAL" in codes and ({"P07_ROLE_LISTED", "P08_OFFICE_MATCH", "P09_PHOTO_OFFICIAL"} & codes))
    strong_identity_pos = any(f.family == "identity" and f.weight >= 2.5 for f in findings)

    if decisive:                       tier = "red"
    elif cov < 0.40 and S < 3.0:       tier = "grey"
    elif S >= 3.0:                     tier = "red"
    elif (S <= -2.0 and "P11_CANDIDATE_PAYS" not in codes
          and not strong_identity_pos and green_anchor): tier = "green"
    else:                              tier = "amber"

    red_kind = None
    if tier == "red":
        red_kind = "impersonation" if (decisive or fam["identity"] >= 2.5 or fam["artifact"] >= 2.5) else "fee_risk"
    return Verdict(tier=tier, red_kind=red_kind, score=S, family_scores=fam, decisive=decisive,
                   coverage=round(cov, 3), reasons=top_reasons(eff, decisive, findings, k=3),
                   ruleset_version=RULESET_VERSION)
```

`top_reasons`: decisive rules first (each rendered from `COPY[rule_id]` with the receipts of the findings that triggered it), then remaining findings sorted by `-abs(effective_weight)`, then by `probe_id`, then by `code` (stable tiebreak). Findings with weight 0 are never reasons.

## 8. Pipeline runner (`pipeline/runner.py`)

```python
async def run_check(check_id: str, deps: Deps) -> None:
    check = deps.repo.get_check(check_id)
    ctx_base = dict(check_id=check_id, claims=check.claims, created_at=check.created_at,
                    serp=deps.serp, settings=deps.settings)
    results: dict[str, ProbeResult] = {}
    deps.events.publish(check_id, "check.running", {})

    async def run_one(P: type[Probe]):
        p = P()
        ctx = ProbeContext(**ctx_base, upstream={d: results[d] for d in DEPENDS.get(p.id, ()) if d in results})
        skip = p.applicable(ctx)
        if skip:
            res = ProbeResult(probe_id=p.id, status=skip)
        else:
            deps.events.publish(check_id, "probe.started", {"probe_id": p.id})
            t0 = time.monotonic()
            try:
                res = await asyncio.wait_for(p.run(ctx), timeout=12.0)
            except asyncio.TimeoutError:
                res = ProbeResult(probe_id=p.id, status="timeout")
            except BudgetExhausted:
                res = ProbeResult(probe_id=p.id, status="skipped_budget")
            except ReplayMiss:
                res = ProbeResult(probe_id=p.id, status="skipped_replay_miss")
            except Exception:
                log.exception("probe_error", extra={"check_id": check_id, "probe_id": p.id})
                res = ProbeResult(probe_id=p.id, status="error")
            res.duration_ms = int((time.monotonic() - t0) * 1000)
        results[p.id] = res
        deps.repo.save_probe_result(check_id, res)
        deps.events.publish(check_id, "probe.finished", res.summary())

    await asyncio.gather(*(run_one(P) for P in WAVE_1))
    await asyncio.gather(*(run_one(P) for P in WAVE_2))

    verdict = score(results, check.claims)
    deps.repo.save_verdict(check_id, verdict)
    sig = template_signature(check.redacted_text, check.claims)
    deps.repo.save_template(check_id, sig, label="scam" if verdict.tier == "red" else "unlabeled")
    campaign_id = link_campaign(check_id, verdict, check.claims, deps.repo) if verdict.tier in ("red", "amber") else None
    deps.events.publish(check_id, "verdict.ready", {"tier": verdict.tier, "campaign_id": campaign_id})
    deps.repo.purge_raw(check_id)        # NFR-06
```

`P09_IMAGE` letter call budget rule: before wave 1, the runner computes `reserved = sum(P.max_calls for applicable probes)`; P09 gets its second call only if `budget - reserved ≥ 3`.

## 9. Events (`pipeline/events.py`)

In-process `dict[check_id, list[asyncio.Queue]]`. Every event is also appended to `check_events` so a reconnecting client replays from `Last-Event-ID`. Event IDs are per-check integers starting at 1.

## 10. Template and campaign code

```python
# template/minhash.py
P = (1 << 61) - 1
_rng = random.Random(26)
A = [_rng.randrange(1, P) for _ in range(128)]
B = [_rng.randrange(0, P) for _ in range(128)]

def signature(tokens: list[str], k: int = 5) -> list[int] | None:
    if len(tokens) < 30:
        return None
    xs = {int.from_bytes(hashlib.blake2b(" ".join(tokens[i:i+k]).encode(), digest_size=8).digest(), "big")
          for i in range(len(tokens) - k + 1)}
    return [min((a * x + b) % P for x in xs) for a, b in zip(A, B)]

def band_keys(sig: list[int], bands: int = 32, rows: int = 4) -> list[str]:
    return [hashlib.blake2b(f"{b}:" .encode() + b"".join(v.to_bytes(8, "big") for v in sig[b*rows:(b+1)*rows]),
                            digest_size=8).hexdigest() for b in range(bands)]

def jaccard_est(a: list[int], b: list[int]) -> float:
    return sum(x == y for x, y in zip(a, b)) / len(a)
```

```python
# campaign/unionfind.py, persisted: campaign_members(check_id, campaign_id)
def link_campaign(check_id, verdict, claims, repo) -> int | None:
    neighbours = set()
    for kind, value in hard_identifiers(claims):            # upi, phone, domain, email
        neighbours |= repo.checks_with_identifier(kind, value, tiers=("red", "amber"), exclude=check_id)
    neighbours |= repo.checks_with_phash_near(check_id, max_hamming=6)
    neighbours |= repo.checks_with_template_near(check_id, min_j=0.6)
    if not neighbours:
        return None
    ids = {repo.campaign_of(n) for n in neighbours} - {None}
    target = min(ids) if ids else repo.create_campaign()
    for cid in ids - {target}:
        repo.merge_campaign(src=cid, dst=target)            # UPDATE campaign_members SET campaign_id = dst
    repo.add_members(target, [check_id, *neighbours])
    repo.refresh_campaign_stats(target)
    return target
```

## 11. Frontend components

| Component | Props | Behaviour |
|-----------|-------|-----------|
| `ClaimEditor` | `claims`, `onChange`, `onRun` | Grouped: Who (org, HR, sender, reply-to), Money (amounts, UPI), Process (deadline, interview), Where (address), Links. "Please check" badge on `pattern`/`llm` fields. "This is mine" toggle on phones and emails. Run disabled until org is set or "I don't know" is ticked |
| `ProbeTimeline` | `events` | One row per probe with engine icon, status, credits, cache badge. Rows appear as `probe.started` arrives |
| `VerdictCard` | `verdict` | Tier colour band + icon + headline + top 3 reasons + `CoverageMeter` + strength bar |
| `ReceiptDrawer` | `finding` | Engine, query (copyable), position, title, link (opens new tab), snippet with matched identifier highlighted |
| `NextSteps` | `verdict`, `official_contacts` | Ordered actions, see `09-user-flow.md` |

State: React Query for fetches, one `EventSource` per check page, no global store.

## 12. Dependencies (`requirements.txt`)

```
fastapi==0.115.*
uvicorn[standard]==0.30.*
pydantic==2.*
pydantic-settings==2.*
httpx==0.27.*
python-multipart==0.0.*
pypdf==4.*
pillow==10.*
imagehash==4.*
pytesseract==0.3.*
tldextract==5.*
rapidfuzz==3.*
pyahocorasick==2.*
wordfreq==3.*
jsonschema==4.*
pyyaml==6.*
sse-starlette==2.*
pytest==8.*
pytest-asyncio==0.23.*
```
