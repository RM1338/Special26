import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import ClaimEditor, { type ClaimSubmit } from "../components/ClaimEditor";
import ClaimsChecked from "../components/ClaimsChecked";
import NextSteps from "../components/NextSteps";
import ProbeTimeline from "../components/ProbeTimeline";
import VerdictCard from "../components/VerdictCard";
import { ERRORS } from "../copy";
import { errorText } from "./Home";

export function ReplayBanner() {
  const { data } = useQuery({ queryKey: ["health"], queryFn: api.health, staleTime: Infinity });
  if (data?.mode !== "replay") return null;
  const date = data.replay_recorded_at ? new Date(data.replay_recorded_at).toLocaleDateString("en-IN",
    { day: "numeric", month: "short", year: "numeric" }) : "an earlier date";
  return <p role="status" className="mb-5 rounded-md bg-[#e8ecf8] px-4 py-2.5 text-[0.88rem] text-action-dark">
    Demo mode: using search results recorded on {date}.</p>;
}

export default function Check() {
  const { id = "" } = useParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const [seen, setSeen] = useState<Set<string>>(new Set());
  const [runError, setRunError] = useState<string | null>(null);
  const [shareState, setShareState] = useState<string | null>(null);
  const q = useQuery({ queryKey: ["check", id], queryFn: () => api.get(id) });
  const status = q.data?.status;
  const live = status === "running" || status === "scoring";

  useEffect(() => {                                            // one EventSource per check page (05 §11)
    if (!live) return;
    const es = new EventSource(`/api/checks/${id}/events`);
    const refetch = () => qc.invalidateQueries({ queryKey: ["check", id] });
    es.addEventListener("probe.started", (e) => {
      const pid = JSON.parse((e as MessageEvent).data).probe_id;
      setSeen((s) => new Set(s).add(pid));
    });
    es.addEventListener("probe.finished", (e) => {           // D-16: refetch to show the row's result
      const pid = JSON.parse((e as MessageEvent).data).probe_id;
      setSeen((s) => new Set(s).add(pid));
      refetch();
    });
    for (const t of ["verdict.ready", "check.failed"]) es.addEventListener(t, () => { refetch(); es.close(); });
    return () => es.close();
  }, [id, live, qc]);

  const run = useMutation({
    mutationFn: async (s: ClaimSubmit) => { await api.putClaims(id, s); return api.run(id); },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["check", id] }),
    onError: (e) => setRunError(errorText(e)),
  });

  async function share() {
    try {
      const s = await api.share(id);
      const url = `${location.origin}${s.url}`;
      if (navigator.share) await navigator.share({ title: "Special26 check", url });
      else { await navigator.clipboard?.writeText(url); setShareState("Link copied"); }
    } catch {
      setShareState("Couldn't create a link");
    }
  }

  if (q.isLoading) return <p className="text-muted">Loading…</p>;
  if (q.isError || !q.data) return <p role="alert">{errorText(q.error)} <Link to="/" className="text-action underline">Start again</Link></p>;
  const c = q.data;
  const org = c.claims.find((x) => x.type === "org")?.value.name ?? "the company";

  if (c.status === "expired") return <p role="alert" className="mx-auto max-w-2xl text-[1.05rem]">{ERRORS.EXPIRED}{" "}
    <Link to="/" className="font-semibold text-action underline">Check an offer</Link></p>;
  if (c.status === "awaiting_confirmation" || c.status === "extracting" || c.status === "received") {
    return <><ReplayBanner /><ClaimEditor claims={c.claims} warnings={c.warnings ?? []} busy={run.isPending}
      error={runError} onRun={(s) => run.mutate(s)} onRestart={() => nav("/")} /></>;
  }
  if (c.status === "failed") return <p role="alert">This check couldn't finish. <Link to="/" className="text-action underline">Try again</Link></p>;

  return (
    <>
      <ReplayBanner />
      {c.verdict ? (
        <div className="lg:grid lg:grid-cols-[minmax(0,1fr)_22rem] lg:items-start lg:gap-10">
          <div className="min-w-0">
            <VerdictCard verdict={c.verdict} findings={c.findings} probes={c.probes} />
            <ClaimsChecked claims={c.claims} findings={c.findings} probes={c.probes} />
          </div>
          <aside className="lg:sticky lg:top-8">
            {c.campaign && (
              <Link to={`/campaign/${c.campaign.campaign_id}`}
                className="mt-6 block rounded-lg border border-rule bg-surface px-5 py-3.5 text-[0.95rem] no-underline hover:border-action lg:mt-0">
                <span className="font-semibold text-ink">Linked to {c.campaign.member_count - 1} other
                  offer{c.campaign.member_count > 2 ? "s" : ""}</span>
                <span className="text-muted"> using the same details{c.campaign.orgs.length > 1 ? `, claiming ${c.campaign.orgs.join(", ")}` : ""}.</span>
              </Link>
            )}
            <div className="lg:rounded-xl lg:border lg:border-rule lg:bg-surface lg:px-6 lg:pb-6 lg:[&>section]:mt-6">
              <NextSteps steps={c.verdict.next_steps} org={org} contacts={c.verdict.official_contacts}
                onShare={share} shareState={shareState} />
            </div>
            <details className="mt-8">
              <summary className="cursor-pointer text-[0.95rem] font-semibold">Checks we ran</summary>
              <ProbeTimeline org={org} seen={seen} probes={c.probes} findings={c.findings} />
            </details>
          </aside>
        </div>
      ) : (
        <div className="mx-auto max-w-2xl">
          <h1 className="text-[1.9rem] font-extrabold leading-tight tracking-tight lg:text-[2.4rem]">Checking {org}…</h1>
          <ProbeTimeline org={org} seen={seen} probes={c.probes} findings={c.findings} />
        </div>
      )}
    </>
  );
}
