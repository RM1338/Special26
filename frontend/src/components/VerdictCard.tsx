import { useState } from "react";
import type { Finding, Probe, Verdict } from "../api";
import { ENGINE_NAMES, FAMILY_NAMES, PROBES, SKIP_REASONS } from "../copy";
import { TierIcon } from "./Icon";
import ReceiptDrawer from "./ReceiptDrawer";

const BAND: Record<string, string> = { red: "bg-red", amber: "bg-amber", green: "bg-green", grey: "bg-grey" };
const APPLICABLE = (p: Probe) => p.status !== "skipped_no_input" && p.status !== "unsupported";

function engineBadge(f?: Finding) {
  if (!f) return null;
  const r = f.receipt;
  const name = r.kind === "serp" ? ENGINE_NAMES[r.engine ?? ""] : r.kind === "local_memory" ? "Earlier checks"
    : r.rule_id === "known_entities.fraud_notice" ? "Employer notice" : "Rule";
  return <span className="shrink-0 rounded border border-rule px-1.5 py-0.5 text-[0.72rem] font-semibold text-muted">{name}</span>;
}

export default function VerdictCard({ verdict, findings, probes }: { verdict: Verdict; findings: Finding[]; probes: Probe[] }) {
  const [open, setOpen] = useState<{ f: Finding; why?: string } | null>(null);
  const [showSkipped, setShowSkipped] = useState(false);
  const byId = Object.fromEntries(findings.map((f) => [f.id, f]));
  const pick = (ids: number[]) => ids.map((i) => byId[i]).find((f) => f?.receipt.kind === "serp" || f?.receipt.link)
    ?? byId[ids[0]];
  const applicable = probes.filter(APPLICABLE);
  const covered = applicable.filter((p) => p.status === "ok");
  const skipped = applicable.filter((p) => p.status !== "ok");
  const families = Object.keys(FAMILY_NAMES).map((fam) => [fam, findings.filter((f) => f.family === fam && f.weight !== 0)] as const)
    .filter(([, fs]) => fs.length);

  return (
    <section aria-labelledby="verdict-title">
      <div className={`${BAND[verdict.tier]} rounded-t-lg px-5 pb-6 pt-5 text-white sm:flex sm:gap-5 sm:px-7 sm:py-7`}>
        <TierIcon tier={verdict.tier} className="size-10 shrink-0 sm:size-12" />
        <div>
          <h1 id="verdict-title" className="mt-3 text-balance text-[1.6rem] font-extrabold leading-tight tracking-tight sm:mt-0 sm:text-[2rem]">
            {verdict.headline}
          </h1>
          <p className="mt-2 text-[1rem] leading-relaxed text-white/90 sm:text-[1.05rem]">{verdict.sub_line}</p>
        </div>
      </div>

      <div className="rounded-b-lg border border-t-0 border-rule bg-surface px-5 pb-6 pt-5 sm:px-7">
        <h2 className="text-[1.1rem] font-bold">Why</h2>
        <ol className="mt-2 divide-y divide-rule">
          {verdict.reasons.map((r) => {
            const f = pick(r.finding_ids);
            return (
              <li key={r.rank}>
                <button onClick={() => f && setOpen({ f, why: r.message })} disabled={!f}
                  className="flex w-full items-start gap-3 py-3 text-left text-[0.98rem] leading-snug hover:text-action">
                  <span className="flex-1">{r.message}</span>
                  {engineBadge(f)}
                </button>
              </li>
            );
          })}
        </ol>

        <div className="mt-6">
          <h2 className="text-[1rem] font-bold">Evidence strength</h2>
          <div className="relative mt-3 h-2.5 rounded-full bg-gradient-to-r from-green via-[#d8dce3] to-red"
            role="img" aria-label={`Evidence leans ${verdict.strength >= 0.5 ? "fraudulent" : "genuine"}`}>
            <span className="absolute top-1/2 size-5 -translate-x-1/2 -translate-y-1/2 rounded-full border-[3px] border-white bg-ink shadow"
              style={{ left: `${verdict.strength * 100}%` }} />
          </div>
          <div className="mt-1.5 flex justify-between text-[0.8rem] text-muted"><span>Leans genuine</span><span>Leans fraudulent</span></div>
        </div>

        <div className="mt-6">
          <button onClick={() => setShowSkipped((v) => !v)} aria-expanded={showSkipped}
            className="text-left text-[0.95rem] font-semibold underline decoration-rule underline-offset-4">
            We could run {covered.length} of {applicable.length} checks.
          </button>
          {showSkipped && (
            <ul className="mt-2 grid gap-1 text-[0.88rem] text-muted">
              {skipped.length === 0 && <li>Every check that applied to this offer ran.</li>}
              {skipped.map((p) => (
                <li key={p.probe_id}>{PROBES[p.probe_id]?.label.replaceAll("{org}", "the company")}:{" "}
                  {p.status === "timeout" || p.status === "error" ? "couldn't check right now" : SKIP_REASONS[p.status] ?? p.status}</li>
              ))}
            </ul>
          )}
        </div>

        {families.length > 0 && (
          <details className="mt-6 border-t border-rule pt-4">
            <summary className="cursor-pointer text-[0.95rem] font-semibold">All findings</summary>
            {families.map(([fam, fs]) => (
              <div key={fam} className="mt-4">
                <h3 className="text-[0.9rem] font-bold text-muted">{FAMILY_NAMES[fam]}</h3>
                <ul className="mt-1">
                  {fs.map((f) => (
                    <li key={f.id}>
                      <button onClick={() => setOpen({ f })} className="flex w-full items-start gap-3 py-2 text-left text-[0.92rem] hover:text-action">
                        <span aria-hidden className={`mt-1.5 size-2 shrink-0 rounded-full ${f.weight > 0 ? "bg-red" : "bg-green"}`} />
                        <span className="flex-1">{f.message}</span>
                        {engineBadge(f)}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </details>
        )}
      </div>
      {open && <ReceiptDrawer finding={open.f} why={open.why} onClose={() => setOpen(null)} />}
    </section>
  );
}
