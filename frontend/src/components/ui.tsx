import { createContext, useCallback, useContext, useEffect, useState, ReactNode, ButtonHTMLAttributes } from "react";
import { AlertTriangle, CheckCircle2, Inbox, Loader2, X, XCircle } from "lucide-react";
import { cx, scoreColor } from "../lib/utils";

type Variant = "primary" | "secondary" | "ghost" | "danger" | "success";
const VARIANTS: Record<Variant, string> = {
  primary: "bg-navy-700 text-white hover:bg-navy-800 focus-visible:outline-navy-500",
  secondary: "bg-white text-navy-800 border border-slate-300 hover:bg-slate-50",
  ghost: "text-navy-700 hover:bg-navy-50",
  danger: "bg-rose-600 text-white hover:bg-rose-700",
  success: "bg-emerald-600 text-white hover:bg-emerald-700",
};
export function Button({ variant = "primary", size = "md", loading, className, children, disabled, ...rest }:
  ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: "sm" | "md" | "lg"; loading?: boolean }) {
  return (
    <button {...rest} disabled={disabled || loading}
      className={cx("inline-flex items-center justify-center gap-2 rounded-lg font-medium transition disabled:cursor-not-allowed disabled:opacity-60",
        size === "sm" ? "px-3 py-1.5 text-xs" : size === "lg" ? "px-6 py-3 text-base" : "px-4 py-2 text-sm", VARIANTS[variant], className)}>
      {loading && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}{children}
    </button>
  );
}

export const Card = ({ className, children }: { className?: string; children: ReactNode }) =>
  <div className={cx("rounded-xl border border-slate-200 bg-white shadow-card", className)}>{children}</div>;

const TONES: Record<string, string> = {
  slate: "bg-slate-100 text-slate-700", indigo: "bg-navy-100 text-navy-800", green: "bg-emerald-100 text-emerald-800",
  amber: "bg-amber-100 text-amber-900", red: "bg-rose-100 text-rose-800", sky: "bg-sky-100 text-sky-800",
};
export const Badge = ({ tone = "slate", children, className }: { tone?: keyof typeof TONES | string; children: ReactNode; className?: string }) =>
  <span className={cx("inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium", TONES[tone] ?? TONES.slate, className)}>{children}</span>;

export const statusTone = (s: string) => ({ pending: "amber", accepted: "green", declined: "red", withdrawn: "slate", completed: "green", failed: "red",
  running: "sky", queued: "slate", active: "green", hidden: "amber", removed: "red", open: "amber", dismissed: "slate", actioned: "green",
  public: "green", restricted: "amber", private: "slate" } as Record<string, string>)[s] ?? "slate";

export function Spinner({ label = "Loading…" }: { label?: string }) {
  return <div className="flex items-center justify-center gap-2 py-16 text-sm text-slate-500" role="status"><Loader2 className="h-5 w-5 animate-spin" />{label}</div>;
}
export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex items-start gap-3 rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
      <XCircle className="mt-0.5 h-5 w-5 shrink-0" /><div className="flex-1">{message}</div>
      {onRetry && <button onClick={onRetry} className="font-medium underline">Retry</button>}
    </div>
  );
}
export function EmptyState({ title, text, action, icon }: { title: string; text?: string; action?: ReactNode; icon?: ReactNode }) {
  return (
    <div className="flex flex-col items-center rounded-xl border border-dashed border-slate-300 bg-white px-6 py-14 text-center">
      <div className="mb-3 rounded-full bg-navy-50 p-3 text-navy-600">{icon ?? <Inbox className="h-6 w-6" />}</div>
      <h3 className="font-semibold text-navy-900">{title}</h3>
      {text && <p className="mt-1 max-w-sm text-sm text-slate-500">{text}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
export const Notice = ({ tone = "amber", title, children }: { tone?: "amber" | "sky" | "green" | "red"; title?: string; children: ReactNode }) => {
  const c = { amber: "border-amber-300 bg-amber-50 text-amber-900", sky: "border-sky-200 bg-sky-50 text-sky-900", green: "border-emerald-200 bg-emerald-50 text-emerald-900", red: "border-rose-200 bg-rose-50 text-rose-900" }[tone];
  return <div role="note" className={cx("flex gap-3 rounded-lg border p-3 text-sm", c)}><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" /><div>{title && <p className="font-semibold">{title}</p>}{children}</div></div>;
};

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div><h1 className="text-2xl font-bold">{title}</h1>{subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}</div>
      {actions}
    </div>
  );
}
export function Stat({ label, value, hint, icon }: { label: string; value: ReactNode; hint?: string; icon?: ReactNode }) {
  return (
    <Card className="p-5">
      <div className="flex items-center justify-between text-sm text-slate-500"><span>{label}</span>{icon && <span className="text-navy-500">{icon}</span>}</div>
      <div className="mt-2 text-3xl font-bold text-navy-900">{value}</div>
      {hint && <div className="mt-1 text-xs text-slate-500">{hint}</div>}
    </Card>
  );
}

export function Field({ label, hint, error, children, required }: { label: string; hint?: string; error?: string; children: ReactNode; required?: boolean }) {
  return (
    <label className="block">
      <span className="label">{label}{required && <span className="text-rose-600" aria-hidden> *</span>}</span>
      {children}
      {hint && !error && <span className="mt-1 block text-xs text-slate-500">{hint}</span>}
      {error && <span className="mt-1 block text-xs text-rose-600">{error}</span>}
    </label>
  );
}

export function ScoreRing({ value, label, size = 88 }: { value: number; label: string; size?: number }) {
  const r = (size - 12) / 2, c = 2 * Math.PI * r, color = scoreColor(value);
  return (
    <div className="flex flex-col items-center gap-1" role="img" aria-label={`${label}: ${value} out of 100`}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#e2e8f0" strokeWidth="8" />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth="8" strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c * (1 - value / 100)} transform={`rotate(-90 ${size / 2} ${size / 2})`} style={{ transition: "stroke-dashoffset .6s" }} />
        <text x="50%" y="50%" dominantBaseline="central" textAnchor="middle" fontSize={size / 3.6} fontWeight="700" fill="#141a3b">{value}</text>
      </svg>
      <span className="text-center text-xs font-medium text-slate-600">{label}</span>
    </div>
  );
}
export const ProgressBar = ({ value }: { value: number }) => (
  <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200" role="progressbar" aria-valuenow={value} aria-valuemin={0} aria-valuemax={100}>
    <div className="h-full rounded-full bg-navy-600 transition-all duration-500" style={{ width: `${value}%` }} />
  </div>
);

export function Modal({ open, onClose, title, children }: { open: boolean; onClose: () => void; title: string; children: ReactNode }) {
  useEffect(() => {
    if (!open) return;
    const h = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-navy-950/50 p-4" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div role="dialog" aria-modal="true" aria-label={title} className="max-h-[90vh] w-full max-w-lg animate-fadeUp overflow-y-auto rounded-xl bg-white p-6 shadow-xl">
        <div className="mb-4 flex items-center justify-between"><h2 className="text-lg font-semibold">{title}</h2>
          <button onClick={onClose} aria-label="Close" className="rounded p-1 text-slate-500 hover:bg-slate-100"><X className="h-5 w-5" /></button></div>
        {children}
      </div>
    </div>
  );
}

export function Pagination({ page, total, pageSize, onPage }: { page: number; total: number; pageSize: number; onPage: (p: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  if (pages <= 1) return null;
  return (
    <div className="mt-6 flex items-center justify-center gap-3 text-sm">
      <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => onPage(page - 1)}>Previous</Button>
      <span className="text-slate-600">Page {page} of {pages}</span>
      <Button variant="secondary" size="sm" disabled={page >= pages} onClick={() => onPage(page + 1)}>Next</Button>
    </div>
  );
}

export function Tabs<T extends string>({ tabs, value, onChange }: { tabs: { id: T; label: string; count?: number }[]; value: T; onChange: (t: T) => void }) {
  return (
    <div className="mb-4 flex gap-1 overflow-x-auto border-b border-slate-200" role="tablist">
      {tabs.map((t) => (
        <button key={t.id} role="tab" aria-selected={value === t.id} onClick={() => onChange(t.id)}
          className={cx("whitespace-nowrap border-b-2 px-4 py-2 text-sm font-medium", value === t.id ? "border-navy-700 text-navy-800" : "border-transparent text-slate-500 hover:text-slate-800")}>
          {t.label}{t.count !== undefined && <span className="ml-1.5 rounded-full bg-slate-100 px-1.5 text-xs">{t.count}</span>}
        </button>
      ))}
    </div>
  );
}

/* ----- toasts ----- */
interface Toast { id: number; kind: "ok" | "err"; text: string }
const ToastCtx = createContext<{ ok: (t: string) => void; err: (t: string) => void }>({ ok: () => {}, err: () => {} });
export const useToast = () => useContext(ToastCtx);
export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<Toast[]>([]);
  const push = useCallback((kind: Toast["kind"], text: string) => {
    const id = Date.now() + Math.random();
    setItems((s) => [...s, { id, kind, text }]);
    setTimeout(() => setItems((s) => s.filter((t) => t.id !== id)), 4500);
  }, []);
  return (
    <ToastCtx.Provider value={{ ok: (t) => push("ok", t), err: (t) => push("err", t) }}>
      {children}
      <div className="pointer-events-none fixed bottom-4 right-4 z-[60] flex flex-col gap-2" aria-live="polite">
        {items.map((t) => (
          <div key={t.id} className={cx("pointer-events-auto flex max-w-sm animate-fadeUp items-start gap-2 rounded-lg px-4 py-3 text-sm text-white shadow-lg", t.kind === "ok" ? "bg-emerald-700" : "bg-rose-700")}>
            {t.kind === "ok" ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" /> : <XCircle className="mt-0.5 h-4 w-4 shrink-0" />}{t.text}
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}
