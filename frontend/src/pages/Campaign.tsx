import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { TIER_ICON } from "../copy";
import { errorText } from "./Home";
import { fmtDate } from "./Share";

const EDGE: Record<string, string> = {
  upi: "UPI ID", phone: "phone number", domain: "domain", email: "email address", image: "photo", template: "wording",
};
const KIND: Record<string, string> = { upi: "UPI ID", phone: "Phone", domain: "Domain", email: "Email" };
const TIER_WORD: Record<string, string> = { red: "High risk", amber: "Unverified", green: "Consistent", grey: "Not enough information" };

export default function Campaign() {
  const { id = "" } = useParams();
  const q = useQuery({ queryKey: ["campaign", id], queryFn: () => api.campaign(id) });
  if (q.isLoading) return <p className="text-muted">Loading…</p>;
  if (q.isError || !q.data) return <p role="alert">{errorText(q.error)}</p>;
  const c = q.data;
  const top = Object.entries(c.edge_counts).sort((a, b) => b[1] - a[1])[0]?.[0] ?? "upi";
  return (
    <section aria-labelledby="camp-title">
      <h1 id="camp-title" className="text-balance text-[1.9rem] font-extrabold leading-tight tracking-tight">
        {c.member_count} offers linked to the same {EDGE[top] ?? top}
      </h1>
      <h2 className="mt-7 text-[1rem] font-bold">Companies impersonated</h2>
      <div className="mt-2 flex flex-wrap gap-2">
        {c.orgs.map((o) => <span key={o} className="rounded-full border border-rule bg-surface px-3 py-1 text-[0.9rem]">{o}</span>)}
      </div>
      <dl className="mt-6 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 text-[0.95rem]">
        <dt className="text-muted">First seen</dt><dd>{fmtDate(c.first_seen)}</dd>
        <dt className="text-muted">Last seen</dt><dd>{fmtDate(c.last_seen)}</dd>
        {c.edge_counts.template ? (<><dt className="text-muted">Wording</dt>
          <dd>{c.edge_counts.template} offers share near-identical wording</dd></>) : null}
      </dl>
      {c.shared_identifiers.length > 0 && (
        <>
          <h2 className="mt-7 text-[1rem] font-bold">Shared details</h2>
          <ul className="mt-2 grid gap-1.5">
            {c.shared_identifiers.map((s) => (
              <li key={s.kind + (s.masked ?? s.value)} className="text-[0.95rem]">
                {KIND[s.kind] ?? s.kind} <span className="font-semibold">{s.masked ?? s.value}</span>
                <span className="text-muted"> in {s.checks} offers</span>
              </li>
            ))}
          </ul>
        </>
      )}
      <h2 className="mt-7 text-[1rem] font-bold">Offers</h2>
      <ol className="mt-2 divide-y divide-rule border-y border-rule">
        {c.members.map((m, i) => (
          <li key={i} className="flex items-center gap-3 py-3 text-[0.95rem]">
            <span aria-hidden>{TIER_ICON[m.tier ?? "grey"]}</span>
            <span className="flex-1"><span className="font-semibold">{m.org ?? "Unknown company"}</span>
              <span className="block text-[0.85rem] text-muted">{TIER_WORD[m.tier ?? "grey"]}, checked {fmtDate(m.created_at)}</span></span>
            {m.share_token && <Link to={`/s/${m.share_token}`} className="font-semibold text-action underline">View</Link>}
          </li>
        ))}
      </ol>
      <p className="mt-8 text-[0.9rem] text-muted">
        Placement officers: share this page with students. It updates as more offers are checked.
      </p>
    </section>
  );
}
