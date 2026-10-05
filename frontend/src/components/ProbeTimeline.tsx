import type { Finding, Probe } from "../api";
import { PROBES, SKIP_REASONS } from "../copy";

const ORDER = Object.keys(PROBES);

export function rowResult(p: Probe | undefined, findings: Finding[]): string {
  if (!p) return "Checking…";
  if (p.status === "ok") {
    const mine = findings.filter((f) => f.probe_id === p.probe_id && f.weight !== 0);
    const concerns = mine.filter((f) => f.weight > 0).length;
    if (concerns) return `${concerns} concern${concerns > 1 ? "s" : ""}`;
    return mine.length ? "Looks consistent" : "Nothing found";
  }
  if (p.status === "timeout" || p.status === "error") return "Couldn't check right now";
  return `Skipped: ${SKIP_REASONS[p.status] ?? p.status}`;
}

function Mark({ p, findings }: { p?: Probe; findings: Finding[] }) {
  if (!p) return <span aria-hidden className="inline-block size-4 animate-spin rounded-full border-2 border-rule border-t-action" />;
  const bad = findings.some((f) => f.probe_id === p.probe_id && f.weight > 0);
  const tone = p.status !== "ok" ? "bg-[#e7eaef] text-grey" : bad ? "bg-red text-white" : "bg-[#e3f1ea] text-green";
  return <span aria-hidden className={`grid size-5 place-items-center rounded-full text-[0.7rem] font-bold ${tone}`}>
    {p.status !== "ok" ? "–" : bad ? "!" : "✓"}
  </span>;
}

export default function ProbeTimeline({ org, seen, probes, findings }: {
  org: string; seen: Set<string>; probes: Probe[]; findings: Finding[];
}) {
  const byId = Object.fromEntries(probes.map((p) => [p.probe_id, p]));
  const rows = ORDER.filter((id) => seen.has(id) || byId[id]);
  return (
    <ol aria-live="polite" className="mt-5 divide-y divide-rule border-y border-rule">
      {rows.map((id) => {
        const p = byId[id];
        const meta = PROBES[id];
        const result = rowResult(p, findings);
        return (
          <li key={id} className="flex items-start gap-3 py-3" aria-label={`${meta.label.replaceAll("{org}", org)}: ${result}`}>
            <span className="mt-0.5"><Mark p={p} findings={findings} /></span>
            <div className="min-w-0 flex-1">
              <p className="text-[0.97rem] leading-snug">{meta.label.replaceAll("{org}", org)}</p>
              <p className="mt-0.5 flex flex-wrap items-center gap-x-2 text-[0.83rem] text-muted">
                {meta.engines.map((e) => (
                  <span key={e} className="rounded border border-rule px-1.5 text-[0.75rem] font-semibold text-ink">{e}</span>
                ))}
                <span>{result}</span>
                {p && p.cache_hits > 0 && <span>(saved search)</span>}
              </p>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
