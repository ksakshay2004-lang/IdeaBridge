import { FormEvent, useState } from "react";
import { Eye, EyeOff, Globe, Lock, Paperclip, X } from "lucide-react";
import { api } from "../lib/api";
import { useLoad } from "../lib/hooks";
import type { Categories } from "../lib/types";
import { STAGES, STAGE_LABEL } from "../lib/types";
import { Button, Card, ErrorBox, Field, Spinner } from "./ui";
import { cx, fmtBytes } from "../lib/utils";

export interface IdeaFormValues {
  title: string; short_description: string; problem: string; solution: string; industry: string; target_audience: string;
  technologies: string[]; stage: string; expected_impact: string; business_potential: string; funding_needed: string; visibility: string;
}
export const EMPTY_IDEA: IdeaFormValues = { title: "", short_description: "", problem: "", solution: "", industry: "", target_audience: "", technologies: [],
  stage: "concept", expected_impact: "", business_potential: "", funding_needed: "", visibility: "public" };

const VIS = [
  { id: "public", icon: <Globe className="h-4 w-4" />, t: "Public", d: "Anyone can read it; visible on Explore." },
  { id: "restricted", icon: <EyeOff className="h-4 w-4" />, t: "Restricted", d: "Signed-in users see a teaser. Full details unlock when you accept their request." },
  { id: "private", icon: <Lock className="h-4 w-4" />, t: "Private", d: "Only you. Not listed, not searchable by others." },
];
const ALLOWED = ".pdf,.docx,.pptx,.png,.jpg,.jpeg,.txt";

export default function IdeaForm({ initial, submitLabel, onSubmit, allowFiles }: {
  initial: IdeaFormValues; submitLabel: string; allowFiles?: boolean;
  onSubmit: (v: IdeaFormValues, files: File[]) => Promise<void>;
}) {
  const [v, setV] = useState(initial);
  const [files, setFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const cats = useLoad(() => api.get<Categories>("/categories"), []);
  const set = <K extends keyof IdeaFormValues>(k: K, val: IdeaFormValues[K]) => setV((s) => ({ ...s, [k]: val }));
  const text = (k: keyof IdeaFormValues) => ({ value: v[k] as string, onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => set(k, e.target.value as never) });
  const toggleTech = (t: string) => set("technologies", v.technologies.includes(t) ? v.technologies.filter((x) => x !== t) : [...v.technologies, t]);

  const validate = (): string => {
    if (v.title.trim().length < 5) return "Title must be at least 5 characters.";
    if (v.short_description.trim().length < 20) return "Short description must be at least 20 characters.";
    if (v.problem.trim().length < 30) return "Please describe the problem in at least 30 characters.";
    if (v.solution.trim().length < 30) return "Please describe the solution in at least 30 characters.";
    if (!v.industry) return "Choose an industry.";
    if (v.target_audience.trim().length < 3) return "Describe the target audience.";
    for (const f of files) {
      if (f.size > 10 * 1024 * 1024) return `${f.name} is larger than 10 MB.`;
      if (!ALLOWED.split(",").some((e) => f.name.toLowerCase().endsWith(e))) return `${f.name}: file type not allowed.`;
    }
    return "";
  };
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const m = validate();
    if (m) { setError(m); window.scrollTo({ top: 0, behavior: "smooth" }); return; }
    setBusy(true); setError("");
    try { await onSubmit(v, files); } catch (err) { setError(err instanceof Error ? err.message : "Failed to save"); window.scrollTo({ top: 0, behavior: "smooth" }); } finally { setBusy(false); }
  };
  if (cats.loading) return <Spinner />;
  return (
    <form onSubmit={submit} className="space-y-6">
      {error && <ErrorBox message={error} />}
      <Card className="space-y-4 p-6">
        <h2 className="font-semibold">The idea</h2>
        <Field label="Idea title" required><input className="input" maxLength={160} {...text("title")} /></Field>
        <Field label="Short description" required hint={`${v.short_description.length}/500 · shown on idea cards`}><textarea className="input" rows={2} maxLength={500} {...text("short_description")} /></Field>
        <Field label="Problem being solved" required hint="Who is affected, and how painful is it?"><textarea className="input" rows={4} {...text("problem")} /></Field>
        <Field label="Proposed solution" required hint="How does it work, and what makes it different?"><textarea className="input" rows={5} {...text("solution")} /></Field>
      </Card>
      <Card className="space-y-4 p-6">
        <h2 className="font-semibold">Market & technology</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Industry" required><select className="input" {...text("industry")}><option value="">Select…</option>{cats.data?.industries.map((c) => <option key={c.id}>{c.name}</option>)}</select></Field>
          <Field label="Current development stage"><select className="input" {...text("stage")}>{STAGES.map((s) => <option key={s} value={s}>{STAGE_LABEL[s]}</option>)}</select></Field>
        </div>
        <Field label="Target audience" required><input className="input" maxLength={500} {...text("target_audience")} /></Field>
        <div><span className="label">Technologies involved</span>
          <div className="flex flex-wrap gap-2">{cats.data?.technologies.map((t) => (
            <button type="button" key={t.id} aria-pressed={v.technologies.includes(t.name)} onClick={() => toggleTech(t.name)}
              className={cx("rounded-full border px-3 py-1 text-xs font-medium transition", v.technologies.includes(t.name) ? "border-navy-700 bg-navy-700 text-white" : "border-slate-300 bg-white text-slate-600 hover:border-navy-400")}>{t.name}</button>))}</div></div>
        <Field label="Expected impact"><textarea className="input" rows={3} {...text("expected_impact")} /></Field>
        <Field label="Business potential" hint="Revenue ideas, pricing, market size, go-to-market."><textarea className="input" rows={3} {...text("business_potential")} /></Field>
        <Field label="Funding sought (USD, optional)" hint="Used to match you with investors whose ticket size fits."><input className="input" type="number" min={0} step={1000} {...text("funding_needed")} /></Field>
      </Card>
      <Card className="space-y-3 p-6">
        <h2 className="font-semibold">Visibility</h2>
        <div className="grid gap-3 sm:grid-cols-3" role="radiogroup" aria-label="Visibility">
          {VIS.map((o) => (
            <button type="button" role="radio" aria-checked={v.visibility === o.id} key={o.id} onClick={() => set("visibility", o.id)}
              className={cx("rounded-xl border-2 p-4 text-left", v.visibility === o.id ? "border-navy-600 bg-navy-50" : "border-slate-200 hover:border-slate-300")}>
              <div className="flex items-center gap-2 font-semibold text-navy-900">{o.icon}{o.t}</div><p className="mt-1 text-xs text-slate-600">{o.d}</p></button>))}
        </div>
        <p className="flex items-center gap-1 text-xs text-slate-500"><Eye className="h-3.5 w-3.5" />You can change visibility any time. Private and restricted ideas are never sent to the LLM in other users' evaluations.</p>
      </Card>
      {allowFiles && (
        <Card className="space-y-3 p-6">
          <h2 className="font-semibold">Supporting documents</h2>
          <p className="text-xs text-slate-500">PDF, DOCX, PPTX, PNG, JPG or TXT · up to 10 MB each · up to 10 files. Documents follow the idea's visibility and are not analysed by the AI.</p>
          <input type="file" multiple accept={ALLOWED} className="block w-full text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-navy-50 file:px-4 file:py-2 file:text-sm file:font-medium file:text-navy-800"
            onChange={(e) => { setFiles([...files, ...Array.from(e.target.files ?? [])].slice(0, 10)); e.target.value = ""; }} />
          {files.length > 0 && <ul className="space-y-1">{files.map((f, i) => (
            <li key={i} className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-sm"><span className="flex items-center gap-2"><Paperclip className="h-4 w-4 text-slate-400" />{f.name} <span className="text-xs text-slate-400">{fmtBytes(f.size)}</span></span>
              <button type="button" aria-label={`Remove ${f.name}`} onClick={() => setFiles(files.filter((_, j) => j !== i))}><X className="h-4 w-4 text-slate-500" /></button></li>))}</ul>}
        </Card>
      )}
      <div className="flex justify-end"><Button type="submit" size="lg" loading={busy}>{submitLabel}</Button></div>
    </form>
  );
}
