# 07. API Contract

Base path `/api`. JSON uses `snake_case`. All responses carry header `X-Request-Id`. Times are ISO 8601 UTC.

## 1. Endpoints

| Method | Path | Purpose | Auth |
|--------|------|---------|------|
| POST | `/api/checks` | Create a check from text and files, run extraction | none, rate limited |
| GET | `/api/checks/{check_id}` | Full check: status, claims, probes, findings, verdict | none (unguessable ID) |
| PUT | `/api/checks/{check_id}/claims` | Replace claims with the student's edited set | none |
| POST | `/api/checks/{check_id}/run` | Start probes after confirmation | none |
| GET | `/api/checks/{check_id}/events` | SSE progress stream | none |
| POST | `/api/checks/{check_id}/share` | Create or return the share token | none |
| GET | `/api/share/{token}` | Redacted, masked read-only view | public |
| GET | `/api/campaigns/{campaign_id}` | Campaign summary, masked | public |
| GET | `/api/health` | Mode, DB status, credits used today | public |
| GET | `/public/img/{token}` | Short-lived image for Google Lens | HMAC token |

Check IDs are 16 chars (`chk_` + 12 base32), about 60 bits of randomness: unguessable enough for a hackathon with no accounts.

## 2. Create a check

`POST /api/checks` as `multipart/form-data`:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `text` | string | one of `text` or `files` | ≤ 20,000 chars |
| `files` | file[] | | ≤ 4, ≤ 5 MB each, pdf/png/jpeg/eml |
| `file_roles` | string (JSON array) | no | Same order as `files`, values `offer_pdf`, `offer_image`, `eml`, `hr_photo` |
| `auto_run` | boolean | no | default `false` |

Response `201 Created`:

```json
{
  "check_id": "chk_k3v9q2m7x1ab",
  "status": "awaiting_confirmation",
  "mode": "live",
  "claims": [
    {"id":"c_1a2b3c4d","type":"org","value":{"name":"Tech Mahindra","legal_suffix":null,"entity_id":12},
     "raw":"Tech Mahindra","source":"dictionary","confidence":0.95},
    {"id":"c_5e6f7a8b","type":"sender_email","value":{"address":"hr.onboarding@techmahindra-careers.in",
     "display_name":null,"registrable_domain":"techmahindra-careers.in","from_headers":false},
     "raw":"hr.onboarding@techmahindra-careers.in","source":"regex","confidence":0.9},
    {"id":"c_9c0d1e2f","type":"amount","value":{"value_inr":2000,"purpose":"verification","payer":"candidate"},
     "raw":"Rs. 2,000/- towards Police Clearance Certificate","source":"regex","confidence":0.85},
    {"id":"c_3a4b5c6d","type":"upi_id","value":{"vpa":"techm.hr@ybl","handle":"ybl","handle_known":true},
     "raw":"techm.hr@ybl","source":"regex","confidence":0.95},
    {"id":"c_7e8f9a0b","type":"role","value":{"title":"Data Analyst Intern"},
     "raw":"Data Analyst Intern","source":"pattern","confidence":0.7}
  ],
  "warnings": [],
  "links": {"self":"/api/checks/chk_k3v9q2m7x1ab","events":"/api/checks/chk_k3v9q2m7x1ab/events"}
}
```

If `auto_run=true`, status is `running` and probes start immediately.

## 3. Edit claims

`PUT /api/checks/{check_id}/claims`, allowed only in `awaiting_confirmation`.

```json
{
  "claims": [
    {"id":"c_1a2b3c4d","type":"org","value":{"name":"Tech Mahindra"}},
    {"id":"c_5e6f7a8b","type":"sender_email","value":{"address":"hr.onboarding@techmahindra-careers.in"}},
    {"id":null,"type":"address","value":{"raw":"Plot 45, Sector 62, Noida 201309"}}
  ],
  "mine": {"phones":["+919000000001"],"emails":["priya.s@college.edu.in"]},
  "org_unknown": false
}
```

Rules: claims omitted from the list are deleted; `id: null` creates a claim with `source: "user"`; server recomputes derived fields (registrable domain, purpose, payer). Response `200` with the same shape as the create response.

## 4. Run and read

`POST /api/checks/{check_id}/run` → `202 {"check_id": "...", "status": "running"}`. Calling it in any other state returns `409 CONFLICT_STATE`.

`GET /api/checks/{check_id}` when `done`:

```json
{
  "check_id": "chk_k3v9q2m7x1ab",
  "status": "done",
  "mode": "live",
  "created_at": "2026-10-07T10:15:30Z",
  "claims": [ "...as above..." ],
  "probes": [
    {"probe_id":"P01_ENTITY","status":"ok","credits_used":1,"cache_hits":0,"duration_ms":1840,
     "outputs":{"official_domains":["techmahindra.com"]}},
    {"probe_id":"P03_HEADERS","status":"skipped_no_input","credits_used":0,"cache_hits":0,"duration_ms":0},
    {"probe_id":"P05_CHATTER","status":"ok","credits_used":3,"cache_hits":0,"duration_ms":4120}
  ],
  "findings": [
    {"id":101,"probe_id":"P02_SENDER","code":"P02_COMBOSQUAT","family":"identity","weight":3.0,
     "effective_weight":3.0,"decisive_flag":null,
     "message":"The sender domain techmahindra-careers.in is not Tech Mahindra's. Tech Mahindra uses techmahindra.com.",
     "claim_ids":["c_5e6f7a8b"],
     "receipt":{"kind":"serp","engine":"google","query":"\"Tech Mahindra\"","position":null,
       "title":"Tech Mahindra (knowledge graph)","link":"https://www.techmahindra.com/",
       "snippet":null,"serp_cache_key":"9f2c...e1","rule_id":null,"extra":{"source":"knowledge_graph.website"}}},
    {"id":104,"probe_id":"P04_FRAUD_NOTICE","code":"P04_NOTICE_FOUND","family":"reputation","weight":0.3,
     "effective_weight":0.3,"decisive_flag":"P04_NOTICE_NO_FEE",
     "message":"Tech Mahindra has published a recruitment fraud notice on its own website.",
     "claim_ids":["c_1a2b3c4d"],
     "receipt":{"kind":"serp","engine":"google","query":"(site:techmahindra.com) (fraud OR ...)","position":1,
       "title":"Recruitment Fraud","link":"https://careers.techmahindra.com/CPDOC/Recruitment_Fraud.pdf",
       "snippet":"... does not ask for any fee ...","serp_cache_key":"a71b...0c"}}
  ],
  "verdict": {
    "tier": "red",
    "red_kind": "impersonation",
    "headline": "Strong signs of impersonation. Do not pay.",
    "score": 8.0,
    "family_scores": {"identity":3.0,"process":4.0,"reputation":1.0,"artifact":0.0,"existence":0.0},
    "decisive": ["D1_FEE_VS_NOTICE","D3_LOOKALIKE_PLUS_FEE"],
    "coverage": 0.86,
    "strength": 0.62,
    "reasons": [
      {"rank":1,"code":"D1_FEE_VS_NOTICE","message":"Tech Mahindra's own recruitment fraud notice says it never charges candidates. This offer asks for ₹2,000.","finding_ids":[104,110]},
      {"rank":2,"code":"D3_LOOKALIKE_PLUS_FEE","message":"The sender domain techmahindra-careers.in is not Tech Mahindra's. Tech Mahindra uses techmahindra.com.","finding_ids":[101,110]},
      {"rank":3,"code":"P11_PERSONAL_UPI","message":"You are asked to pay a personal UPI ID (te****@ybl).","finding_ids":[111]}
    ],
    "official_contacts": [
      {"kind":"careers_url","value":"https://careers.techmahindra.com/","finding_id":104}
    ],
    "next_steps": ["do_not_pay","verify_official","report_cybercrime","report_chakshu"],
    "ruleset_version": "2026.10.1"
  },
  "campaign": {"campaign_id": 3, "member_count": 4, "orgs": ["Tech Mahindra","Infosys"]},
  "credits": {"used": 10, "cache_hits": 1, "budget": 14}
}
```

`strength = clamp((score + 8.5) / 26.5, 0, 1)`.

## 5. Server-sent events

`GET /api/checks/{check_id}/events`, `Content-Type: text/event-stream`. Supports `Last-Event-ID`. Heartbeat comment `: ping` every 15 s. Stream closes after `verdict.ready` or `check.failed`.

| Event | Data |
|-------|------|
| `check.extracting` | `{}` |
| `claims.ready` | `{"claim_count": 9, "warnings": ["OCR_UNAVAILABLE"]}` |
| `check.running` | `{"probes_planned": 11, "budget": 14}` |
| `probe.started` | `{"probe_id": "P07_ROLE", "engine": "google_jobs"}` |
| `probe.finished` | `{"probe_id": "P07_ROLE", "status": "ok", "findings": 1, "credits_used": 1, "cache_hits": 0, "duration_ms": 2210}` |
| `budget.warning` | `{"remaining": 2}` |
| `verdict.ready` | `{"tier": "red", "red_kind": "impersonation", "campaign_id": 3}` |
| `check.failed` | `{"code": "INTERNAL", "message": "..."}` |

Example frame:

```
id: 7
event: probe.finished
data: {"probe_id":"P09_IMAGE","status":"ok","findings":1,"credits_used":1,"cache_hits":0,"duration_ms":3302}

```

## 6. Share

`POST /api/checks/{check_id}/share` (only when `done`) → `200 {"token": "x9Qe...22chars", "url": "/s/x9Qe...", "expires_at": "2026-11-06T10:16:00Z"}`. Idempotent.

`GET /api/share/{token}` returns the same shape as §4 with these differences:

- `claims[].raw` removed; phones masked `+91 ******3210`; UPI masked `te****@ybl`; emails masked `h***@techmahindra-careers.in`; domains and URLs in full.
- `findings[].receipt.snippet` has identifiers masked the same way.
- No `credits`, no `probes[].outputs`.
- `view_count` incremented.

## 7. Campaign

`GET /api/campaigns/{campaign_id}`:

```json
{
  "campaign_id": 3,
  "member_count": 4,
  "orgs": ["Tech Mahindra", "Infosys"],
  "first_seen": "2026-10-06T08:02:11Z",
  "last_seen": "2026-10-07T10:16:40Z",
  "edge_counts": {"upi": 3, "template": 2},
  "tier_counts": {"red": 4},
  "shared_identifiers": [
    {"kind": "upi", "masked": "te****@ybl", "checks": 3},
    {"kind": "domain", "value": "techmahindra-careers.in", "checks": 2}
  ],
  "members": [{"share_token": "x9Qe...", "org": "Tech Mahindra", "tier": "red", "created_at": "..."}]
}
```

Members only expose a share token if one exists; otherwise `share_token: null`. If the campaign was merged, respond `301` with `Location: /api/campaigns/{merged_into}`.

## 8. Health

```json
{"status":"ok","mode":"replay","db":"ok","ruleset_version":"2026.10.1",
 "credits_today":{"used":37,"cap":200},"replay_recorded_at":"2026-10-09T05:40:00Z","ocr":true,"llm":"none"}
```

## 9. Errors

Every error uses one envelope:

```json
{"error": {"code": "VALIDATION_ERROR", "message": "text is longer than 20000 characters",
           "details": {"field": "text", "max": 20000}},
 "request_id": "req_01HV..."}
```

| HTTP | Code | When |
|------|------|------|
| 400 | `BAD_REQUEST` | Neither text nor files given |
| 404 | `NOT_FOUND` | Unknown check, token, campaign |
| 409 | `CONFLICT_STATE` | Wrong status for the operation |
| 410 | `EXPIRED` | Check expired or share token expired |
| 413 | `PAYLOAD_TOO_LARGE` | File > 5 MB or > 4 files |
| 415 | `UNSUPPORTED_MEDIA` | Not pdf/png/jpeg/eml |
| 422 | `VALIDATION_ERROR` | Field-level validation |
| 429 | `RATE_LIMITED` | > `SPECIAL26_RATE_LIMIT_PER_HOUR` checks from one IP, includes `Retry-After` |
| 429 | `BUDGET_EXHAUSTED` | Daily credit cap reached before the check could start (live only) |
| 500 | `INTERNAL` | Unhandled |

Budget exhaustion *during* a check is not an HTTP error: affected probes get status `skipped_budget` and the check still completes.

## 10. Frontend routes

| Route | Page |
|-------|------|
| `/` | Home and intake |
| `/c/{check_id}` | Claim editor, live timeline, verdict |
| `/s/{token}` | Share page |
| `/campaign/{id}` | Campaign page |

## 11. TypeScript types (frontend `api.ts`)

```ts
export type Tier = "red" | "amber" | "green" | "grey";
export type Family = "identity" | "process" | "reputation" | "artifact" | "existence";
export interface Receipt { kind: "serp" | "rule" | "rdap" | "local_memory"; engine?: string; query?: string;
  position?: number | null; title?: string; link?: string; snippet?: string | null;
  serp_cache_key?: string; rule_id?: string | null; extra?: Record<string, unknown>; }
export interface Finding { id: number; probe_id: string; code: string; family: Family; weight: number;
  effective_weight: number; decisive_flag: string | null; message: string; claim_ids: string[]; receipt: Receipt; }
export interface Reason { rank: number; code: string; message: string; finding_ids: number[]; }
export interface Verdict { tier: Tier; red_kind: "impersonation" | "fee_risk" | null; headline: string;
  score: number; family_scores: Record<Family, number>; decisive: string[]; coverage: number; strength: number;
  reasons: Reason[]; official_contacts: { kind: string; value: string; finding_id: number }[];
  next_steps: string[]; ruleset_version: string; }
```
