import { useCallback, useEffect, useRef, useState } from "react";
import type { Claim, Finding } from "../api";
import { ENGINE_NAMES } from "../copy";

const CLOSE_MS = 180;
// Receipts saved before D-57 start with "Rule: P11_URGENCY. "; people should never see internal codes.
const plain = (t?: string | null) => t?.replace(/^Rule:\s*[A-Z0-9_.]+\.?\s*/, "") ?? null;

export default function ReceiptDrawer({ finding, why, claims, onClose }: {
  finding: Finding; why?: string; claims?: Claim[]; onClose: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [closing, setClosing] = useState(false);
  const r = finding.receipt;

  const close = useCallback(() => {
    if (closing) return;
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (reduce) return onClose();
    setClosing(true);                                            // short tear-off, then unmount
    window.setTimeout(onClose, CLOSE_MS);
  }, [closing, onClose]);

  useEffect(() => {
    const prev = document.activeElement as HTMLElement | null;
    ref.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
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
  }, [close]);

  const isRule = r.kind === "rule" && r.rule_id !== "known_entities.fraud_notice";
  const head = r.kind === "serp"
    ? `${ENGINE_NAMES[r.engine ?? ""] ?? "Search"}${r.position ? ` · result #${r.position}` : ""}`
    : r.kind === "local_memory" ? "Earlier checks and known patterns"
    : r.kind === "rdap" ? "Domain registration record"
    : r.rule_id === "known_entities.fraud_notice" ? "Employer's own notice" : "How we judged this";
  const host = r.link && !r.link.startsWith("/") ? r.link.replace(/^https?:\/\//, "").replace(/\/$/, "") : null;
  const ruleText = plain(r.extra?.text as string | undefined);
  const verified = r.extra?.verified_on as string | undefined;
  const header = r.extra?.header as string | undefined;
  // The exact words in the offer that this finding is about (private page only; share pages drop raw text)
  const quoted = (claims ?? []).filter((c) => finding.claim_ids.includes(c.id) && c.raw && c.type !== "org")
    .map((c) => c.raw!.trim()).filter((v, i, a) => v && a.indexOf(v) === i).slice(0, 3);

  return (
    <div className={`fixed inset-0 z-40 flex items-end justify-center bg-ink/40 ${closing ? "backdrop-out" : "backdrop-in"}`}
      onClick={close}>
      <div ref={ref} tabIndex={-1} role="dialog" aria-modal="true" aria-label={head}
        onClick={(e) => e.stopPropagation()}
        className={`slip ${closing ? "tearing" : "printing"} mb-0 w-full max-w-xl px-5 pb-7 pt-6 text-[0.88rem] leading-relaxed text-ink sm:mb-10 sm:rounded-b-md sm:px-7`}>
        <div className="flex items-start justify-between gap-4">
          <p className="font-semibold">{head}</p>
          <button onClick={close} className="font-sans text-[0.9rem] font-semibold text-action underline underline-offset-4">Close</button>
        </div>
        <div className="slip-rule my-3" />
        {isRule ? (
          <div className="grid gap-3">
            {ruleText && <p>{ruleText}</p>}
            {quoted.length > 0 && (
              <p><span className="text-muted">In this offer: </span>{quoted.map((q) => `"${q}"`).join(", ")}</p>
            )}
            {header && (
              <p className="break-words"><span className="text-muted">From your email's header: </span>{header}</p>
            )}
          </div>
        ) : (
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
            {verified && (<><dt className="text-muted">Checked</dt><dd>From the employer's own notice, read on {verified}.</dd></>)}
          </dl>
        )}
        <div className="slip-rule my-3" />
        <p><span className="text-muted">Why it matters: </span>{why ?? finding.message}</p>
      </div>
    </div>
  );
}
