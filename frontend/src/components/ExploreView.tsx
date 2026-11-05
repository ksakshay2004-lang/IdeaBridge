import { useState } from "react";
import { Search, SlidersHorizontal } from "lucide-react";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useDebounced, useLoad } from "../lib/hooks";
import type { Categories, IdeaCard, Paged } from "../lib/types";
import { STAGES, STAGE_LABEL } from "../lib/types";
import { Card, EmptyState, ErrorBox, Pagination, Spinner, useToast } from "./ui";
import IdeaCardView from "./IdeaCard";
import { errMsg } from "../lib/utils";

export default function ExploreView({ detailBase }: { detailBase: string }) {
  const { user } = useAuth();
  const toast = useToast();
  const [q, setQ] = useState("");
  const [semantic, setSemantic] = useState(false);
  const [industry, setIndustry] = useState("");
  const [technology, setTechnology] = useState("");
  const [stage, setStage] = useState("");
  const [sort, setSort] = useState("newest");
  const [page, setPage] = useState(1);
  const dq = useDebounced(q);
  const cats = useLoad(() => api.get<Categories>("/categories"), []);
  const list = useLoad(() => api.get<Paged<IdeaCard>>("/ideas", { q: dq, semantic: semantic && dq ? true : undefined, industry, technology, stage, sort, page, page_size: 12 }),
    [dq, semantic, industry, technology, stage, sort, page]);

  const toggleSave = async (i: IdeaCard) => {
    try {
      if (i.is_saved) await api.del(`/saved/${i.id}`); else await api.post(`/saved/${i.id}`);
      list.setData((d) => d && { ...d, items: d.items.map((x) => (x.id === i.id ? { ...x, is_saved: !x.is_saved } : x)) });
      toast.ok(i.is_saved ? "Removed from saved ideas" : "Saved to your list");
    } catch (e) { toast.err(errMsg(e)); }
  };
  const reset = (fn: () => void) => { fn(); setPage(1); };
  const canSave = user?.role === "entrepreneur";

  return (
    <div>
      <Card className="mb-6 p-4">
        <div className="flex flex-col gap-3 lg:flex-row">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
            <input className="input pl-9" placeholder={semantic ? "Describe what you're looking for…" : "Search ideas by keyword…"} value={q} onChange={(e) => reset(() => setQ(e.target.value))} aria-label="Search ideas" />
          </div>
          <select className="input lg:w-44" value={industry} onChange={(e) => reset(() => setIndustry(e.target.value))} aria-label="Industry">
            <option value="">All industries</option>{cats.data?.industries.map((c) => <option key={c.id}>{c.name}</option>)}
          </select>
          <select className="input lg:w-40" value={technology} onChange={(e) => reset(() => setTechnology(e.target.value))} aria-label="Technology">
            <option value="">All technologies</option>{cats.data?.technologies.map((c) => <option key={c.id}>{c.name}</option>)}
          </select>
          <select className="input lg:w-36" value={stage} onChange={(e) => reset(() => setStage(e.target.value))} aria-label="Stage">
            <option value="">Any stage</option>{STAGES.map((s) => <option key={s} value={s}>{STAGE_LABEL[s]}</option>)}
          </select>
          <select className="input lg:w-36" value={sort} onChange={(e) => reset(() => setSort(e.target.value))} aria-label="Sort">
            <option value="newest">Newest</option><option value="score">Top score</option>
          </select>
        </div>
        <label className="mt-3 flex items-center gap-2 text-xs text-slate-600">
          <input type="checkbox" checked={semantic} onChange={(e) => reset(() => setSemantic(e.target.checked))} />
          <SlidersHorizontal className="h-3.5 w-3.5" />Meaning-based search (ranks by vector similarity instead of exact keywords)
        </label>
      </Card>
      {list.loading ? <Spinner /> : list.error ? <ErrorBox message={list.error} onRetry={() => list.reload()} /> :
        !list.data || list.data.items.length === 0 ? <EmptyState title="No ideas found" text="Try different keywords or clear some filters." /> : (
          <>
            <p className="mb-3 text-sm text-slate-500">{list.data.total} idea{list.data.total === 1 ? "" : "s"}{!user && " · sign in to see more"}</p>
            <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {list.data.items.map((i) => <IdeaCardView key={i.id} idea={i} to={`${detailBase}/${i.id}`} onToggleSave={canSave ? toggleSave : undefined} />)}
            </div>
            <Pagination page={page} total={list.data.total} pageSize={12} onPage={setPage} />
          </>
        )}
    </div>
  );
}
