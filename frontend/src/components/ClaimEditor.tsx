import { useState } from "react";
import type { Claim } from "../api";
import { ERRORS } from "../copy";

type Draft = Claim & { removed?: boolean };
const GUESS = new Set(["pattern", "llm"]);
const PURPOSES: [string, string][] = [
  ["registration", "Registration"], ["training", "Training"], ["verification", "Verification"],
  ["deposit", "Deposit"], ["equipment", "Kit or equipment"], ["document", "Documents"], ["other_fee", "Other fee"],
  ["stipend", "Stipend"], ["salary", "Salary"],
];

let tmp = 0;
const newClaim = (type: Claim["type"], value: Record<string, unknown>): Draft =>
  ({ id: `new_${++tmp}`, type, value, source: "user", confidence: 1 });

export interface ClaimSubmit {
  claims: { id: string | null; type: string; value: Record<string, unknown> }[];
  mine: { phones: string[]; emails: string[] };
  org_unknown: boolean;
}

function Badge() {
  return <span className="ml-2 rounded bg-[#fdf3d7] px-1.5 py-0.5 text-[0.72rem] font-semibold text-[#7a4a00]">Please check</span>;
}

function Field({ label, guess, children }: { label: string; guess?: boolean; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="flex items-center text-[0.85rem] font-semibold text-muted">{label}{guess && <Badge />}</span>
      {children}
    </label>
  );
}

const input = "mt-1 block w-full rounded-md border border-rule bg-surface px-3 py-2.5 text-[1rem] focus:border-action focus:outline-none";

function Group({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <fieldset className="mt-7 border-l-2 border-rule pl-4">
      <legend className="-ml-4 mb-3 pl-4 text-[1.1rem] font-bold">{title}</legend>
      <div className="grid gap-4">{children}</div>
    </fieldset>
  );
}

export default function ClaimEditor({ claims, warnings, busy, error, onRun, onRestart }: {
  claims: Claim[]; warnings: string[]; busy: boolean; error: string | null;
  onRun: (s: ClaimSubmit) => void; onRestart: () => void;
}) {
  const [drafts, setDrafts] = useState<Draft[]>(() => {
    const d: Draft[] = claims.map((c) => ({ ...c, value: { ...c.value } }));
    if (!d.some((c) => c.type === "org")) d.unshift(newClaim("org", { name: "" }));
    if (!d.some((c) => c.type === "hr_person")) d.push(newClaim("hr_person", { name: "", title: "" }));
    if (!d.some((c) => c.type === "address")) d.push(newClaim("address", { raw: "" }));
    return d;
  });
  const [mine, setMine] = useState<Set<string>>(new Set());
  const [orgUnknown, setOrgUnknown] = useState(false);

  const of = (t: Claim["type"]) => drafts.filter((c) => c.type === t && !c.removed);
  const set = (id: string, patch: Record<string, unknown>) =>
    setDrafts((ds) => ds.map((c) => (c.id === id ? { ...c, value: { ...c.value, ...patch } } : c)));
  const toggleMine = (key: string) =>
    setMine((m) => { const n = new Set(m); if (n.has(key)) n.delete(key); else n.add(key); return n; });

  const org = of("org")[0];
  const orgName = String(org?.value.name ?? "").trim();
  const canRun = !!orgName || orgUnknown;

  function submit() {
    const keep = drafts.filter((c) => {
      if (c.removed) return false;
      if (c.type === "org") return !!String(c.value.name ?? "").trim() && !orgUnknown;
      if (c.type === "hr_person") return !!String(c.value.name ?? "").trim();
      if (c.type === "address") return !!String(c.value.raw ?? "").trim();
      return true;
    });
    onRun({
      claims: keep.map((c) => ({ id: c.id.startsWith("new_") ? null : c.id, type: c.type, value: c.value })),
      mine: {
        phones: of("phone").filter((c) => mine.has(c.id)).map((c) => String(c.value.e164)),
        emails: [...of("sender_email"), ...of("reply_to")].filter((c) => mine.has(c.id)).map((c) => String(c.value.address)),
      },
      org_unknown: orgUnknown,
    });
  }

  const MineToggle = ({ id }: { id: string }) => (
    <label className="mt-1.5 inline-flex items-center gap-2 text-[0.85rem]">
      <input type="checkbox" checked={mine.has(id)} onChange={() => toggleMine(id)} className="size-4 accent-action" />
      This is mine
    </label>
  );

  return (
    <section aria-labelledby="confirm-title">
      <h1 id="confirm-title" className="text-[1.9rem] font-extrabold leading-tight tracking-tight">
        Is this what the offer says?
      </h1>
      {warnings.includes("OCR_UNAVAILABLE") && (
        <p role="status" className="mt-4 rounded-md border border-amber/40 bg-[#fff6ed] px-4 py-3 text-[0.95rem]">
          {ERRORS.OCR_UNAVAILABLE}
        </p>
      )}

      <Group title="Who is offering">
        {org && (
          <div>
            <Field label="Organisation" guess={GUESS.has(org.source)}>
              <input className={`${input} ${!orgName && !orgUnknown ? "border-amber ring-2 ring-amber/30" : ""}`}
                value={String(org.value.name ?? "")} disabled={orgUnknown}
                onChange={(e) => set(org.id, { name: e.target.value })} />
            </Field>
            {!orgName && (
              <>
                <p className="mt-1.5 text-[0.9rem]">Which company or scheme does the offer say it's from?</p>
                <label className="mt-1 inline-flex items-center gap-2 text-[0.9rem]">
                  <input type="checkbox" checked={orgUnknown} onChange={(e) => setOrgUnknown(e.target.checked)}
                    className="size-4 accent-action" />
                  The offer doesn't say
                </label>
              </>
            )}
          </div>
        )}
        {of("hr_person").map((c) => (
          <div key={c.id} className="grid gap-4 sm:grid-cols-2">
            <Field label="HR name" guess={GUESS.has(c.source)}>
              <input className={input} value={String(c.value.name ?? "")} onChange={(e) => set(c.id, { name: e.target.value })} />
            </Field>
            <Field label="HR title" guess={GUESS.has(c.source)}>
              <input className={input} value={String(c.value.title ?? "")} onChange={(e) => set(c.id, { title: e.target.value })} />
            </Field>
          </div>
        ))}
      </Group>

      <Group title="How they contacted you">
        {of("sender_email").map((c) => (
          <div key={c.id}>
            <Field label="Sender email" guess={GUESS.has(c.source)}>
              <input className={input} type="email" value={String(c.value.address ?? "")}
                onChange={(e) => set(c.id, { address: e.target.value })} />
            </Field>
            <MineToggle id={c.id} />
          </div>
        ))}
        {of("reply_to").map((c) => (
          <div key={c.id}>
            <Field label="Reply-to" guess={GUESS.has(c.source)}>
              <input className={input} type="email" value={String(c.value.address ?? "")}
                onChange={(e) => set(c.id, { address: e.target.value })} />
            </Field>
            <MineToggle id={c.id} />
          </div>
        ))}
        {of("phone").map((c) => (
          <div key={c.id}>
            <Field label="Phone number">
              <input className={input} inputMode="tel" value={String(c.value.e164 ?? "")}
                onChange={(e) => set(c.id, { e164: e.target.value })} />
            </Field>
            <MineToggle id={c.id} />
          </div>
        ))}
        {(of("phone").length > 0 || of("sender_email").length > 0) && (
          <p className="text-[0.85rem] text-muted">Mark your own number and email so we don't search for them.</p>
        )}
        {of("url").map((c) => (
          <Field key={c.id} label="Link">
            <input className={input} value={String(c.value.url ?? "")} onChange={(e) => set(c.id, { url: e.target.value })} />
          </Field>
        ))}
        {of("upi_id").map((c) => (
          <Field key={c.id} label="UPI ID">
            <input className={input} value={String(c.value.vpa ?? "")} onChange={(e) => set(c.id, { vpa: e.target.value })} />
          </Field>
        ))}
      </Group>

      {of("amount").length > 0 && (
        <Group title="Money">
          {of("amount").map((c) => (
            <div key={c.id} className="grid grid-cols-[1fr_1fr] gap-3 sm:grid-cols-[8rem_1fr_auto]">
              <Field label="Amount (₹)">
                <input className={input} inputMode="numeric" value={String(c.value.value_inr ?? "")}
                  onChange={(e) => set(c.id, { value_inr: Number(e.target.value.replace(/\D/g, "")) || 0 })} />
              </Field>
              <Field label="For">
                <select className={input} value={String(c.value.purpose ?? "other_fee")}
                  onChange={(e) => set(c.id, { purpose: e.target.value })}>
                  {PURPOSES.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
                </select>
              </Field>
              <div className="col-span-2 sm:col-span-1">
                <span className="text-[0.85rem] font-semibold text-muted">Who pays</span>
                <div role="radiogroup" className="mt-1 flex overflow-hidden rounded-md border border-rule">
                  {([["candidate", "You"], ["employer", "Them"]] as const).map(([k, l]) => (
                    <button key={k} type="button" role="radio" aria-checked={c.value.payer === k}
                      onClick={() => set(c.id, { payer: k })}
                      className={`flex-1 px-4 py-2.5 text-[0.95rem] ${c.value.payer === k ? "bg-ink font-semibold text-white" : "bg-surface"}`}>
                      {l}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </Group>
      )}

      <Group title="Process">
        {of("deadline").map((c) => (
          <Field key={c.id} label="Deadline (hours)">
            <input className={input} inputMode="numeric" value={String(c.value.hours ?? "")}
              onChange={(e) => set(c.id, { hours: Number(e.target.value.replace(/\D/g, "")) || 0 })} />
          </Field>
        ))}
        {(() => {
          const p = of("process")[0];
          const kind = p?.value.no_interview ? "none" : p?.value.chat_only_interview ? "chat" : "normal";
          return (
            <Field label="Interview type">
              <select className={input} value={kind} onChange={(e) => {
                const v = e.target.value;
                const flags = { no_interview: v === "none", chat_only_interview: v === "chat" };
                if (p) set(p.id, flags);
                else setDrafts((ds) => [...ds, newClaim("process", { telegram: false, whatsapp: false, urgent: false, ...flags })]);
              }}>
                <option value="normal">Regular interview, or not mentioned</option>
                <option value="none">No interview</option>
                <option value="chat">Only over chat</option>
              </select>
            </Field>
          );
        })()}
      </Group>

      <Group title="Where">
        {of("address").map((c) => (
          <Field key={c.id} label="Office address" guess={GUESS.has(c.source)}>
            <input className={input} value={String(c.value.raw ?? "")} onChange={(e) => set(c.id, { raw: e.target.value })} />
          </Field>
        ))}
      </Group>

      {error && <p role="alert" className="mt-6 font-semibold text-red">{error}</p>}
      <div className="mt-8 flex flex-wrap items-center gap-4">
        <button type="button" onClick={submit} disabled={!canRun || busy}
          className="w-full rounded-lg bg-action px-6 py-4 text-[1.05rem] font-bold text-white hover:bg-action-dark disabled:opacity-50 sm:w-auto">
          {busy ? "Starting…" : "Run checks"}
        </button>
        <button type="button" onClick={onRestart} className="text-[0.95rem] font-semibold text-action underline underline-offset-4">
          Start over
        </button>
      </div>
      <p className="mt-3 text-[0.85rem] text-muted">Uses about 11 Google searches. Takes about 25 seconds.</p>
    </section>
  );
}
