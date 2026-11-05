import { FormEvent, useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { Building2, Lightbulb } from "lucide-react";
import { homePath, useAuth } from "../../lib/auth";
import { Button, Card, ErrorBox, Field } from "../../components/ui";
import { cx, errMsg } from "../../lib/utils";

export function Login() {
  const { user, login } = useAuth();
  const nav = useNavigate();
  const loc = useLocation() as { state?: { from?: string } };
  const [email, setEmail] = useState(""); const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  if (user) return <Navigate to={homePath(user)} replace />;
  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true); setError("");
    try { const u = await login(email, password); nav(loc.state?.from ?? homePath(u), { replace: true }); }
    catch (err) { setError(errMsg(err)); } finally { setBusy(false); }
  };
  return (
    <div className="mx-auto flex max-w-md flex-col px-4 py-16">
      <h1 className="text-center text-3xl font-bold">Welcome back</h1>
      <p className="mb-6 mt-1 text-center text-sm text-slate-500">Log in to your IdeaBridge account</p>
      <Card className="p-6">
        <form onSubmit={submit} className="space-y-4">
          {error && <ErrorBox message={error} />}
          <Field label="Email" required><input className="input" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></Field>
          <Field label="Password" required><input className="input" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} /></Field>
          <Button type="submit" loading={busy} className="w-full">Log in</Button>
        </form>
      </Card>
      <p className="mt-4 text-center text-sm text-slate-600">New here? <Link className="font-medium text-navy-700 hover:underline" to="/register">Create an account</Link></p>
    </div>
  );
}

export function Register() {
  const { user, register } = useAuth();
  const nav = useNavigate();
  const [role, setRole] = useState<"creator" | "entrepreneur">("creator");
  const [f, setF] = useState({ full_name: "", email: "", password: "", company_name: "" });
  const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  if (user) return <Navigate to={homePath(user)} replace />;
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [k]: e.target.value });
  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true); setError("");
    try { const u = await register({ ...f, role, company_name: role === "entrepreneur" ? f.company_name : undefined }); nav(homePath(u) + (role === "creator" ? "/submit" : "/profile"), { replace: true }); }
    catch (err) { setError(errMsg(err)); } finally { setBusy(false); }
  };
  const opt = (r: "creator" | "entrepreneur", icon: React.ReactNode, t: string, d: string) => (
    <button type="button" onClick={() => setRole(r)} aria-pressed={role === r}
      className={cx("flex-1 rounded-xl border-2 p-4 text-left transition", role === r ? "border-navy-600 bg-navy-50" : "border-slate-200 hover:border-slate-300")}>
      <div className="mb-1 text-navy-700">{icon}</div><div className="font-semibold">{t}</div><div className="text-xs text-slate-500">{d}</div></button>
  );
  return (
    <div className="mx-auto flex max-w-lg flex-col px-4 py-14">
      <h1 className="text-center text-3xl font-bold">Create your account</h1>
      <Card className="mt-6 p-6">
        <form onSubmit={submit} className="space-y-4">
          <div className="flex gap-3">{opt("creator", <Lightbulb />, "Idea creator", "I have ideas to share")}{opt("entrepreneur", <Building2 />, "Entrepreneur / investor", "I want to find ideas")}</div>
          {error && <ErrorBox message={error} />}
          <Field label="Full name" required><input className="input" required minLength={2} autoComplete="name" value={f.full_name} onChange={set("full_name")} /></Field>
          {role === "entrepreneur" && <Field label="Company / fund name"><input className="input" value={f.company_name} onChange={set("company_name")} /></Field>}
          <Field label="Email" required><input className="input" type="email" required autoComplete="email" value={f.email} onChange={set("email")} /></Field>
          <Field label="Password" required hint="At least 8 characters, with a letter and a digit."><input className="input" type="password" required minLength={8} autoComplete="new-password" value={f.password} onChange={set("password")} /></Field>
          <Button type="submit" loading={busy} className="w-full">Create account</Button>
        </form>
      </Card>
      <p className="mt-4 text-center text-sm text-slate-600">Already registered? <Link className="font-medium text-navy-700 hover:underline" to="/login">Log in</Link></p>
    </div>
  );
}
