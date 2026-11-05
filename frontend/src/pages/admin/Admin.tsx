import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Activity, Flag, Lightbulb, RefreshCw, ShieldCheck, Users } from "lucide-react";
import { api } from "../../lib/api";
import { useDebounced, useLoad } from "../../lib/hooks";
import type { Paged, UserBrief } from "../../lib/types";
import { Badge, Button, Card, EmptyState, ErrorBox, Field, Modal, PageHeader, Pagination, Spinner, Stat, Tabs, statusTone, useToast } from "../../components/ui";
import { errMsg, fmtDate, fmtDateTime } from "../../lib/utils";

const COLORS = ["#2f3b78", "#4a5fb3", "#7084c9", "#a0aedd", "#059669", "#d97706", "#dc2626", "#0ea5e9"];
interface Analytics { totals: Record<string, number>; growth: { labels: string[]; users: number[]; ideas: number[] }; ideas_by_industry: { industry: string; count: number }[];
  ideas_by_visibility: { visibility: string; count: number }[]; collab_by_status: { status: string; count: number }[]; avg_scores: { technical: number; market: number; innovation: number } }

export function AdminAnalytics() {
  const toast = useToast();
  const { data, loading, error, reload } = useLoad(() => api.get<Analytics>("/admin/analytics"), []);
  const logs = useLoad(() => api.get<{ id: number; admin: string; action: string; detail: string; created_at: string }[]>("/admin/logs"), []);
  const [busy, setBusy] = useState(false);
  if (loading) return <Spinner />;
  if (error || !data) return <ErrorBox message={error ?? "Failed"} onRetry={() => reload()} />;
  const t = data.totals;
  const growth = data.growth.labels.map((l, i) => ({ date: l.slice(5), Users: data.growth.users[i], Ideas: data.growth.ideas[i] }));
  const reindex = async () => { setBusy(true); try { const r = await api.post<{ ideas: number; reference_projects: number }>("/admin/reindex"); toast.ok(`Reindexed ${r.reference_projects} projects and ${r.ideas} ideas`); } catch (e) { toast.err(errMsg(e)); } finally { setBusy(false); } };
  return (
    <div>
      <PageHeader title="Platform analytics" actions={<Button variant="secondary" loading={busy} onClick={reindex}><RefreshCw className="h-4 w-4" />Re-embed all content</Button>} />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Users" value={t.users} hint={`${t.creators} creators · ${t.entrepreneurs} entrepreneurs`} icon={<Users className="h-5 w-5" />} />
        <Stat label="Ideas" value={t.ideas} hint={`${t.evaluations} evaluated`} icon={<Lightbulb className="h-5 w-5" />} />
        <Stat label="Evaluations" value={t.evaluations} hint={`${t.evaluations_live} live AI · ${t.evaluations_demo} demo`} icon={<Activity className="h-5 w-5" />} />
        <Stat label="Open reports" value={t.open_reports} hint={`${t.unverified_entrepreneurs} entrepreneurs unverified`} icon={<Flag className="h-5 w-5" />} />
      </div>
      <div className="mt-6 grid gap-5 lg:grid-cols-2">
        <Card className="p-5"><h2 className="mb-3 font-semibold">Growth – last 14 days</h2><div className="h-64"><ResponsiveContainer><LineChart data={growth}><CartesianGrid stroke="#e2e8f0" /><XAxis dataKey="date" fontSize={11} /><YAxis allowDecimals={false} fontSize={11} /><Tooltip /><Legend />
          <Line type="monotone" dataKey="Users" stroke="#2f3b78" strokeWidth={2} dot={false} /><Line type="monotone" dataKey="Ideas" stroke="#059669" strokeWidth={2} dot={false} /></LineChart></ResponsiveContainer></div></Card>
        <Card className="p-5"><h2 className="mb-3 font-semibold">Ideas by industry</h2><div className="h-64"><ResponsiveContainer><BarChart data={data.ideas_by_industry} layout="vertical" margin={{ left: 20 }}><CartesianGrid horizontal={false} stroke="#e2e8f0" /><XAxis type="number" allowDecimals={false} fontSize={11} />
          <YAxis type="category" dataKey="industry" width={120} fontSize={11} /><Tooltip /><Bar dataKey="count" fill="#4a5fb3" radius={[0, 4, 4, 0]} /></BarChart></ResponsiveContainer></div></Card>
        <Card className="p-5"><h2 className="mb-3 font-semibold">Visibility mix</h2><div className="h-56"><ResponsiveContainer><PieChart><Pie data={data.ideas_by_visibility} dataKey="count" nameKey="visibility" outerRadius={80} label>{data.ideas_by_visibility.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}</Pie><Tooltip /><Legend /></PieChart></ResponsiveContainer></div></Card>
        <Card className="p-5"><h2 className="mb-3 font-semibold">Average AI scores & collaboration</h2>
          <div className="grid grid-cols-3 gap-3 text-center">{[["Technical", data.avg_scores.technical], ["Market", data.avg_scores.market], ["Innovation", data.avg_scores.innovation]].map(([l, v]) => <div key={l as string} className="rounded-lg bg-slate-50 p-3"><div className="text-2xl font-bold text-navy-800">{v}</div><div className="text-xs text-slate-500">{l}</div></div>)}</div>
          <div className="mt-4 flex flex-wrap gap-2">{data.collab_by_status.length === 0 ? <span className="text-sm text-slate-500">No collaboration requests yet.</span> : data.collab_by_status.map((c) => <Badge key={c.status} tone={statusTone(c.status)}>{c.status}: {c.count}</Badge>)}</div>
          <p className="mt-3 text-xs text-slate-500">{t.messages} messages · {t.collab_requests} requests · {t.reference_projects} reference projects</p></Card>
      </div>
      <Card className="mt-6 p-5"><h2 className="mb-3 font-semibold">Recent admin activity</h2>
        {logs.data?.length ? <ul className="divide-y divide-slate-100 text-sm">{logs.data.slice(0, 10).map((l) => <li key={l.id} className="flex justify-between gap-4 py-2"><span><Badge>{l.action}</Badge> <span className="text-slate-600">{l.detail}</span></span><span className="shrink-0 text-xs text-slate-400">{l.admin} · {fmtDateTime(l.created_at)}</span></li>)}</ul> : <p className="text-sm text-slate-500">No activity logged yet.</p>}</Card>
    </div>
  );
}

interface AUser { id: number; email: string; full_name: string; role: string; is_active: boolean; is_verified: boolean; created_at: string; last_login_at: string | null; company_name: string | null; idea_count: number | null }
export function AdminUsers() {
  const toast = useToast();
  const [q, setQ] = useState(""); const [role, setRole] = useState(""); const [page, setPage] = useState(1);
  const dq = useDebounced(q);
  const { data, loading, error, reload } = useLoad(() => api.get<Paged<AUser>>("/admin/users", { q: dq, role, page }), [dq, role, page]);
  const [del, setDel] = useState<AUser | null>(null);
  const patch = async (u: AUser, body: object, ok: string) => { try { await api.patch(`/admin/users/${u.id}`, body); toast.ok(ok); reload(true); } catch (e) { toast.err(errMsg(e)); } };
  const remove = async () => { if (!del) return; try { await api.del(`/admin/users/${del.id}`); toast.ok("User deleted"); setDel(null); reload(true); } catch (e) { toast.err(errMsg(e)); } };
  return (
    <div><PageHeader title="User management" />
      <div className="mb-4 flex flex-wrap gap-3"><input className="input max-w-xs" placeholder="Search name or email…" value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} aria-label="Search users" />
        <select className="input w-44" value={role} onChange={(e) => { setRole(e.target.value); setPage(1); }} aria-label="Role"><option value="">All roles</option><option>creator</option><option>entrepreneur</option><option>admin</option></select></div>
      {loading ? <Spinner /> : error ? <ErrorBox message={error} onRetry={() => reload()} /> : !data?.items.length ? <EmptyState title="No users found" /> : (
        <Card className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm"><thead className="border-b bg-slate-50 text-xs uppercase text-slate-500"><tr><th className="px-4 py-3">User</th><th className="px-4 py-3">Role</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Joined</th><th className="px-4 py-3 text-right">Actions</th></tr></thead>
          <tbody className="divide-y divide-slate-100">{data.items.map((u) => (
            <tr key={u.id}><td className="px-4 py-3"><div className="font-medium text-navy-900">{u.full_name}</div><div className="text-xs text-slate-500">{u.email}{u.company_name && ` · ${u.company_name}`}</div></td>
              <td className="px-4 py-3"><Badge tone="indigo">{u.role}</Badge>{u.role === "entrepreneur" && <Badge tone={u.is_verified ? "green" : "amber"} className="ml-1">{u.is_verified ? "verified" : "unverified"}</Badge>}</td>
              <td className="px-4 py-3"><Badge tone={u.is_active ? "green" : "red"}>{u.is_active ? "active" : "deactivated"}</Badge></td><td className="px-4 py-3 text-slate-500">{fmtDate(u.created_at)}</td>
              <td className="px-4 py-3"><div className="flex justify-end gap-1">
                {u.role === "entrepreneur" && <Button size="sm" variant="secondary" onClick={() => patch(u, { is_verified: !u.is_verified }, u.is_verified ? "Verification removed" : "Entrepreneur verified")}><ShieldCheck className="h-3.5 w-3.5" />{u.is_verified ? "Unverify" : "Verify"}</Button>}
                {u.role !== "admin" && <><Button size="sm" variant="secondary" onClick={() => patch(u, { is_active: !u.is_active }, u.is_active ? "User deactivated" : "User activated")}>{u.is_active ? "Deactivate" : "Activate"}</Button><Button size="sm" variant="ghost" onClick={() => setDel(u)}>Delete</Button></>}</div></td></tr>))}</tbody></table></Card>)}
      <Pagination page={page} total={data?.total ?? 0} pageSize={25} onPage={setPage} />
      <Modal open={!!del} onClose={() => setDel(null)} title="Delete user?"><p className="text-sm text-slate-600">This permanently deletes <b>{del?.full_name}</b> and all their ideas, messages and requests.</p>
        <div className="mt-5 flex justify-end gap-2"><Button variant="secondary" onClick={() => setDel(null)}>Cancel</Button><Button variant="danger" onClick={remove}>Delete</Button></div></Modal>
    </div>
  );
}

interface AIdea { id: number; title: string; industry: string; visibility: string; moderation_status: string; stage: string; created_at: string; creator: UserBrief; overall_score: number | null; open_reports: number }
export function AdminIdeas() {
  const toast = useToast();
  const [q, setQ] = useState(""); const [status, setStatus] = useState(""); const [page, setPage] = useState(1);
  const dq = useDebounced(q);
  const { data, loading, error, reload } = useLoad(() => api.get<Paged<AIdea>>("/admin/ideas", { q: dq, status, page }), [dq, status, page]);
  const setMod = async (i: AIdea, s: string) => { try { await api.patch(`/admin/ideas/${i.id}`, { moderation_status: s }); toast.ok(`Idea set to ${s}`); reload(true); } catch (e) { toast.err(errMsg(e)); } };
  const remove = async (i: AIdea) => { if (!window.confirm(`Permanently delete “${i.title}”?`)) return; try { await api.del(`/admin/ideas/${i.id}`); toast.ok("Idea deleted"); reload(true); } catch (e) { toast.err(errMsg(e)); } };
  return (
    <div><PageHeader title="Idea management" />
      <div className="mb-4 flex flex-wrap gap-3"><input className="input max-w-xs" placeholder="Search title…" value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} aria-label="Search ideas" />
        <select className="input w-44" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }} aria-label="Moderation status"><option value="">All statuses</option><option>active</option><option>hidden</option><option>removed</option></select></div>
      {loading ? <Spinner /> : error ? <ErrorBox message={error} onRetry={() => reload()} /> : !data?.items.length ? <EmptyState title="No ideas found" /> : (
        <Card className="overflow-x-auto"><table className="w-full min-w-[820px] text-left text-sm"><thead className="border-b bg-slate-50 text-xs uppercase text-slate-500"><tr><th className="px-4 py-3">Idea</th><th className="px-4 py-3">Creator</th><th className="px-4 py-3">Visibility</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Score</th><th className="px-4 py-3 text-right">Actions</th></tr></thead>
          <tbody className="divide-y divide-slate-100">{data.items.map((i) => (
            <tr key={i.id}><td className="px-4 py-3"><Link to={`/app/admin/ideas/${i.id}`} className="font-medium text-navy-900 hover:underline">{i.title}</Link><div className="text-xs text-slate-500">{i.industry} · {fmtDate(i.created_at)}</div>{i.open_reports > 0 && <Badge tone="red">{i.open_reports} report(s)</Badge>}</td>
              <td className="px-4 py-3">{i.creator.name}</td><td className="px-4 py-3"><Badge tone={statusTone(i.visibility)}>{i.visibility}</Badge></td><td className="px-4 py-3"><Badge tone={statusTone(i.moderation_status)}>{i.moderation_status}</Badge></td><td className="px-4 py-3">{i.overall_score ?? "–"}</td>
              <td className="px-4 py-3"><div className="flex justify-end gap-1">{i.moderation_status !== "active" && <Button size="sm" variant="secondary" onClick={() => setMod(i, "active")}>Restore</Button>}
                {i.moderation_status === "active" && <Button size="sm" variant="secondary" onClick={() => setMod(i, "hidden")}>Hide</Button>}{i.moderation_status !== "removed" && <Button size="sm" variant="secondary" onClick={() => setMod(i, "removed")}>Remove</Button>}<Button size="sm" variant="ghost" onClick={() => remove(i)}>Delete</Button></div></td></tr>))}</tbody></table></Card>)}
      <Pagination page={page} total={data?.total ?? 0} pageSize={25} onPage={setPage} />
    </div>
  );
}

interface AReport { id: number; reason: string; details: string; status: string; created_at: string; reporter: UserBrief; resolution_note: string; idea: { id: number; title: string; short_description: string; moderation_status: string; creator: UserBrief } }
export function AdminReports() {
  const toast = useToast();
  const [status, setStatus] = useState("open");
  const { data, loading, error, reload } = useLoad(() => api.get<AReport[]>("/admin/reports", { status }), [status]);
  const [sel, setSel] = useState<{ r: AReport; action: string } | null>(null); const [note, setNote] = useState("");
  const resolve = async (e: FormEvent) => { e.preventDefault(); if (!sel) return; try { await api.post(`/admin/reports/${sel.r.id}/resolve`, { action: sel.action, note }); toast.ok("Report resolved"); setSel(null); setNote(""); reload(true); } catch (er) { toast.err(errMsg(er)); } };
  return (
    <div><PageHeader title="Reports & moderation" subtitle="Content reported by users." />
      <Tabs value={status} onChange={setStatus} tabs={[{ id: "open", label: "Open" }, { id: "actioned", label: "Actioned" }, { id: "dismissed", label: "Dismissed" }]} />
      {loading ? <Spinner /> : error ? <ErrorBox message={error} onRetry={() => reload()} /> : !data?.length ? <EmptyState icon={<Flag className="h-6 w-6" />} title="Nothing here" text="No reports with this status." /> : (
        <div className="space-y-4">{data.map((r) => (
          <Card key={r.id} className="p-5"><div className="flex flex-wrap items-start justify-between gap-3"><div><div className="flex flex-wrap items-center gap-2"><Badge tone="red">{r.reason}</Badge><Link to={`/app/admin/ideas/${r.idea.id}`} className="font-semibold text-navy-900 hover:underline">{r.idea.title}</Link><Badge tone={statusTone(r.idea.moderation_status)}>{r.idea.moderation_status}</Badge></div>
            <p className="mt-1 text-xs text-slate-500">Reported by {r.reporter.name} · {fmtDateTime(r.created_at)} · creator: {r.idea.creator.name}</p></div>
            {r.status === "open" && <div className="flex gap-2"><Button size="sm" variant="secondary" onClick={() => setSel({ r, action: "dismiss" })}>Dismiss</Button><Button size="sm" variant="secondary" onClick={() => setSel({ r, action: "hide_idea" })}>Hide idea</Button><Button size="sm" variant="danger" onClick={() => setSel({ r, action: "remove_idea" })}>Remove idea</Button></div>}</div>
            {r.details && <p className="mt-3 rounded-lg bg-slate-50 p-3 text-sm text-slate-700">{r.details}</p>}{r.resolution_note && <p className="mt-2 text-sm text-slate-600">Resolution: {r.resolution_note}</p>}</Card>))}</div>)}
      <Modal open={!!sel} onClose={() => setSel(null)} title={`Resolve: ${sel?.action.replace("_", " ")}`}><form onSubmit={resolve} className="space-y-4"><Field label="Note (shown to the creator if the idea is actioned)"><textarea className="input" rows={3} value={note} onChange={(e) => setNote(e.target.value)} /></Field><div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={() => setSel(null)}>Cancel</Button><Button type="submit">Confirm</Button></div></form></Modal>
    </div>
  );
}

interface ACat { id: number; name: string; kind: string; description: string; is_active: boolean; idea_count: number | null }
export function AdminCategories() {
  const toast = useToast();
  const { data, loading, error, reload } = useLoad(() => api.get<ACat[]>("/admin/categories"), []);
  const [f, setF] = useState({ name: "", kind: "industry", description: "" }); const [edit, setEdit] = useState<ACat | null>(null);
  const add = async (e: FormEvent) => { e.preventDefault(); try { await api.post("/admin/categories", f); setF({ ...f, name: "", description: "" }); toast.ok("Category added"); reload(true); } catch (er) { toast.err(errMsg(er)); } };
  const toggle = async (c: ACat) => { try { await api.patch(`/admin/categories/${c.id}`, { is_active: !c.is_active }); reload(true); } catch (er) { toast.err(errMsg(er)); } };
  const rename = async (e: FormEvent) => { e.preventDefault(); if (!edit) return; try { await api.patch(`/admin/categories/${edit.id}`, { name: edit.name, description: edit.description }); setEdit(null); toast.ok("Category updated"); reload(true); } catch (er) { toast.err(errMsg(er)); } };
  const remove = async (c: ACat) => { if (!window.confirm(`Delete “${c.name}”?`)) return; try { await api.del(`/admin/categories/${c.id}`); toast.ok("Deleted"); reload(true); } catch (er) { toast.err(errMsg(er)); } };
  return (
    <div><PageHeader title="Category management" subtitle="Industries and technologies available on the submission form and filters." />
      <Card className="mb-6 p-5"><form onSubmit={add} className="grid gap-3 sm:grid-cols-[1fr_140px_1fr_auto] sm:items-end"><Field label="Name"><input className="input" required minLength={2} value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></Field>
        <Field label="Kind"><select className="input" value={f.kind} onChange={(e) => setF({ ...f, kind: e.target.value })}><option>industry</option><option>technology</option></select></Field>
        <Field label="Description"><input className="input" value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} /></Field><Button type="submit">Add</Button></form></Card>
      {loading ? <Spinner /> : error ? <ErrorBox message={error} onRetry={() => reload()} /> : (
        <div className="grid gap-5 md:grid-cols-2">{["industry", "technology"].map((k) => (
          <Card key={k} className="p-5"><h2 className="mb-3 font-semibold capitalize">{k}s</h2><ul className="divide-y divide-slate-100">{(data ?? []).filter((c) => c.kind === k).map((c) => (
            <li key={c.id} className="flex items-center justify-between gap-2 py-2 text-sm"><div className={c.is_active ? "" : "text-slate-400 line-through"}>{c.name}{c.idea_count ? <span className="ml-2 text-xs text-slate-400">{c.idea_count} ideas</span> : null}</div>
              <div className="flex gap-1"><Button size="sm" variant="ghost" onClick={() => setEdit(c)}>Edit</Button><Button size="sm" variant="ghost" onClick={() => toggle(c)}>{c.is_active ? "Deactivate" : "Activate"}</Button><Button size="sm" variant="ghost" onClick={() => remove(c)}>Delete</Button></div></li>))}</ul></Card>))}</div>)}
      <Modal open={!!edit} onClose={() => setEdit(null)} title="Edit category">{edit && <form onSubmit={rename} className="space-y-4"><Field label="Name"><input className="input" required value={edit.name} onChange={(e) => setEdit({ ...edit, name: e.target.value })} /></Field>
        <Field label="Description"><input className="input" value={edit.description} onChange={(e) => setEdit({ ...edit, description: e.target.value })} /></Field><div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={() => setEdit(null)}>Cancel</Button><Button type="submit">Save</Button></div></form>}</Modal>
    </div>
  );
}
