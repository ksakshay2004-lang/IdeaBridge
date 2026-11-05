import { FormEvent, useEffect, useState } from "react";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { useLoad } from "../../lib/hooks";
import type { Categories, User } from "../../lib/types";
import { STAGES, STAGE_LABEL } from "../../lib/types";
import { Badge, Button, Card, ErrorBox, Field, Notice, PageHeader, Spinner, useToast } from "../../components/ui";
import { cx, csv, errMsg } from "../../lib/utils";

interface ProfResp { user: User; profile: Record<string, any> }
const Chips = ({ options, value, onChange }: { options: string[]; value: string[]; onChange: (v: string[]) => void }) => (
  <div className="flex flex-wrap gap-2">{options.map((o) => { const on = value.includes(o); return (
    <button type="button" key={o} aria-pressed={on} onClick={() => onChange(on ? value.filter((x) => x !== o) : [...value, o])}
      className={cx("rounded-full border px-3 py-1 text-xs font-medium", on ? "border-navy-700 bg-navy-700 text-white" : "border-slate-300 bg-white text-slate-600 hover:border-navy-400")}>{o}</button>); })}</div>
);

export default function Profile() {
  const { user, refresh } = useAuth();
  const toast = useToast();
  const { data, loading, error, reload } = useLoad(() => api.get<ProfResp>("/profile/me"), []);
  const cats = useLoad(() => api.get<Categories>("/categories"), []);
  const [f, setF] = useState<Record<string, any>>({});
  const [busy, setBusy] = useState(false); const [formErr, setFormErr] = useState("");
  const [pw, setPw] = useState({ current_password: "", new_password: "" });
  useEffect(() => { if (data) setF({ full_name: data.user.full_name, ...data.profile, skills: (data.profile.skills ?? []).join(", "), target_markets: (data.profile.target_markets ?? []).join(", ") }); }, [data]);
  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => setF({ ...f, [k]: e.target.value });
  const isCreator = user?.role === "creator", isEnt = user?.role === "entrepreneur";

  const save = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true); setFormErr("");
    try {
      if (isCreator) await api.put("/profile/me/creator", { full_name: f.full_name, headline: f.headline ?? "", bio: f.bio ?? "", organization: f.organization ?? "", location: f.location ?? "", website: f.website ?? "", skills: csv(f.skills ?? "") });
      else await api.put("/profile/me/entrepreneur", { full_name: f.full_name, company_name: f.company_name ?? "", company_type: f.company_type ?? "startup", bio: f.bio ?? "", website: f.website ?? "", location: f.location ?? "",
        industries: f.industries ?? [], technologies: f.technologies ?? [], interests: f.interests ?? "", preferred_stages: f.preferred_stages ?? [], target_markets: csv(f.target_markets ?? ""),
        investment_min: f.investment_min === "" || f.investment_min == null ? null : Number(f.investment_min), investment_max: f.investment_max === "" || f.investment_max == null ? null : Number(f.investment_max) });
      await refresh(); await reload(true); toast.ok("Profile saved");
    } catch (err) { setFormErr(errMsg(err)); } finally { setBusy(false); }
  };
  const changePw = async (e: FormEvent) => {
    e.preventDefault();
    try { await api.post("/auth/change-password", pw); setPw({ current_password: "", new_password: "" }); toast.ok("Password changed"); } catch (err) { toast.err(errMsg(err)); }
  };
  if (loading) return <Spinner />;
  if (error) return <ErrorBox message={error} onRetry={() => reload()} />;

  return (
    <div className="space-y-6">
      <PageHeader title={isEnt ? "Company profile" : "Profile & settings"} subtitle={isEnt ? "Your preferences power match scores and recommendations." : "How you appear to entrepreneurs."} />
      {isEnt && user && <Notice tone={user.is_verified ? "green" : "amber"} title={user.is_verified ? "Your profile is verified" : "Verification pending"}>{user.is_verified ? "Creators see a verified badge next to your name." : "An administrator reviews new entrepreneur profiles. A complete profile helps."}</Notice>}
      <form onSubmit={save}>
        <Card className="space-y-4 p-6">
          {formErr && <ErrorBox message={formErr} />}
          <div className="grid gap-4 sm:grid-cols-2"><Field label="Full name"><input className="input" value={f.full_name ?? ""} onChange={set("full_name")} /></Field>
            <Field label="Email"><input className="input" value={user?.email ?? ""} disabled /></Field></div>
          {isCreator && <>
            <Field label="Headline"><input className="input" maxLength={160} value={f.headline ?? ""} onChange={set("headline")} placeholder="e.g. Final-year computer science student" /></Field>
            <div className="grid gap-4 sm:grid-cols-2"><Field label="Organisation"><input className="input" value={f.organization ?? ""} onChange={set("organization")} /></Field><Field label="Location"><input className="input" value={f.location ?? ""} onChange={set("location")} /></Field></div>
            <Field label="Website" hint="Must start with https://"><input className="input" value={f.website ?? ""} onChange={set("website")} /></Field>
            <Field label="Skills" hint="Comma separated"><input className="input" value={f.skills ?? ""} onChange={set("skills")} /></Field>
            <Field label="Bio"><textarea className="input" rows={4} value={f.bio ?? ""} onChange={set("bio")} /></Field></>}
          {isEnt && <>
            <div className="grid gap-4 sm:grid-cols-2"><Field label="Company / fund"><input className="input" value={f.company_name ?? ""} onChange={set("company_name")} /></Field>
              <Field label="Type"><select className="input" value={f.company_type ?? "startup"} onChange={set("company_type")}>{["startup", "investor", "corporate", "other"].map((t) => <option key={t}>{t}</option>)}</select></Field></div>
            <div className="grid gap-4 sm:grid-cols-2"><Field label="Website"><input className="input" value={f.website ?? ""} onChange={set("website")} /></Field><Field label="Location"><input className="input" value={f.location ?? ""} onChange={set("location")} /></Field></div>
            <Field label="About"><textarea className="input" rows={3} value={f.bio ?? ""} onChange={set("bio")} /></Field>
            <div><span className="label">Industries of interest</span><Chips options={cats.data?.industries.map((c) => c.name) ?? []} value={f.industries ?? []} onChange={(v) => setF({ ...f, industries: v })} /></div>
            <div><span className="label">Technologies of interest</span><Chips options={cats.data?.technologies.map((c) => c.name) ?? []} value={f.technologies ?? []} onChange={(v) => setF({ ...f, technologies: v })} /></div>
            <div><span className="label">Preferred project stages</span><Chips options={[...STAGES]} value={f.preferred_stages ?? []} onChange={(v) => setF({ ...f, preferred_stages: v })} /><p className="mt-1 text-xs text-slate-500">{(f.preferred_stages ?? []).map((s: string) => STAGE_LABEL[s]).join(", ")}</p></div>
            <Field label="Business interests" hint="Free text – used for semantic matching against ideas."><textarea className="input" rows={3} value={f.interests ?? ""} onChange={set("interests")} /></Field>
            <Field label="Target markets" hint="Comma separated, e.g. students, farmers, SMEs"><input className="input" value={f.target_markets ?? ""} onChange={set("target_markets")} /></Field>
            <div className="grid gap-4 sm:grid-cols-2"><Field label="Minimum investment (USD)"><input className="input" type="number" min={0} value={f.investment_min ?? ""} onChange={set("investment_min")} /></Field>
              <Field label="Maximum investment (USD)"><input className="input" type="number" min={0} value={f.investment_max ?? ""} onChange={set("investment_max")} /></Field></div></>}
          <div className="flex justify-end"><Button type="submit" loading={busy}>Save profile</Button></div>
        </Card>
      </form>
      <form onSubmit={changePw}><Card className="space-y-4 p-6"><h2 className="font-semibold">Change password {user?.role === "admin" && <Badge>admin</Badge>}</h2>
        <div className="grid gap-4 sm:grid-cols-2"><Field label="Current password"><input className="input" type="password" autoComplete="current-password" required value={pw.current_password} onChange={(e) => setPw({ ...pw, current_password: e.target.value })} /></Field>
          <Field label="New password" hint="8+ characters, letter and digit"><input className="input" type="password" autoComplete="new-password" required minLength={8} value={pw.new_password} onChange={(e) => setPw({ ...pw, new_password: e.target.value })} /></Field></div>
        <div className="flex justify-end"><Button type="submit" variant="secondary">Update password</Button></div></Card></form>
    </div>
  );
}
