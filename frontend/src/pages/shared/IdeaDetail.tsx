import { useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { ArrowLeft, Bookmark, BookmarkCheck, Download, Flag, Handshake, Lock, MessageSquare, Pencil, RefreshCw, ShieldCheck, Trash2, Upload, X } from "lucide-react";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { useLoad } from "../../lib/hooks";
import type { Evaluation, IdeaDetail as Idea } from "../../lib/types";
import { STAGE_LABEL } from "../../lib/types";
import { Badge, Button, Card, EmptyState, ErrorBox, Field, Modal, Notice, Spinner, Tabs, statusTone, useToast } from "../../components/ui";
import ReportView from "../../components/ReportView";
import EvaluationProgress from "../../components/EvaluationProgress";
import IdeaForm, { IdeaFormValues } from "../../components/IdeaForm";
import { errMsg, fmtBytes, fmtDate, fmtMoney } from "../../lib/utils";

interface EvalResp { current: Evaluation; latest_completed: Evaluation | null }
interface Match { entrepreneur: { id: number; name: string; company_name: string; company_type: string; industries: string[]; is_verified: boolean }; score: number; reasons: string[] }
const toForm = (i: Idea): IdeaFormValues => ({ title: i.title, short_description: i.short_description, problem: i.problem ?? "", solution: i.solution ?? "", industry: i.industry,
  target_audience: i.target_audience ?? "", technologies: i.technologies, stage: i.stage, expected_impact: i.expected_impact ?? "", business_potential: i.business_potential ?? "",
  funding_needed: i.funding_needed ? String(i.funding_needed) : "", visibility: i.visibility });

export default function IdeaDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const nav = useNavigate();
  const toast = useToast();
  const [sp] = useSearchParams();
  const [tab, setTab] = useState<"overview" | "evaluation" | "documents" | "matches">(sp.get("tab") === "evaluation" ? "evaluation" : "overview");
  const [modal, setModal] = useState<"" | "edit" | "request" | "report" | "delete">("");
  const [msg, setMsg] = useState(""); const [kind, setKind] = useState("collaborate"); const [reason, setReason] = useState("spam"); const [busy, setBusy] = useState(false);
  const idea = useLoad(() => api.get<Idea>(`/ideas/${id}`), [id]);
  const i = idea.data;
  const owner = !!user && !!i && (user.id === i.creator.id);
  const full = i?.access === "full";
  const evalRes = useLoad<EvalResp | null>(async () => (full ? api.get<EvalResp>(`/ideas/${id}/evaluation`).catch(() => null) : null), [id, full]);
  const matches = useLoad<Match[]>(async () => (owner ? api.get<Match[]>(`/ideas/${id}/matches`) : []), [id, owner]);
  const base = user ? `/app/${user.role}` : "";

  if (idea.loading) return <Spinner />;
  if (idea.error || !i) return <div className="mx-auto max-w-xl py-10"><ErrorBox message={idea.error ?? "Idea not found"} /><Link to="/explore" className="mt-4 inline-block text-sm text-navy-700 hover:underline">← Back to Explore</Link></div>;

  const run = async (fn: () => Promise<unknown>, ok: string) => { setBusy(true); try { await fn(); toast.ok(ok); } catch (e) { toast.err(errMsg(e)); } finally { setBusy(false); } };
  const toggleSave = () => run(async () => { if (i.is_saved) await api.del(`/saved/${i.id}`); else await api.post(`/saved/${i.id}`); await idea.reload(true); }, i.is_saved ? "Removed from saved" : "Saved");
  const sendRequest = () => run(async () => { await api.post("/collaboration", { idea_id: i.id, kind, message: msg }); setModal(""); setMsg(""); await idea.reload(true); }, "Request sent to the creator");
  const sendReport = () => run(async () => { await api.post(`/ideas/${i.id}/report`, { reason, details: msg }); setModal(""); setMsg(""); }, "Thanks – our moderators will review it");
  const del = () => run(async () => { await api.del(`/ideas/${i.id}`); nav(`${base}/ideas`); }, "Idea deleted");
  const reEval = () => run(async () => { await api.post(`/ideas/${i.id}/evaluate`); setTab("evaluation"); await evalRes.reload(true); }, "Evaluation started");
  const upload = async (f?: File) => { if (!f) return; await run(async () => { await api.upload(`/ideas/${i.id}/documents`, f); await idea.reload(true); }, "Document uploaded"); };
  const delDoc = (d: number) => run(async () => { await api.del(`/documents/${d}`); await idea.reload(true); }, "Document removed");
  const saveEdit = async (v: IdeaFormValues) => {
    await api.put(`/ideas/${i.id}`, { ...v, funding_needed: v.funding_needed ? Number(v.funding_needed) : null });
    setModal(""); toast.ok("Idea updated"); await idea.reload(true); await evalRes.reload(true);
  };

  const cur = evalRes.data?.current;
  const tabs = [{ id: "overview" as const, label: "Overview" }, ...(full ? [{ id: "evaluation" as const, label: "AI evaluation" }] : []),
    ...(full ? [{ id: "documents" as const, label: "Documents", count: i.documents?.length ?? 0 }] : []), ...(owner ? [{ id: "matches" as const, label: "Matched entrepreneurs" }] : [])];

  return (
    <div>
      <Link to={owner ? `${base}/ideas` : user?.role === "entrepreneur" ? `${base}/discover` : "/explore"} className="mb-4 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-navy-800"><ArrowLeft className="h-4 w-4" />Back</Link>
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="mb-2 flex flex-wrap gap-2"><Badge tone="indigo">{i.industry}</Badge><Badge>{STAGE_LABEL[i.stage]}</Badge><Badge tone={statusTone(i.visibility)}>{i.visibility}</Badge>
            {i.moderation_status && i.moderation_status !== "active" && <Badge tone={statusTone(i.moderation_status)}>{i.moderation_status} by moderators</Badge>}</div>
          <h1 className="text-2xl font-bold sm:text-3xl">{i.title}</h1>
          <p className="mt-2 text-sm text-slate-500">By <span className="font-medium text-slate-700">{i.creator.name}</span>{i.creator.headline && ` · ${i.creator.headline}`} · Posted {fmtDate(i.created_at)}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {owner && <><Button variant="secondary" onClick={() => setModal("edit")}><Pencil className="h-4 w-4" />Edit</Button><Button variant="secondary" loading={busy} onClick={reEval}><RefreshCw className="h-4 w-4" />Re-run AI evaluation</Button><Button variant="danger" onClick={() => setModal("delete")}><Trash2 className="h-4 w-4" />Delete</Button></>}
          {user?.role === "entrepreneur" && <>
            <Button variant="secondary" onClick={toggleSave}>{i.is_saved ? <BookmarkCheck className="h-4 w-4" /> : <Bookmark className="h-4 w-4" />}{i.is_saved ? "Saved" : "Save"}</Button>
            <Link to={`${base}/messages?with=${i.creator.id}`}><Button variant="secondary"><MessageSquare className="h-4 w-4" />Contact creator</Button></Link>
            {i.my_request && ["pending", "accepted"].includes(i.my_request.status) ? <Badge tone={statusTone(i.my_request.status)} className="self-center">Request {i.my_request.status}</Badge> :
              <Button onClick={() => setModal("request")}><Handshake className="h-4 w-4" />Request collaboration</Button>}</>}
          {user && !owner && user.role !== "admin" && <Button variant="ghost" onClick={() => setModal("report")} aria-label="Report this idea"><Flag className="h-4 w-4" /></Button>}
        </div>
      </div>

      {!user && <Notice tone="sky" title="Sign in to see more"><Link className="font-medium underline" to="/login" state={{ from: `/ideas/${i.id}` }}>Log in</Link> or <Link className="font-medium underline" to="/register">create an account</Link> to read the full idea, its AI evaluation and contact the creator.</Notice>}
      {!full && user && i.visibility === "restricted" && (
        <Notice tone="sky" title="Restricted idea"><span className="flex items-center gap-1"><Lock className="h-3.5 w-3.5" />Full details, documents and the AI report unlock when the creator accepts your collaboration request.</span></Notice>)}
      <div className="mt-4"><Tabs tabs={tabs} value={tab} onChange={setTab} /></div>

      {tab === "overview" && (
        <div className="grid gap-5 lg:grid-cols-3">
          <div className="space-y-5 lg:col-span-2">
            <Card className="p-6"><h2 className="font-semibold">Summary</h2><p className="mt-2 text-slate-700">{i.short_description}</p></Card>
            {full ? (<>
              <Card className="p-6"><h2 className="font-semibold">Problem</h2><p className="mt-2 whitespace-pre-line text-slate-700">{i.problem}</p></Card>
              <Card className="p-6"><h2 className="font-semibold">Proposed solution</h2><p className="mt-2 whitespace-pre-line text-slate-700">{i.solution}</p></Card>
              {i.expected_impact && <Card className="p-6"><h2 className="font-semibold">Expected impact</h2><p className="mt-2 whitespace-pre-line text-slate-700">{i.expected_impact}</p></Card>}
              {i.business_potential && <Card className="p-6"><h2 className="font-semibold">Business potential</h2><p className="mt-2 whitespace-pre-line text-slate-700">{i.business_potential}</p></Card>}</>) :
              <EmptyState icon={<ShieldCheck className="h-6 w-6" />} title="Details are protected" text="The creator shares the full description only with people they approve." />}
          </div>
          <div className="space-y-5">
            <Card className="p-5 text-sm"><h2 className="mb-3 font-semibold">Details</h2><dl className="space-y-2">
              <div className="flex justify-between"><dt className="text-slate-500">Stage</dt><dd>{STAGE_LABEL[i.stage]}</dd></div>
              {full && <div className="flex justify-between gap-4"><dt className="text-slate-500">Audience</dt><dd className="text-right">{i.target_audience}</dd></div>}
              {full && <div className="flex justify-between"><dt className="text-slate-500">Funding sought</dt><dd>{fmtMoney(i.funding_needed)}</dd></div>}
              <div className="flex justify-between"><dt className="text-slate-500">Updated</dt><dd>{fmtDate(i.updated_at)}</dd></div></dl>
              {i.technologies.length > 0 && <div className="mt-3 flex flex-wrap gap-1">{i.technologies.map((t) => <Badge key={t}>{t}</Badge>)}</div>}</Card>
            {i.scores && <Card className="p-5 text-sm"><h2 className="mb-3 font-semibold">AI scores {i.scores.mode === "demo" && <Badge tone="amber">demo</Badge>}</h2>
              {[["Overall", i.scores.overall], ["Technical", i.scores.technical_feasibility], ["Market", i.scores.market_opportunity], ["Innovation", i.scores.innovation_differentiation]].map(([l, v]) => (
                <div key={l as string} className="mb-2 flex items-center justify-between"><span className="text-slate-500">{l}</span><span className="font-semibold">{v}/100</span></div>))}</Card>}
          </div>
        </div>)}

      {tab === "evaluation" && full && (evalRes.loading ? <Spinner /> : !cur ? <EmptyState title="No evaluation yet" text={owner ? "Run the AI evaluation to get a full report." : "The creator hasn't run an evaluation."} action={owner && <Button onClick={reEval}>Run evaluation</Button>} /> :
        cur.status === "failed" ? <div className="space-y-3"><ErrorBox message={cur.error ?? "Evaluation failed"} />{owner && <Button onClick={reEval}>Try again</Button>}</div> :
        cur.status !== "completed" ? <EvaluationProgress evaluation={cur} onUpdate={(e) => evalRes.setData({ current: e, latest_completed: evalRes.data?.latest_completed ?? null })} onDone={() => { evalRes.reload(true); idea.reload(true); }} /> :
        <ReportView evaluation={cur} />)}

      {tab === "documents" && full && (
        <Card className="p-6">
          {(i.documents ?? []).length === 0 ? <p className="text-sm text-slate-500">No documents attached.</p> : <ul className="divide-y divide-slate-100">{i.documents!.map((d) => (
            <li key={d.id} className="flex items-center justify-between py-3 text-sm"><div><div className="font-medium">{d.filename}</div><div className="text-xs text-slate-500">{fmtBytes(d.size)} · {fmtDate(d.uploaded_at)}</div></div>
              <div className="flex gap-2"><Button size="sm" variant="secondary" onClick={() => api.download(`/documents/${d.id}/download`, d.filename).catch((e) => toast.err(errMsg(e)))}><Download className="h-4 w-4" />Download</Button>
                {owner && <Button size="sm" variant="ghost" aria-label={`Delete ${d.filename}`} onClick={() => delDoc(d.id)}><X className="h-4 w-4" /></Button>}</div></li>))}</ul>}
          {owner && <label className="mt-4 inline-flex cursor-pointer items-center gap-2 rounded-lg border border-dashed border-slate-300 px-4 py-2 text-sm text-navy-700 hover:bg-navy-50"><Upload className="h-4 w-4" />Upload a document
            <input type="file" className="hidden" accept=".pdf,.docx,.pptx,.png,.jpg,.jpeg,.txt" onChange={(e) => { upload(e.target.files?.[0]); e.target.value = ""; }} /></label>}
        </Card>)}

      {tab === "matches" && owner && (matches.loading ? <Spinner /> : !matches.data?.length ? <EmptyState title="No matches yet" text="Entrepreneurs whose profiles overlap with this idea will appear here." /> :
        <div className="grid gap-4 md:grid-cols-2">{matches.data.map((m) => (
          <Card key={m.entrepreneur.id} className="p-5"><div className="flex items-start justify-between"><div><div className="font-semibold">{m.entrepreneur.company_name || m.entrepreneur.name}</div>
            <div className="text-xs text-slate-500">{m.entrepreneur.name} · {m.entrepreneur.company_type}{m.entrepreneur.is_verified && <span className="ml-1 text-emerald-700">✓ verified</span>}</div></div>
            <Badge tone="indigo">{m.score}/100</Badge></div>
            <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-slate-600">{m.reasons.map((r) => <li key={r}>{r}</li>)}</ul></Card>))}</div>)}

      <Modal open={modal === "edit"} onClose={() => setModal("")} title="Edit idea"><div className="-mx-2"><IdeaForm initial={toForm(i)} submitLabel="Save changes" onSubmit={saveEdit} /></div></Modal>
      <Modal open={modal === "request"} onClose={() => setModal("")} title="Request collaboration">
        <div className="space-y-4"><Field label="I want to"><select className="input" value={kind} onChange={(e) => setKind(e.target.value)}><option value="collaborate">Collaborate</option><option value="fund">Fund this idea</option><option value="develop">Develop it into a product</option></select></Field>
          <Field label="Message to the creator" hint="At least 10 characters."><textarea className="input" rows={4} value={msg} onChange={(e) => setMsg(e.target.value)} /></Field>
          <Button loading={busy} disabled={msg.trim().length < 10} onClick={sendRequest} className="w-full">Send request</Button></div></Modal>
      <Modal open={modal === "report"} onClose={() => setModal("")} title="Report this idea">
        <div className="space-y-4"><Field label="Reason"><select className="input" value={reason} onChange={(e) => setReason(e.target.value)}>{["spam", "plagiarism", "inappropriate", "confidential", "other"].map((r) => <option key={r}>{r}</option>)}</select></Field>
          <Field label="Details (optional)"><textarea className="input" rows={3} value={msg} onChange={(e) => setMsg(e.target.value)} /></Field><Button loading={busy} onClick={sendReport} className="w-full">Submit report</Button></div></Modal>
      <Modal open={modal === "delete"} onClose={() => setModal("")} title="Delete this idea?"><p className="text-sm text-slate-600">This permanently deletes the idea, its documents, evaluations and related requests. This cannot be undone.</p>
        <div className="mt-5 flex justify-end gap-2"><Button variant="secondary" onClick={() => setModal("")}>Cancel</Button><Button variant="danger" loading={busy} onClick={del}>Delete permanently</Button></div></Modal>
    </div>
  );
}
