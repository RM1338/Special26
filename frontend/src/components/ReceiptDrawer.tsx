import { useEffect, useRef } from "react";
import type { Finding } from "../api";
import { ENGINE_NAMES } from "../copy";

export default function ReceiptDrawer({ finding, why, onClose }: { finding: Finding; why?: string; onClose: () => void }) {
  const ref = useRef<HTMLDivElement>(null);
  const r = finding.receipt;
  useEffect(() => {
    const prev = document.activeElement as HTMLElement | null;
    ref.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "Tab" && ref.current) {                       // trap focus inside the slip
        const f = ref.current.querySelectorAll<HTMLElement>("a,button");
        if (!f.length) return;
        const [first, last] = [f[0], f[f.length - 1]];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    };
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("keydown", onKey); prev?.focus(); };
  }, [onClose]);

  const head = r.kind === "serp"
    ? `${ENGINE_NAMES[r.engine ?? ""] ?? "Search"}${r.position ? ` · result #${r.position}` : ""}`
    : r.kind === "local_memory" ? "Earlier checks"
    : r.rule_id === "known_entities.fraud_notice" ? "Employer's own notice" : "Rule";
  const host = r.link ? r.link.replace(/^https?:\/\//, "").replace(/\/$/, "") : null;
  const ruleText = (r.extra?.text as string | undefined) ?? (r.rule_id ? `Rule: ${r.rule_id}.` : null);
  const verified = r.extra?.verified_on as string | undefined;

  return (
    <div className="fixed inset-0 z-40 flex items-end justify-center bg-ink/40" onClick={onClose}>
      <div ref={ref} tabIndex={-1} role="dialog" aria-modal="true" aria-label="Receipt"
        onClick={(e) => e.stopPropagation()}
        className="slip printing mb-0 w-full max-w-xl px-5 pb-7 pt-6 text-[0.88rem] leading-relaxed text-ink sm:mb-10 sm:rounded-b-md sm:px-7">
        <div className="flex items-start justify-between gap-4">
          <p className="font-semibold">{head}</p>
          <button onClick={onClose} className="font-sans text-[0.9rem] font-semibold text-action underline underline-offset-4">Close</button>
        </div>
        <div className="slip-rule my-3" />
        <dl className="grid grid-cols-[5.5rem_1fr] gap-x-3 gap-y-2">
          {r.query && (<><dt className="text-muted">Query</dt>
            <dd className="break-words">{r.query}{" "}
              <button className="font-sans text-[0.8rem] font-semibold text-action underline"
                onClick={() => navigator.clipboard?.writeText(r.query ?? "")}>copy</button></dd></>)}
          {r.title && (<><dt className="text-muted">Title</dt><dd className="break-words">{r.title}</dd></>)}
          {host && (<><dt className="text-muted">Link</dt>
            <dd className="break-all"><a href={r.link!} target="_blank" rel="noopener noreferrer"
              className="text-action underline">{host}</a></dd></>)}
          {r.snippet && (<><dt className="text-muted">Snippet</dt><dd className="break-words">"{r.snippet}"</dd></>)}
          {r.kind !== "serp" && ruleText && !r.snippet && (<><dt className="text-muted">Rule</dt><dd>{ruleText}</dd></>)}
          {verified && (<><dt className="text-muted">Checked</dt><dd>From the employer's own notice, read on {verified}.</dd></>)}
        </dl>
        <div className="slip-rule my-3" />
        <p><span className="text-muted">Why it matters: </span>{why ?? finding.message}</p>
      </div>
    </div>
  );
}
