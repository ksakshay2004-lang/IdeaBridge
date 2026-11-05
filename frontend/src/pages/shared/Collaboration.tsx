import { useState } from "react";
import { Link } from "react-router-dom";
import { Handshake, MessageSquare } from "lucide-react";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { useLoad } from "../../lib/hooks";
import type { Collab } from "../../lib/types";
import { Badge, Button, Card, EmptyState, ErrorBox, Field, Modal, PageHeader, Spinner, Tabs, statusTone, useToast } from "../../components/ui";
import { errMsg, fmtDate } from "../../lib/utils";

export default function Collaboration() {
  const { user } = useAuth();
  const toast = useToast();
  const isCreator = user?.role === "creator";
  const base = `/app/${user?.role}`;
  const [tab, setTab] = useState("all");
  const [target, setTarget] = useState<{ c: Collab; action: "accept" | "decline" } | null>(null);
  const [note, setNote] = useState(""); const [busy, setBusy] = useState(false);
  const { data, loading, error, reload } = useLoad(() => api.get<Collab[]>("/collaboration"), []);
  const shown = (data ?? []).filter((c) => tab === "all" || c.status === tab);
  const count = (s: string) => (data ?? []).filter((c) => c.status === s).length;

  const respond = async () => {
    if (!target) return; setBusy(true);
    try { await api.post(`/collaboration/${target.c.id}/respond`, { action: target.action, message: note }); toast.ok(target.action === "accept" ? "Request accepted" : "Request declined"); setTarget(null); setNote(""); reload(true); }
    catch (e) { toast.err(errMsg(e)); } finally { setBusy(false); }
  };
  const withdraw = async (c: Collab) => { try { await api.post(`/collaboration/${c.id}/withdraw`); toast.ok("Request withdrawn"); reload(true); } catch (e) { toast.err(errMsg(e)); } };

  return (
    <div>
      <PageHeader title="Collaboration requests" subtitle={isCreator ? "People who want to collaborate on, fund or develop your ideas." : "Requests you have sent to idea creators."} />
      <Tabs value={tab} onChange={setTab} tabs={[{ id: "all", label: "All", count: data?.length }, { id: "pending", label: "Pending", count: count("pending") }, { id: "accepted", label: "Accepted", count: count("accepted") }, { id: "declined", label: "Declined", count: count("declined") }, { id: "withdrawn", label: "Withdrawn", count: count("withdrawn") }]} />
      {loading ? <Spinner /> : error ? <ErrorBox message={error} onRetry={() => reload()} /> : shown.length === 0 ?
        <EmptyState icon={<Handshake className="h-6 w-6" />} title="No requests here" text={isCreator ? "When an entrepreneur reaches out about one of your ideas, it will show up here." : "Find an idea you like and send a collaboration request."} action={!isCreator && <Link to={`${base}/discover`}><Button>Discover ideas</Button></Link>} /> : (
          <div className="space-y-4">{shown.map((c) => {
            const other = isCreator ? c.entrepreneur : c.creator;
            return (
              <Card key={c.id} className="p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div><div className="flex flex-wrap items-center gap-2"><Badge tone={statusTone(c.status)}>{c.status}</Badge><Badge tone="indigo">{c.kind}</Badge>
                    <Link to={`${base}/ideas/${c.idea_id}`} className="font-semibold text-navy-900 hover:underline">{c.idea_title}</Link></div>
                    <p className="mt-1 text-xs text-slate-500">{isCreator ? "From" : "To"} <span className="font-medium text-slate-700">{other.name}</span>{other.headline && ` (${other.headline})`}{other.is_verified && <span className="ml-1 text-emerald-700">✓ verified</span>} · {fmtDate(c.created_at)}</p></div>
                  <div className="flex flex-wrap gap-2">
                    <Link to={`${base}/messages?with=${other.id}`}><Button size="sm" variant="secondary"><MessageSquare className="h-4 w-4" />Message</Button></Link>
                    {isCreator && c.status === "pending" && <><Button size="sm" variant="success" onClick={() => setTarget({ c, action: "accept" })}>Accept</Button><Button size="sm" variant="secondary" onClick={() => setTarget({ c, action: "decline" })}>Decline</Button></>}
                    {!isCreator && ["pending", "accepted"].includes(c.status) && <Button size="sm" variant="ghost" onClick={() => withdraw(c)}>Withdraw</Button>}
                  </div>
                </div>
                <p className="mt-3 whitespace-pre-line rounded-lg bg-slate-50 p-3 text-sm text-slate-700">{c.message}</p>
                {c.response_message && <p className="mt-2 text-sm text-slate-600"><span className="font-medium">Reply:</span> {c.response_message}</p>}
              </Card>);
          })}</div>)}
      <Modal open={!!target} onClose={() => setTarget(null)} title={target?.action === "accept" ? "Accept request" : "Decline request"}>
        {target?.action === "accept" && <p className="mb-3 text-sm text-slate-600">Accepting unlocks the full idea, documents and AI report for this person if the idea is restricted.</p>}
        <Field label="Message (optional)"><textarea className="input" rows={3} value={note} onChange={(e) => setNote(e.target.value)} /></Field>
        <div className="mt-4 flex justify-end gap-2"><Button variant="secondary" onClick={() => setTarget(null)}>Cancel</Button><Button variant={target?.action === "accept" ? "success" : "danger"} loading={busy} onClick={respond}>{target?.action === "accept" ? "Accept" : "Decline"}</Button></div>
      </Modal>
    </div>
  );
}
