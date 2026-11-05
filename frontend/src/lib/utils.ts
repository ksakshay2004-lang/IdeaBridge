export const cx = (...c: (string | false | null | undefined)[]) => c.filter(Boolean).join(" ");
export const fmtDate = (s?: string | null) => (s ? new Date(s).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" }) : "—");
export const fmtDateTime = (s?: string | null) => (s ? new Date(s).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "—");
export const fmtMoney = (n?: number | null) => (n || n === 0 ? `$${n.toLocaleString()}` : "—");
export const fmtBytes = (n: number) => (n < 1024 ? `${n} B` : n < 1048576 ? `${(n / 1024).toFixed(1)} KB` : `${(n / 1048576).toFixed(1)} MB`);
export const scoreColor = (n: number) => (n >= 70 ? "#059669" : n >= 45 ? "#d97706" : "#dc2626");
export const csv = (s: string) => s.split(",").map((x) => x.trim()).filter(Boolean);
export const errMsg = (e: unknown) => (e instanceof Error ? e.message : "Something went wrong");
