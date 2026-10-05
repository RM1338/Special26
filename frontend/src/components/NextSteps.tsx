import type { Contact } from "../api";

const link = "font-semibold text-action underline underline-offset-4";

export default function NextSteps({ steps, org, contacts, onShare, shareState }: {
  steps: string[]; org: string; contacts: Contact[]; onShare?: () => void; shareState?: string | null;
}) {
  const contact = contacts.find((c) => c.kind === "careers_url") ?? contacts.find((c) => c.kind === "website");
  const items: Record<string, React.ReactNode> = {
    do_not_pay: "Do not pay anything or share Aadhaar, PAN or bank details.",
    verify_official: contact && (
      <>Confirm directly with {org}: <a className={`${link} break-all`} href={contact.value} target="_blank" rel="noopener noreferrer">
        {contact.value.replace(/^https?:\/\//, "").replace(/\/$/, "")}</a></>
    ),
    call_1930: (<>Already paid? <a className={link} href="tel:1930">Call 1930</a> (National Cyber Crime Helpline) now.
      Fast reporting improves the chance of stopping the money.</>),
    report_cybercrime: (<>Report it at <a className={link} href="https://cybercrime.gov.in" target="_blank"
      rel="noopener noreferrer">cybercrime.gov.in</a></>),
    report_chakshu: (<>Report the call or message on <a className={link} href="https://sancharsaathi.gov.in/sfc/"
      target="_blank" rel="noopener noreferrer">Sanchar Saathi (Chakshu)</a></>),
    tell_placement_cell: (
      <span className="flex flex-wrap items-center gap-3">Tell your placement cell
        {onShare && <button onClick={onShare} className="rounded-md border border-action px-3 py-1.5 text-[0.9rem] font-semibold text-action">
          {shareState ?? "Share"}</button>}
      </span>),
  };
  const shown = steps.filter((s) => items[s]);
  return (
    <section aria-labelledby="next-title" className="mt-10">
      <h2 id="next-title" className="text-[1.25rem] font-bold">What to do now</h2>
      <ol className="mt-3 grid gap-3">
        {shown.map((s, i) => (
          <li key={s} className="flex gap-3 text-[0.98rem] leading-relaxed">
            <span aria-hidden className="mt-0.5 grid size-6 shrink-0 place-items-center rounded-full bg-ink text-[0.75rem] font-bold text-white">{i + 1}</span>
            <span className="min-w-0">{items[s]}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}
