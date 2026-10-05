import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import NextSteps from "../components/NextSteps";
import VerdictCard from "../components/VerdictCard";
import { errorText } from "./Home";

export const fmtDate = (iso?: string | null) =>
  iso ? new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }) : "";

export default function Share() {
  const { token = "" } = useParams();
  const q = useQuery({ queryKey: ["share", token], queryFn: () => api.getShare(token) });
  if (q.isLoading) return <p className="text-muted">Loading…</p>;
  if (q.isError || !q.data?.verdict) return <p role="alert">{errorText(q.error)}</p>;
  const c = q.data;
  const org = c.claims.find((x) => x.type === "org")?.value.name ?? "the company";
  return (
    <>
      <p className="mb-5 text-[0.9rem] text-muted">Shared from Special26. Checked on {fmtDate(c.shared_on ?? c.created_at)}.</p>
      <VerdictCard verdict={c.verdict!} findings={c.findings} probes={c.probes} />
      <NextSteps steps={c.verdict!.next_steps.filter((s) => s !== "tell_placement_cell")} org={org}
        contacts={c.verdict!.official_contacts} />
      <Link to="/" className="mt-10 inline-block w-full rounded-lg bg-action px-6 py-4 text-center text-[1.05rem] font-bold text-white no-underline hover:bg-action-dark sm:w-auto">
        Check your own offer
      </Link>
    </>
  );
}
