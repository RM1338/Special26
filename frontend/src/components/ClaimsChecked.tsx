import { useState } from "react";
import type { Claim, Finding, Probe } from "../api";
import ReceiptDrawer from "./ReceiptDrawer";

const LABEL: Partial<Record<Claim["type"], string>> = {
  org: "Organisation", url: "Website or link", sender_email: "Sender email", reply_to: "Reply-to", phone: "Phone",
  upi_id: "UPI ID", amount: "Payment ask", address: "Office address", role: "Role", hr_person: "HR person",
  image: "Image",
};
const ORDER = Object.keys(LABEL) as Claim["type"][];

function shown(c: Claim): string {
  const v = c.value;
  switch (c.type) {
    case "org": return v.name;
    case "url": return v.host ?? v.url;
    case "sender_email": case "reply_to": return v.address;
    case "phone": return v.e164;
    case "upi_id": return v.vpa;
    case "amount": return `₹${Number(v.value_inr).toLocaleString("en-IN")}${v.purpose ? ` for ${String(v.purpose).replace("_", " ")}` : ""}`;
    case "address": return v.raw;
    case "role": return v.title;
    case "hr_person": return [v.name, v.title].filter(Boolean).join(", ");
    case "image": return v.role === "hr_photo" ? "HR's profile photo" : "Offer letter image";
    default: return c.raw ?? "";
  }
}

/** What we can honestly say when no finding refers to this claim (D-45). */
function neutral(c: Claim, org: string, official: string[] | null, probes: Record<string, Probe>): string {
  const ran = (id: string) => probes[id]?.status === "ok";
  if (c.type === "url" && c.value.registrable_domain && official !== null) {
    const d = c.value.registrable_domain as string;
    if (official.includes(d)) return `One of ${org}'s official websites, according to Google Search.`;
    const traced = ran("P06_IDENTIFIER_TRACE") ? ` We searched for ${d} in public reports and found nothing.` : "";
    return (official.length ? `Not one of the websites Google Search shows for ${org} (${official.join(", ")}).`
      : `Google Search did not show ${d} for ${org}.`) + traced;
  }
  if (c.type === "phone" && c.value.role === "recipient") return "Marked as yours, so we did not search for it.";
  if ((c.type === "phone" || c.type === "upi_id") && ran("P06_IDENTIFIER_TRACE"))
    return "We searched for it in public reports and found nothing.";
  if (c.type === "role" && ran("P07_ROLE")) return "Google Jobs had no listing to compare. That is not evidence either way.";
  if (c.type === "address" && ran("P08_OFFICE")) return "Google Maps gave nothing conclusive about this place.";
  if (c.type === "image" && ran("P09_IMAGE")) return "Google Lens found no matches that point either way.";
  if (c.type === "amount" && c.value.payer !== "candidate") return "Paid to you, not asked from you.";
  return "Nothing in our checks confirmed or contradicted this.";
}

export default function ClaimsChecked({ claims, findings, probes }: { claims: Claim[]; findings: Finding[]; probes: Probe[] }) {
  const [open, setOpen] = useState<Finding | null>(null);
  const byProbe = Object.fromEntries(probes.map((p) => [p.probe_id, p]));
  const p01 = byProbe["P01_ENTITY"];
  const official = p01?.status === "ok" ? ((p01.outputs?.official_domains as string[] | undefined) ?? []) : null;
  const org = claims.find((c) => c.type === "org")?.value.name ?? "the company";
  const rows = claims.filter((c) => LABEL[c.type]).sort((a, b) => ORDER.indexOf(a.type) - ORDER.indexOf(b.type));
  if (!rows.length) return null;

  return (
    <section aria-labelledby="claims-title" className="mt-10">
      <h2 id="claims-title" className="text-[1.25rem] font-bold">What the offer claims, and what we found</h2>
      <ul className="mt-3 divide-y divide-rule border-y border-rule">
        {rows.map((c) => {
          const fs = findings.filter((f) => f.claim_ids.includes(c.id) && (f.weight !== 0 || f.code === "P01_OFFICIAL_FOUND"));
          return (
            <li key={c.id} className="py-3.5">
              <p className="text-[0.82rem] font-semibold text-muted">{LABEL[c.type]}</p>
              <p className="break-words text-[1rem] font-semibold">{shown(c)}</p>
              {fs.length ? (
                <ul className="mt-1.5 grid gap-1">
                  {fs.map((f) => (
                    <li key={f.id}>
                      <button onClick={() => setOpen(f)} className="flex w-full items-start gap-2.5 text-left text-[0.93rem] leading-snug hover:text-action">
                        <span aria-hidden className={`mt-1.5 size-2 shrink-0 rounded-full ${f.weight > 0 ? "bg-red" : f.weight < 0 ? "bg-green" : "bg-grey"}`} />
                        <span>{f.message} <span className="text-action underline underline-offset-2">See source</span></span>
                      </button>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-1 text-[0.93rem] text-muted">{neutral(c, org, official, byProbe)}</p>
              )}
            </li>
          );
        })}
      </ul>
      {open && <ReceiptDrawer finding={open} onClose={() => setOpen(null)} />}
    </section>
  );
}
