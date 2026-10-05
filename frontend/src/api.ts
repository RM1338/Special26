// Typed client for docs/07-api-contract.md
export type Tier = "red" | "amber" | "green" | "grey";
export type Family = "identity" | "process" | "reputation" | "artifact" | "existence";
export interface Receipt {
  kind: "serp" | "rule" | "rdap" | "local_memory"; engine?: string | null; query?: string | null;
  position?: number | null; title?: string | null; link?: string | null; snippet?: string | null;
  serp_cache_key?: string | null; rule_id?: string | null; extra?: Record<string, unknown>;
}
export interface Finding {
  id: number; probe_id: string; code: string; family: Family; weight: number; effective_weight: number;
  decisive_flag: string | null; message: string; claim_ids: string[]; receipt: Receipt;
}
export interface Reason { rank: number; code: string; message: string; finding_ids: number[] }
export interface Contact { kind: string; value: string; finding_id: number }
export interface Verdict {
  tier: Tier; red_kind: "impersonation" | "fee_risk" | null; headline: string; sub_line: string; score: number;
  family_scores: Record<Family, number>; decisive: string[]; coverage: number; strength: number;
  reasons: Reason[]; official_contacts: Contact[]; next_steps: string[]; ruleset_version: string;
}
export type ClaimType = "org" | "scheme" | "sender_email" | "reply_to" | "url" | "phone" | "upi_id" | "amount" |
  "hr_person" | "address" | "role" | "stipend" | "deadline" | "process" | "legal_id" | "image";
export interface Claim {
  id: string; type: ClaimType; value: Record<string, any>; raw?: string; source: string; confidence: number;
}
export interface Probe {
  probe_id: string; status: string; credits_used: number; cache_hits: number; duration_ms: number;
  outputs?: Record<string, unknown>;
}
export interface CheckView {
  check_id: string; status: string; mode: "live" | "replay"; created_at: string; warnings?: string[];
  claims: Claim[]; probes: Probe[]; findings: Finding[]; verdict: Verdict | null;
  campaign: { campaign_id: number; member_count: number; orgs: string[] } | null;
  credits?: { used: number; cache_hits: number; budget: number };
}
export interface Created {
  check_id: string; status: string; mode: string; claims: Claim[]; warnings: string[];
  links: { self: string; events: string };
}
export interface Health { mode: "live" | "replay"; replay_recorded_at: string | null; ocr: boolean }

export class ApiError extends Error {
  status: number; code: string; retryAfter?: number;
  constructor(status: number, code: string, message: string, retryAfter?: number) {
    super(message);
    this.status = status; this.code = code; this.retryAfter = retryAfter;
  }
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(path, init);
  if (!r.ok) {
    const body = await r.json().catch(() => null);
    throw new ApiError(r.status, body?.error?.code ?? "INTERNAL", body?.error?.message ?? "Something went wrong.",
      Number(r.headers.get("Retry-After")) || undefined);
  }
  return r.json();
}

export const api = {
  create: (form: FormData) => call<Created>("/api/checks", { method: "POST", body: form }),
  get: (id: string) => call<CheckView>(`/api/checks/${id}`),
  putClaims: (id: string, body: unknown) =>
    call<Created>(`/api/checks/${id}/claims`, {
      method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    }),
  run: (id: string) => call<{ check_id: string; status: string }>(`/api/checks/${id}/run`, { method: "POST" }),
  share: (id: string) => call<{ token: string; url: string; expires_at: string }>(`/api/checks/${id}/share`,
    { method: "POST" }),
  getShare: (token: string) => call<CheckView>(`/api/share/${token}`),
  health: () => call<Health>("/api/health"),
};
