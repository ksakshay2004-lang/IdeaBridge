import { FormEvent, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { MessageSquare, Send } from "lucide-react";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { useLoad } from "../../lib/hooks";
import type { Conversation, Msg, UserBrief } from "../../lib/types";
import { Card, EmptyState, ErrorBox, PageHeader, Spinner, useToast, Button } from "../../components/ui";
import { cx, errMsg, fmtDateTime } from "../../lib/utils";

interface Thread { user: UserBrief; can_send: boolean; messages: Msg[] }

export default function Messages() {
  const { user } = useAuth();
  const toast = useToast();
  const [params, setParams] = useSearchParams();
  const withId = params.get("with") ? Number(params.get("with")) : null;
  const [thread, setThread] = useState<Thread | null>(null);
  const [tLoading, setTLoading] = useState(false); const [tError, setTError] = useState("");
  const [body, setBody] = useState(""); const [sending, setSending] = useState(false);
  const bottom = useRef<HTMLDivElement>(null);
  const convs = useLoad(() => api.get<Conversation[]>("/messages/conversations"), []);

  const loadThread = async (silent = false) => {
    if (!withId) { setThread(null); return; }
    if (!silent) setTLoading(true);
    try { setThread(await api.get<Thread>(`/messages/thread/${withId}`)); setTError(""); } catch (e) { setTError(errMsg(e)); } finally { setTLoading(false); }
  };
  useEffect(() => { loadThread(); convs.reload(true); /* eslint-disable-next-line */ }, [withId]);
  useEffect(() => { const t = setInterval(() => { loadThread(true); convs.reload(true); }, 8000); return () => clearInterval(t); /* eslint-disable-next-line */ }, [withId]);
  useEffect(() => { bottom.current?.scrollIntoView({ behavior: "smooth" }); }, [thread?.messages.length]);

  const send = async (e: FormEvent) => {
    e.preventDefault(); if (!body.trim() || !withId) return; setSending(true);
    try { await api.post("/messages", { recipient_id: withId, body }); setBody(""); await loadThread(true); convs.reload(true); } catch (err) { toast.err(errMsg(err)); } finally { setSending(false); }
  };
  const list = convs.data ?? [];
  const known = list.some((c) => c.user_id === withId);

  return (
    <div>
      <PageHeader title="Messages" subtitle="Direct conversations with creators and entrepreneurs." />
      <Card className="grid h-[70vh] min-h-[420px] overflow-hidden md:grid-cols-[280px_1fr]">
        <div className={cx("overflow-y-auto border-r border-slate-200", withId && "hidden md:block")}>
          {convs.loading ? <Spinner /> : convs.error ? <div className="p-3"><ErrorBox message={convs.error} /></div> : (list.length === 0 && !withId) ? <p className="p-6 text-center text-sm text-slate-500">No conversations yet.{user?.role === "entrepreneur" && " Open an idea and choose “Contact creator”."}</p> :
            <>{withId && !known && thread && <button className="block w-full border-b border-slate-100 bg-navy-50 px-4 py-3 text-left text-sm font-medium">{thread.user.name} <span className="text-xs text-slate-500">(new)</span></button>}
              {list.map((c) => (
                <button key={c.user_id} onClick={() => setParams({ with: String(c.user_id) })} className={cx("block w-full border-b border-slate-100 px-4 py-3 text-left hover:bg-slate-50", c.user_id === withId && "bg-navy-50")}>
                  <div className="flex items-center justify-between"><span className="truncate text-sm font-semibold text-navy-900">{c.user.name}</span>{c.unread > 0 && <span className="rounded-full bg-rose-600 px-1.5 text-[10px] font-bold text-white">{c.unread}</span>}</div>
                  <div className="truncate text-xs text-slate-500">{c.last_from_me && "You: "}{c.last_message}</div></button>))}</>}
        </div>
        <div className={cx("flex min-h-0 flex-col", !withId && "hidden md:flex")}>
          {!withId ? <div className="m-auto"><EmptyState icon={<MessageSquare className="h-6 w-6" />} title="Select a conversation" /></div> : tLoading && !thread ? <Spinner /> : tError ? <div className="p-4"><ErrorBox message={tError} /></div> : thread && (
            <>
              <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3"><div><div className="font-semibold">{thread.user.name}</div><div className="text-xs text-slate-500">{thread.user.headline} · {thread.user.role}</div></div>
                <button className="text-xs text-navy-700 md:hidden" onClick={() => setParams({})}>All chats</button></div>
              <div className="flex-1 space-y-3 overflow-y-auto bg-slate-50 p-4">
                {thread.messages.length === 0 && <p className="text-center text-sm text-slate-400">No messages yet. Say hello!</p>}
                {thread.messages.map((m) => { const mine = m.sender_id === user?.id; return (
                  <div key={m.id} className={cx("flex", mine ? "justify-end" : "justify-start")}><div className={cx("max-w-[80%] rounded-2xl px-4 py-2 text-sm", mine ? "bg-navy-700 text-white" : "bg-white text-slate-800 shadow-sm")}>
                    <p className="whitespace-pre-wrap break-words">{m.body}</p><div className={cx("mt-1 text-[10px]", mine ? "text-navy-200" : "text-slate-400")}>{fmtDateTime(m.created_at)}</div></div></div>); })}
                <div ref={bottom} />
              </div>
              {thread.can_send ? (
                <form onSubmit={send} className="flex gap-2 border-t border-slate-200 p-3"><input className="input" placeholder="Write a message…" maxLength={5000} value={body} onChange={(e) => setBody(e.target.value)} aria-label="Message" />
                  <Button type="submit" loading={sending} disabled={!body.trim()} aria-label="Send"><Send className="h-4 w-4" /></Button></form>) :
                <p className="border-t border-slate-200 p-3 text-center text-xs text-slate-500">You can reply once this person contacts you or you have a collaboration request together.</p>}
            </>)}
        </div>
      </Card>
    </div>
  );
}
