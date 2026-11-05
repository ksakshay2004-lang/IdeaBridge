import { Link } from "react-router-dom";
import { Button, Card } from "../../components/ui";

export function About() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-16 sm:px-6">
      <h1 className="text-4xl font-extrabold">About IdeaBridge</h1>
      <p className="mt-5 text-lg text-slate-600">Many valuable ideas never leave a notebook because their creators cannot reach people with the resources to build them – and entrepreneurs have no efficient way to find early-stage ideas worth their time.</p>
      <div className="mt-10 grid gap-5 md:grid-cols-3">
        {[["Evidence first", "Evaluations rely on retrieved, real comparison data. The agent is instructed – and the code enforces – that it may not invent projects, papers or companies."],
          ["Privacy by design", "Ideas are public, restricted or private. Restricted details unlock only for people the creator accepts; private ideas are never exposed or compared."],
          ["Honest AI", "When no AI model is configured the app says so loudly and uses a transparent rule-based engine. Demo output is never presented as live AI."]].map(([t, d]) => (
          <Card key={t} className="p-6"><h3 className="font-semibold">{t}</h3><p className="mt-2 text-sm text-slate-600">{d}</p></Card>))}
      </div>
      <h2 className="mt-12 text-2xl font-bold">Limitations</h2>
      <p className="mt-3 text-slate-600">Similarity is measured against a curated dataset and the platform's own ideas – not the whole market. Evaluations are decision-support only and are not legal, financial or investment advice, nor a guarantee of novelty or patentability.</p>
      <Link to="/register" className="mt-8 inline-block"><Button>Join IdeaBridge</Button></Link>
    </div>
  );
}

export function HowItWorks() {
  const flows = [
    ["Idea creators", ["Register and complete your profile", "Submit the idea with problem, solution, audience and stage", "Watch the AI evaluation progress and read the report", "Review collaboration requests and accept the ones you trust", "Iterate: edit the idea and re-run the evaluation"]],
    ["Entrepreneurs & investors", ["Register and describe your interests, stages and ticket size", "Browse, filter or search by meaning", "Check recommendations with match explanations", "Save ideas and send collaboration or funding requests", "Unlock restricted details once accepted, then message the creator"]],
  ] as const;
  const pipeline = ["Understand the idea", "Create a text embedding", "Vector-search real projects, platform ideas (and arXiv, if enabled)", "Analyse with an LLM – or the labelled demo engine", "Validate, clamp and store the structured report"];
  return (
    <div className="mx-auto max-w-5xl px-4 py-16 sm:px-6">
      <h1 className="text-4xl font-extrabold">How it works</h1>
      <div className="mt-10 grid gap-6 md:grid-cols-2">
        {flows.map(([t, s]) => (<Card key={t} className="p-6"><h2 className="text-lg font-semibold">{t}</h2>
          <ol className="mt-4 space-y-3">{s.map((x, i) => <li key={x} className="flex gap-3 text-sm text-slate-700"><span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-navy-700 text-xs font-bold text-white">{i + 1}</span>{x}</li>)}</ol></Card>))}
      </div>
      <Card className="mt-8 p-6"><h2 className="text-lg font-semibold">The evaluation pipeline</h2>
        <div className="mt-4 flex flex-wrap items-center gap-2 text-sm">{pipeline.map((p, i) => <span key={p} className="flex items-center gap-2"><span className="rounded-lg bg-navy-50 px-3 py-2 text-navy-900">{p}</span>{i < pipeline.length - 1 && <span className="text-slate-400">→</span>}</span>)}</div></Card>
    </div>
  );
}
