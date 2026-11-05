import { Link, useNavigate } from "react-router-dom";
import { FolderKanban, Handshake, PlusCircle, Sparkles, Eye } from "lucide-react";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { useLoad } from "../../lib/hooks";
import type { Collab, Evaluation, IdeaCard } from "../../lib/types";
import { Badge, Button, Card, EmptyState, ErrorBox, PageHeader, ProgressBar, Spinner, Stat, statusTone, useToast } from "../../components/ui";
import IdeaForm, { EMPTY_IDEA, IdeaFormValues } from "../../components/IdeaForm";
import IdeaCardView from "../../components/IdeaCard";
import { fmtDate, scoreColor } from "../../lib/utils";

export function CreatorOverview() {
  const { user } = useAuth();
  const ideas = useLoad(() => api.get<IdeaCard[]>("/ideas/mine"), []);
  const reqs = useLoad(() => api.get<Collab[]>("/collaboration", { status: "pending" }), []);
  if (ideas.loading) return <Spinner />;
  if (ideas.error) return <ErrorBox message={ideas.error} onRetry={() => ideas.reload()} />;
  const list = ideas.data ?? [];
  const scored = list.filter((i) => i.scores);
  const avg = scored.length ? Math.round(scored.reduce((a, i) => a + (i.scores?.overall ?? 0), 0) / scored.length) : null;
  return (
    <div>
      <PageHeader title={`Hello, ${user?.full_name.split(" ")[0]}`} subtitle="Here's how your ideas are doing." actions={<Link to="/app/creator/submit"><Button><PlusCircle className="h-4 w-4" />Submit new idea</Button></Link>} />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Ideas" value={list.length} icon={<FolderKanban className="h-5 w-5" />} />
        <Stat label="Public / restricted" value={list.filter((i) => i.visibility !== "private").length} icon={<Eye className="h-5 w-5" />} />
        <Stat label="Avg. AI score" value={avg ?? "–"} hint={scored.some((i) => i.scores?.mode === "demo") ? "includes demo-mode scores" : undefined} icon={<Sparkles className="h-5 w-5" />} />
        <Stat label="Pending requests" value={reqs.data?.length ?? 0} icon={<Handshake className="h-5 w-5" />} />
      </div>
      <h2 className="mb-3 mt-8 text-lg font-semibold">Recent ideas</h2>
      {list.length === 0 ? <EmptyState title="No ideas yet" text="Submit your first idea to get an AI evaluation and reach entrepreneurs." action={<Link to="/app/creator/submit"><Button>Submit an idea</Button></Link>} /> :
        <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">{list.slice(0, 3).map((i) => <IdeaCardView key={i.id} idea={i} to={`/app/creator/ideas/${i.id}`} />)}</div>}
      {(reqs.data?.length ?? 0) > 0 && <Card className="mt-8 p-5"><div className="flex items-center justify-between"><h2 className="font-semibold">Needs your response</h2><Link to="/app/creator/collaboration" className="text-sm text-navy-700 hover:underline">View all →</Link></div>
        <ul className="mt-3 divide-y divide-slate-100">{reqs.data!.slice(0, 4).map((r) => <li key={r.id} className="py-2 text-sm"><span className="font-medium">{r.entrepreneur.name}</span> wants to {r.kind} on <span className="font-medium">{r.idea_title}</span></li>)}</ul></Card>}
    </div>
  );
}

export function SubmitIdea() {
  const nav = useNavigate(); const toast = useToast();
  const submit = async (v: IdeaFormValues, files: File[]) => {
    const res = await api.post<{ idea: { id: number } }>("/ideas", { ...v, funding_needed: v.funding_needed ? Number(v.funding_needed) : null });
    const failed: string[] = [];
    for (const f of files) { try { await api.upload(`/ideas/${res.idea.id}/documents`, f); } catch { failed.push(f.name); } }
    toast.ok("Idea submitted – AI evaluation started");
    if (failed.length) toast.err(`Could not upload: ${failed.join(", ")}`);
    nav(`/app/creator/ideas/${res.idea.id}?tab=evaluation`);
  };
  return (<div className="mx-auto max-w-3xl"><PageHeader title="Submit a new idea" subtitle="After submitting, the AI agent evaluates it automatically." /><IdeaForm initial={EMPTY_IDEA} submitLabel="Submit & evaluate" allowFiles onSubmit={submit} /></div>);
}

export function MyIdeas() {
  const { data, loading, error, reload } = useLoad(() => api.get<IdeaCard[]>("/ideas/mine"), []);
  if (loading) return <Spinner />;
  if (error) return <ErrorBox message={error} onRetry={() => reload()} />;
  return (
    <div>
      <PageHeader title="My ideas" subtitle="Manage, edit and track your submissions." actions={<Link to="/app/creator/submit"><Button><PlusCircle className="h-4 w-4" />New idea</Button></Link>} />
      {!data?.length ? <EmptyState title="You haven't submitted any ideas" action={<Link to="/app/creator/submit"><Button>Submit your first idea</Button></Link>} /> :
        <Card className="overflow-x-auto"><table className="w-full min-w-[720px] text-left text-sm"><thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500"><tr>
          <th className="px-4 py-3">Idea</th><th className="px-4 py-3">Stage</th><th className="px-4 py-3">Visibility</th><th className="px-4 py-3">AI score</th><th className="px-4 py-3">Requests</th><th className="px-4 py-3">Updated</th></tr></thead>
          <tbody className="divide-y divide-slate-100">{data.map((i) => (
            <tr key={i.id} className="hover:bg-slate-50"><td className="px-4 py-3"><Link to={`/app/creator/ideas/${i.id}`} className="font-medium text-navy-900 hover:underline">{i.title}</Link><div className="text-xs text-slate-500">{i.industry}</div>
              {i.moderation_status !== "active" && <Badge tone={statusTone(i.moderation_status ?? "")}>{i.moderation_status}</Badge>}</td>
              <td className="px-4 py-3 capitalize">{i.stage}</td><td className="px-4 py-3"><Badge tone={statusTone(i.visibility)}>{i.visibility}</Badge></td>
              <td className="px-4 py-3">{i.evaluation && i.evaluation.status !== "completed" ? <div className="w-24"><ProgressBar value={i.evaluation.progress} /><span className="text-xs text-slate-500">{i.evaluation.status}</span></div> :
                i.scores ? <span className="font-semibold" style={{ color: scoreColor(i.scores.overall) }}>{i.scores.overall}{i.scores.mode === "demo" && <span className="ml-1 text-xs font-normal text-amber-700">demo</span>}</span> : "–"}</td>
              <td className="px-4 py-3">{i.pending_requests ? <Badge tone="amber">{i.pending_requests} pending</Badge> : "–"}</td><td className="px-4 py-3 text-slate-500">{fmtDate(i.updated_at)}</td></tr>))}</tbody></table></Card>}
    </div>
  );
}

export function Reports() {
  const { data, loading, error, reload } = useLoad(() => api.get<Evaluation[]>("/evaluations"), []);
  if (loading) return <Spinner />;
  if (error) return <ErrorBox message={error} onRetry={() => reload()} />;
  return (
    <div>
      <PageHeader title="AI evaluation reports" subtitle="The latest evaluation for each of your ideas." />
      {!data?.length ? <EmptyState icon={<Sparkles className="h-6 w-6" />} title="No evaluations yet" text="Submit an idea and the AI agent will evaluate it automatically." /> :
        <div className="grid gap-4 md:grid-cols-2">{data.map((e) => (
          <Card key={e.id} className="p-5"><div className="flex items-start justify-between gap-2"><Link to={`/app/creator/ideas/${e.idea_id}?tab=evaluation`} className="font-semibold text-navy-900 hover:underline">{e.idea_title}</Link>
            <Badge tone={statusTone(e.status)}>{e.status}</Badge></div>
            <div className="mt-1 flex flex-wrap gap-2 text-xs text-slate-500"><span>v{e.version}</span><span>{fmtDate(e.completed_at ?? e.created_at)}</span>{e.mode && <Badge tone={e.mode === "demo" ? "amber" : "sky"}>{e.mode === "demo" ? "demo mode" : `AI · ${e.model}`}</Badge>}{e.outdated && <Badge tone="amber">outdated</Badge>}</div>
            {e.scores ? <div className="mt-4 grid grid-cols-4 gap-2 text-center">{[["Overall", e.scores.overall], ["Tech", e.scores.technical_feasibility], ["Market", e.scores.market_opportunity], ["Novelty", e.scores.innovation_differentiation]].map(([l, v]) => (
              <div key={l as string} className="rounded-lg bg-slate-50 p-2"><div className="text-lg font-bold" style={{ color: scoreColor(v as number) }}>{v}</div><div className="text-[11px] text-slate-500">{l}</div></div>))}</div> :
              e.status === "failed" ? <p className="mt-3 text-sm text-rose-700">{e.error}</p> : <div className="mt-4"><ProgressBar value={e.progress} /></div>}</Card>))}</div>}
    </div>
  );
}
