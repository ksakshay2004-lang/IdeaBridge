import { Link } from "react-router-dom";
import { Bookmark, Compass, Handshake, Sparkles } from "lucide-react";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { useLoad } from "../../lib/hooks";
import type { Collab, IdeaCard } from "../../lib/types";
import ExploreView from "../../components/ExploreView";
import IdeaCardView from "../../components/IdeaCard";
import { Button, EmptyState, ErrorBox, Notice, PageHeader, Spinner, Stat, useToast } from "../../components/ui";
import { errMsg } from "../../lib/utils";

const D = "/app/entrepreneur/ideas";

export function EntrepreneurOverview() {
  const { user } = useAuth();
  const rec = useLoad(() => api.get<IdeaCard[]>("/recommendations", { limit: 3 }), []);
  const saved = useLoad(() => api.get<IdeaCard[]>("/saved"), []);
  const reqs = useLoad(() => api.get<Collab[]>("/collaboration"), []);
  return (
    <div>
      <PageHeader title={`Hello, ${user?.full_name.split(" ")[0]}`} subtitle="Fresh ideas matched to your focus." actions={<Link to="/app/entrepreneur/discover"><Button><Compass className="h-4 w-4" />Discover ideas</Button></Link>} />
      {!user?.is_verified && <div className="mb-5"><Notice title="Verification pending">An administrator will review your profile. Completing it speeds this up.</Notice></div>}
      <div className="grid gap-4 sm:grid-cols-3">
        <Stat label="Saved ideas" value={saved.data?.length ?? "–"} icon={<Bookmark className="h-5 w-5" />} />
        <Stat label="Requests sent" value={reqs.data?.length ?? "–"} icon={<Handshake className="h-5 w-5" />} />
        <Stat label="Accepted" value={reqs.data?.filter((r) => r.status === "accepted").length ?? "–"} icon={<Sparkles className="h-5 w-5" />} />
      </div>
      <div className="mb-3 mt-8 flex items-center justify-between"><h2 className="text-lg font-semibold">Top matches for you</h2><Link to="/app/entrepreneur/recommended" className="text-sm text-navy-700 hover:underline">See all →</Link></div>
      {rec.loading ? <Spinner /> : rec.error ? <ErrorBox message={rec.error} /> : !rec.data?.length ? <EmptyState title="No ideas yet" /> :
        <div className="grid gap-5 md:grid-cols-3">{rec.data.map((i) => <IdeaCardView key={i.id} idea={i} to={`${D}/${i.id}`} showMatch />)}</div>}
    </div>
  );
}

export function Discover() {
  return (<div><PageHeader title="Discover ideas" subtitle="Search by keyword or by meaning, and filter by industry, technology and stage." /><ExploreView detailBase={D} /></div>);
}

export function Recommended() {
  const toast = useToast();
  const { data, loading, error, reload, setData } = useLoad(() => api.get<IdeaCard[]>("/recommendations", { limit: 24 }), []);
  const toggle = async (i: IdeaCard) => {
    try { if (i.is_saved) await api.del(`/saved/${i.id}`); else await api.post(`/saved/${i.id}`); setData((d) => d && d.map((x) => (x.id === i.id ? { ...x, is_saved: !x.is_saved } : x))); } catch (e) { toast.err(errMsg(e)); }
  };
  if (loading) return <Spinner />;
  if (error) return <ErrorBox message={error} onRetry={() => reload()} />;
  return (
    <div><PageHeader title="Recommended ideas" subtitle="Ranked by match with your industries, technologies, interests, stages, markets and ticket size." />
      <Notice tone="sky">Improve these results by completing your <Link className="underline" to="/app/entrepreneur/profile">company profile</Link>.</Notice>
      <div className="mt-5">{!data?.length ? <EmptyState title="Nothing to recommend yet" text="Check back when more ideas are published." /> :
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">{data.map((i) => <IdeaCardView key={i.id} idea={i} to={`${D}/${i.id}`} onToggleSave={toggle} showMatch />)}</div>}</div></div>
  );
}

export function Saved() {
  const toast = useToast();
  const { data, loading, error, reload, setData } = useLoad(() => api.get<IdeaCard[]>("/saved"), []);
  const unsave = async (i: IdeaCard) => { try { await api.del(`/saved/${i.id}`); setData((d) => d && d.filter((x) => x.id !== i.id)); toast.ok("Removed"); } catch (e) { toast.err(errMsg(e)); } };
  if (loading) return <Spinner />;
  if (error) return <ErrorBox message={error} onRetry={() => reload()} />;
  return (
    <div><PageHeader title="Saved ideas" />{!data?.length ? <EmptyState icon={<Bookmark className="h-6 w-6" />} title="No saved ideas" text="Use the bookmark icon on any idea to keep it here." action={<Link to="/app/entrepreneur/discover"><Button>Discover ideas</Button></Link>} /> :
      <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">{data.map((i) => <IdeaCardView key={i.id} idea={i} to={`${D}/${i.id}`} onToggleSave={unsave} />)}</div>}</div>
  );
}
