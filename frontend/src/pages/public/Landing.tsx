import { Link } from "react-router-dom";
import { ArrowRight, BrainCircuit, Building2, Compass, FileSearch, Handshake, Lightbulb, LineChart, Lock, Rocket, ShieldCheck, Sparkles, Users } from "lucide-react";
import { api } from "../../lib/api";
import { useLoad } from "../../lib/hooks";
import type { IdeaCard } from "../../lib/types";
import { Button, Card, Spinner } from "../../components/ui";
import IdeaCardView from "../../components/IdeaCard";

const steps = [
  { icon: <Lightbulb />, t: "Submit your idea", d: "Describe the problem, your solution and who it is for. Choose public, restricted or private visibility." },
  { icon: <BrainCircuit />, t: "AI evaluates it", d: "The agent compares your idea with real existing projects and other ideas, then scores feasibility, market and novelty." },
  { icon: <Compass />, t: "Get discovered", d: "Entrepreneurs and investors browse, filter and receive smart match recommendations." },
  { icon: <Handshake />, t: "Collaborate", d: "Accept requests, unlock restricted details for people you trust, and talk directly in-app." },
];
const testimonials = [
  { q: "I finally learned how my idea differs from what already exists – and what to fix first.", n: "Sample creator", r: "Student innovator" },
  { q: "The match explanations save me hours of screening. I only open ideas that fit my thesis.", n: "Sample investor", r: "Angel investor" },
  { q: "Restricted visibility let me share my prototype details only with people I chose.", n: "Sample founder", r: "Hardware researcher" },
];

export default function Landing() {
  const featured = useLoad(() => api.get<IdeaCard[]>("/ideas/featured", { limit: 3 }), []);
  const stats = useLoad(() => api.get<{ ideas: number; creators: number; entrepreneurs: number; evaluations: number }>("/stats"), []);
  return (
    <>
      <section className="relative overflow-hidden bg-gradient-to-br from-navy-950 via-navy-900 to-navy-700 text-white">
        <div className="absolute -right-24 -top-24 h-96 w-96 rounded-full bg-navy-500/30 blur-3xl" aria-hidden />
        <div className="relative mx-auto grid max-w-7xl items-center gap-12 px-4 py-20 sm:px-6 lg:grid-cols-2 lg:py-28">
          <div>
            <span className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-xs font-medium"><Sparkles className="h-3.5 w-3.5" />AI-powered innovation marketplace</span>
            <h1 className="mt-5 text-4xl font-extrabold leading-tight text-white sm:text-5xl">Turn great ideas into funded, built products.</h1>
            <p className="mt-5 max-w-xl text-lg text-slate-200">IdeaBridge connects students, researchers and innovators with entrepreneurs and investors – and an evaluation agent checks novelty, feasibility and market potential before anyone spends time.</p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link to="/register"><Button size="lg" className="bg-white !text-navy-900 hover:!bg-slate-100">Submit your idea <ArrowRight className="h-4 w-4" /></Button></Link>
              <Link to="/explore"><Button size="lg" variant="ghost" className="!text-white ring-1 ring-white/30 hover:!bg-white/10">Explore ideas</Button></Link>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            {[["Ideas shared", stats.data?.ideas], ["Creators", stats.data?.creators], ["Entrepreneurs", stats.data?.entrepreneurs], ["AI evaluations", stats.data?.evaluations]].map(([l, v]) => (
              <div key={l as string} className="rounded-2xl bg-white/10 p-6 ring-1 ring-white/15 backdrop-blur"><div className="text-3xl font-bold">{v ?? "–"}</div><div className="mt-1 text-sm text-slate-200">{l}</div></div>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-20 sm:px-6">
        <h2 className="text-center text-3xl font-bold">How IdeaBridge works</h2>
        <div className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {steps.map((s, i) => (
            <Card key={s.t} className="p-6"><div className="mb-4 grid h-11 w-11 place-items-center rounded-xl bg-navy-50 text-navy-700">{s.icon}</div>
              <div className="text-xs font-semibold text-navy-500">STEP {i + 1}</div><h3 className="mt-1 font-semibold">{s.t}</h3><p className="mt-2 text-sm text-slate-600">{s.d}</p></Card>
          ))}
        </div>
      </section>

      <section className="bg-white py-20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6">
          <div className="flex items-end justify-between"><h2 className="text-3xl font-bold">Featured ideas</h2><Link to="/explore" className="text-sm font-medium text-navy-700 hover:underline">View all →</Link></div>
          <div className="mt-8">
            {featured.loading ? <Spinner /> : !featured.data?.length ? <p className="text-sm text-slate-500">No public ideas yet – be the first to share one.</p> :
              <div className="grid gap-5 md:grid-cols-3">{featured.data.map((i) => <IdeaCardView key={i.id} idea={i} to={`/ideas/${i.id}`} />)}</div>}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-20 sm:px-6">
        <div className="grid items-center gap-12 lg:grid-cols-2">
          <div>
            <h2 className="text-3xl font-bold">An evaluation agent that shows its evidence</h2>
            <p className="mt-4 text-slate-600">Every idea is embedded as a vector and compared against a curated dataset of real projects, other ideas on the platform and, optionally, arXiv research. Similarity percentages are calculated – never invented.</p>
            <ul className="mt-6 space-y-3 text-sm text-slate-700">
              {[[<FileSearch key="a" />, "Similar projects, with computed similarity and key differences"], [<LineChart key="b" />, "Technical feasibility, market opportunity and differentiation scores"], [<ShieldCheck key="c" />, "Strengths, weaknesses, risks and concrete improvements"], [<Lock key="d" />, "Private ideas never leave the platform or reach the LLM"]].map(([ic, t], i) => (
                <li key={i} className="flex items-center gap-3"><span className="text-navy-600 [&>svg]:h-5 [&>svg]:w-5">{ic}</span>{t as string}</li>))}
            </ul>
            <p className="mt-5 rounded-lg bg-amber-50 p-3 text-xs text-amber-900">Without an LLM API key the platform runs in a clearly labelled <b>demo mode</b> using a local rule-based engine – it never pretends to be a live AI model.</p>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <Card className="p-6"><Users className="mb-3 h-6 w-6 text-navy-600" /><h3 className="font-semibold">For idea creators</h3><ul className="mt-2 space-y-1.5 text-sm text-slate-600"><li>• Honest feedback in minutes</li><li>• Control who sees what</li><li>• Reach vetted entrepreneurs</li><li>• Track development stage</li></ul></Card>
            <Card className="p-6"><Building2 className="mb-3 h-6 w-6 text-navy-600" /><h3 className="font-semibold">For entrepreneurs</h3><ul className="mt-2 space-y-1.5 text-sm text-slate-600"><li>• Pre-screened deal flow</li><li>• Match scores with reasons</li><li>• Semantic search & filters</li><li>• Verified profile badge</li></ul></Card>
          </div>
        </div>
      </section>

      <section className="bg-navy-50 py-20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6">
          <h2 className="text-center text-3xl font-bold">What people say</h2>
          <p className="mt-1 text-center text-xs text-slate-500">Sample content for illustration – not real customer quotes.</p>
          <div className="mt-8 grid gap-5 md:grid-cols-3">
            {testimonials.map((t) => <Card key={t.q} className="p-6"><p className="text-sm text-slate-700">“{t.q}”</p><div className="mt-4 text-sm font-semibold">{t.n}</div><div className="text-xs text-slate-500">{t.r} · sample</div></Card>)}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-4xl px-4 py-20 text-center sm:px-6">
        <Rocket className="mx-auto h-10 w-10 text-navy-600" />
        <h2 className="mt-4 text-3xl font-bold">Ready to bridge the gap?</h2>
        <p className="mt-3 text-slate-600">Create a free account as a creator or an entrepreneur in under a minute.</p>
        <Link to="/register" className="mt-6 inline-block"><Button size="lg">Create your account</Button></Link>
      </section>
    </>
  );
}
