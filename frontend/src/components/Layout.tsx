import { ReactNode, useEffect, useRef, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { Bell, BarChart3, Bookmark, Building2, Compass, FileText, FolderKanban, Handshake, LayoutDashboard, LogOut, Menu, MessageSquare, PlusCircle,
  Settings, Shield, Sparkles, Tags, Users, X, Flag, Lightbulb } from "lucide-react";
import { useAuth, homePath } from "../lib/auth";
import { api } from "../lib/api";
import type { Notice, SystemStatus } from "../lib/types";
import { cx, fmtDateTime } from "../lib/utils";
import { useLoad } from "../lib/hooks";
import { Button } from "./ui";

export const Logo = ({ light }: { light?: boolean }) => (
  <Link to="/" className="flex items-center gap-2 font-bold" aria-label="IdeaBridge home">
    <span className="grid h-8 w-8 place-items-center rounded-lg bg-navy-700 text-white"><Lightbulb className="h-4 w-4" /></span>
    <span className={cx("text-lg tracking-tight", light ? "text-white" : "text-navy-900")}>Idea<span className="text-navy-500">Bridge</span></span>
  </Link>
);

export function PublicLayout() {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const loc = useLocation();
  useEffect(() => setOpen(false), [loc.pathname]);
  const links = [["/explore", "Explore Ideas"], ["/how-it-works", "How it works"], ["/about", "About"]];
  const { data: status } = useLoad(() => api.get<SystemStatus>("/system/status"), []);
  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6">
          <Logo />
          <nav className="hidden items-center gap-1 md:flex" aria-label="Main">
            {links.map(([to, label]) => <NavLink key={to} to={to} className={({ isActive }) => cx("rounded-lg px-3 py-2 text-sm font-medium", isActive ? "text-navy-800 bg-navy-50" : "text-slate-600 hover:text-navy-800")}>{label}</NavLink>)}
          </nav>
          <div className="hidden items-center gap-2 md:flex">
            {user ? <Link to={homePath(user)}><Button>Dashboard</Button></Link> : <>
              <Link to="/login"><Button variant="ghost">Log in</Button></Link><Link to="/register"><Button>Get started</Button></Link></>}
          </div>
          <button className="md:hidden" aria-label="Toggle menu" onClick={() => setOpen(!open)}>{open ? <X /> : <Menu />}</button>
        </div>
        {open && (
          <div className="space-y-1 border-t border-slate-200 bg-white px-4 py-3 md:hidden">
            {links.map(([to, label]) => <Link key={to} to={to} className="block rounded-lg px-3 py-2 text-sm font-medium text-slate-700">{label}</Link>)}
            {user ? <Link to={homePath(user)} className="block rounded-lg px-3 py-2 text-sm font-semibold text-navy-700">Dashboard</Link> : <>
              <Link to="/login" className="block rounded-lg px-3 py-2 text-sm font-medium">Log in</Link>
              <Link to="/register" className="block rounded-lg px-3 py-2 text-sm font-semibold text-navy-700">Get started</Link></>}
          </div>
        )}
      </header>
      {status?.evaluation_mode === "demo" && (
        <div className="bg-amber-100 px-4 py-1.5 text-center text-xs text-amber-900">{status.demo_notice}</div>
      )}
      <main className="flex-1"><Outlet /></main>
      <footer className="bg-navy-950 text-slate-300">
        <div className="mx-auto grid max-w-7xl gap-8 px-4 py-12 sm:px-6 md:grid-cols-4">
          <div className="md:col-span-2"><Logo light /><p className="mt-3 max-w-sm text-sm text-slate-400">The marketplace where great ideas meet the people who can build them – with an AI agent that checks novelty and feasibility first.</p></div>
          <div><h4 className="mb-3 text-sm font-semibold text-white">Platform</h4><ul className="space-y-2 text-sm"><li><Link to="/explore" className="hover:text-white">Explore ideas</Link></li><li><Link to="/how-it-works" className="hover:text-white">How it works</Link></li><li><Link to="/about" className="hover:text-white">About</Link></li></ul></div>
          <div><h4 className="mb-3 text-sm font-semibold text-white">Account</h4><ul className="space-y-2 text-sm"><li><Link to="/login" className="hover:text-white">Log in</Link></li><li><Link to="/register" className="hover:text-white">Create account</Link></li></ul></div>
        </div>
        <div className="border-t border-white/10 py-4 text-center text-xs text-slate-500">© {new Date().getFullYear()} IdeaBridge. AI evaluations are decision-support tools, not legal, financial or investment advice.</div>
      </footer>
    </div>
  );
}

type NavItem = { to: string; label: string; icon: ReactNode; end?: boolean };
const NAV: Record<string, NavItem[]> = {
  creator: [
    { to: "/app/creator", label: "Overview", icon: <LayoutDashboard className="h-4 w-4" />, end: true },
    { to: "/app/creator/submit", label: "Submit New Idea", icon: <PlusCircle className="h-4 w-4" /> },
    { to: "/app/creator/ideas", label: "My Ideas", icon: <FolderKanban className="h-4 w-4" /> },
    { to: "/app/creator/reports", label: "AI Evaluation Reports", icon: <Sparkles className="h-4 w-4" /> },
    { to: "/app/creator/collaboration", label: "Collaboration Requests", icon: <Handshake className="h-4 w-4" /> },
    { to: "/app/creator/messages", label: "Messages", icon: <MessageSquare className="h-4 w-4" /> },
    { to: "/app/creator/profile", label: "Profile & Settings", icon: <Settings className="h-4 w-4" /> },
  ],
  entrepreneur: [
    { to: "/app/entrepreneur", label: "Overview", icon: <LayoutDashboard className="h-4 w-4" />, end: true },
    { to: "/app/entrepreneur/discover", label: "Discover Ideas", icon: <Compass className="h-4 w-4" /> },
    { to: "/app/entrepreneur/recommended", label: "Recommended Ideas", icon: <Sparkles className="h-4 w-4" /> },
    { to: "/app/entrepreneur/saved", label: "Saved Ideas", icon: <Bookmark className="h-4 w-4" /> },
    { to: "/app/entrepreneur/collaboration", label: "Collaboration Requests", icon: <Handshake className="h-4 w-4" /> },
    { to: "/app/entrepreneur/messages", label: "Messages", icon: <MessageSquare className="h-4 w-4" /> },
    { to: "/app/entrepreneur/profile", label: "Company Profile", icon: <Building2 className="h-4 w-4" /> },
  ],
  admin: [
    { to: "/app/admin", label: "Analytics", icon: <BarChart3 className="h-4 w-4" />, end: true },
    { to: "/app/admin/users", label: "User Management", icon: <Users className="h-4 w-4" /> },
    { to: "/app/admin/ideas", label: "Idea Management", icon: <FileText className="h-4 w-4" /> },
    { to: "/app/admin/reports", label: "Reports & Moderation", icon: <Flag className="h-4 w-4" /> },
    { to: "/app/admin/categories", label: "Category Management", icon: <Tags className="h-4 w-4" /> },
  ],
};

function NotificationBell() {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<Notice[]>([]);
  const [counts, setCounts] = useState({ notifications: 0, messages: 0 });
  const ref = useRef<HTMLDivElement>(null);
  const nav = useNavigate();
  const poll = () => api.get<{ notifications: number; messages: number }>("/notifications/unread-count").then(setCounts).catch(() => {});
  useEffect(() => { poll(); const t = setInterval(poll, 20000); return () => clearInterval(t); }, []);
  useEffect(() => {
    const h = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", h); return () => document.removeEventListener("mousedown", h);
  }, []);
  const toggle = async () => { const next = !open; setOpen(next); if (next) setItems(await api.get<Notice[]>("/notifications").catch(() => [])); };
  const go = async (n: Notice) => { if (!n.is_read) await api.post(`/notifications/${n.id}/read`).catch(() => {}); setOpen(false); poll(); if (n.link) nav(n.link); };
  const readAll = async () => { await api.post("/notifications/read-all"); setItems(items.map((i) => ({ ...i, is_read: true }))); poll(); };
  const total = counts.notifications;
  return (
    <div className="relative" ref={ref}>
      <button onClick={toggle} aria-label={`Notifications (${total} unread)`} className="relative rounded-lg p-2 text-slate-600 hover:bg-slate-100">
        <Bell className="h-5 w-5" />
        {total > 0 && <span className="absolute right-1 top-1 grid h-4 min-w-4 place-items-center rounded-full bg-rose-600 px-1 text-[10px] font-bold text-white">{total > 9 ? "9+" : total}</span>}
      </button>
      {open && (
        <div className="absolute right-0 z-50 mt-2 w-80 animate-fadeUp rounded-xl border border-slate-200 bg-white shadow-xl">
          <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3"><span className="text-sm font-semibold">Notifications</span>
            <button onClick={readAll} className="text-xs text-navy-600 hover:underline">Mark all read</button></div>
          <div className="max-h-96 overflow-y-auto">
            {items.length === 0 ? <p className="p-6 text-center text-sm text-slate-500">You're all caught up.</p> : items.map((n) => (
              <button key={n.id} onClick={() => go(n)} className={cx("block w-full border-b border-slate-50 px-4 py-3 text-left hover:bg-slate-50", !n.is_read && "bg-navy-50/60")}>
                <div className="text-sm font-medium text-navy-900">{n.title}</div><div className="line-clamp-2 text-xs text-slate-600">{n.body}</div>
                <div className="mt-1 text-[11px] text-slate-400">{fmtDateTime(n.created_at)}</div></button>))}
          </div>
        </div>
      )}
    </div>
  );
}

export function DashboardLayout() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const [open, setOpen] = useState(false);
  const loc = useLocation();
  useEffect(() => setOpen(false), [loc.pathname]);
  if (!user) return null;
  const items = NAV[user.role] ?? [];
  const sidebar = (
    <nav className="flex h-full flex-col" aria-label="Dashboard">
      <div className="px-4 py-5"><Logo light /></div>
      <div className="mx-3 mb-3 rounded-lg bg-white/5 px-3 py-2 text-xs text-slate-300">
        <div className="flex items-center gap-1 font-semibold capitalize text-white">{user.role === "admin" && <Shield className="h-3 w-3" />}{user.role}</div>
        <div className="truncate">{user.full_name}</div>
        {user.role === "entrepreneur" && <div className={user.is_verified ? "text-emerald-300" : "text-amber-300"}>{user.is_verified ? "✓ Verified" : "Verification pending"}</div>}
      </div>
      <ul className="flex-1 space-y-0.5 px-3">
        {items.map((i) => (
          <li key={i.to}><NavLink to={i.to} end={i.end} className={({ isActive }) => cx("flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition", isActive ? "bg-white/10 text-white" : "text-slate-300 hover:bg-white/5 hover:text-white")}>{i.icon}{i.label}</NavLink></li>
        ))}
      </ul>
      <button onClick={() => { logout(); nav("/"); }} className="m-3 flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-slate-300 hover:bg-white/5 hover:text-white"><LogOut className="h-4 w-4" />Log out</button>
    </nav>
  );
  return (
    <div className="min-h-screen lg:flex">
      <aside className="hidden w-64 shrink-0 bg-navy-900 lg:block"><div className="sticky top-0 h-screen overflow-y-auto">{sidebar}</div></aside>
      {open && <div className="fixed inset-0 z-50 lg:hidden"><div className="absolute inset-0 bg-navy-950/60" onClick={() => setOpen(false)} /><aside className="absolute left-0 top-0 h-full w-64 bg-navy-900">{sidebar}</aside></div>}
      <div className="min-w-0 flex-1">
        <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-slate-200 bg-white/90 px-4 backdrop-blur sm:px-6">
          <button className="lg:hidden" aria-label="Open menu" onClick={() => setOpen(true)}><Menu /></button>
          <div className="hidden text-sm text-slate-500 lg:block">Welcome back, <span className="font-medium text-navy-900">{user.full_name.split(" ")[0]}</span></div>
          <div className="flex items-center gap-2"><Link to="/explore" className="hidden text-sm text-slate-600 hover:text-navy-800 sm:block">Public site</Link><NotificationBell /></div>
        </header>
        <main className="mx-auto max-w-6xl animate-fadeUp p-4 sm:p-6"><Outlet /></main>
      </div>
    </div>
  );
}
