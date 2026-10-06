import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import NextSteps from "../components/NextSteps";
import { ArrowIcon } from "../components/Icon";
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
      <div className="lg:grid lg:grid-cols-[minmax(0,1fr)_22rem] lg:items-start lg:gap-10">
        <VerdictCard verdict={c.verdict!} findings={c.findings} probes={c.probes} />
        <aside className="lg:sticky lg:top-8">
          <div className="lg:rounded-xl lg:border lg:border-rule lg:bg-surface lg:px-6 lg:pb-6 lg:[&>section]:mt-6">
            <NextSteps steps={c.verdict!.next_steps.filter((s) => s !== "tell_placement_cell")} org={org}
              contacts={c.verdict!.official_contacts} />
          </div>
          <Link to="/" className="mt-8 flex w-full items-center justify-center gap-2 rounded-lg bg-action px-6 py-4 text-[1.05rem] font-bold text-white no-underline hover:bg-action-dark">
            Check your own offer <ArrowIcon className="size-5" />
          </Link>
        </aside>
      </div>
    </>
  );
}
