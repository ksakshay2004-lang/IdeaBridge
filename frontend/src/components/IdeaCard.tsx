import { Link } from "react-router-dom";
import { Bookmark, BookmarkCheck, Lock, ShieldCheck, Sparkles } from "lucide-react";
import type { IdeaCard as Idea } from "../lib/types";
import { STAGE_LABEL } from "../lib/types";
import { Badge, Card, statusTone } from "./ui";
import { cx, scoreColor } from "../lib/utils";

export default function IdeaCardView({ idea, to, onToggleSave, showMatch }: { idea: Idea; to: string; onToggleSave?: (i: Idea) => void; showMatch?: boolean }) {
  const s = idea.scores;
  return (
    <Card className="flex h-full flex-col p-5 transition hover:-translate-y-0.5 hover:shadow-lg">
      <div className="mb-3 flex items-start justify-between gap-2">
        <div className="flex flex-wrap gap-1.5">
          <Badge tone="indigo">{idea.industry}</Badge>
          <Badge>{STAGE_LABEL[idea.stage] ?? idea.stage}</Badge>
          {idea.visibility !== "public" && <Badge tone={statusTone(idea.visibility)}><Lock className="h-3 w-3" />{idea.visibility}</Badge>}
        </div>
        {onToggleSave && (
          <button onClick={() => onToggleSave(idea)} aria-label={idea.is_saved ? "Remove from saved" : "Save idea"} className="text-navy-600 hover:text-navy-900">
            {idea.is_saved ? <BookmarkCheck className="h-5 w-5" /> : <Bookmark className="h-5 w-5" />}
          </button>
        )}
      </div>
      <Link to={to} className="group"><h3 className="text-base font-semibold leading-snug group-hover:text-navy-600">{idea.title}</h3></Link>
      <p className="mt-2 line-clamp-3 flex-1 text-sm text-slate-600">{idea.short_description}</p>
      {idea.technologies.length > 0 && <div className="mt-3 flex flex-wrap gap-1">{idea.technologies.slice(0, 4).map((t) => <span key={t} className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600">{t}</span>)}</div>}
      {showMatch && idea.match && (
        <div className="mt-3 rounded-lg bg-navy-50 p-3 text-xs text-navy-900">
          <div className="mb-1 flex items-center gap-1 font-semibold"><Sparkles className="h-3.5 w-3.5" />Match score {idea.match.score}/100</div>
          <ul className="list-disc space-y-0.5 pl-4 text-slate-700">{idea.match.reasons.slice(0, 3).map((r) => <li key={r}>{r}</li>)}</ul>
        </div>
      )}
      <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3 text-xs text-slate-500">
        <span className="flex items-center gap-1">{idea.creator.name}</span>
        {s ? <span className={cx("font-semibold")} style={{ color: scoreColor(s.overall) }} title={s.mode === "demo" ? "Demo-mode heuristic score" : "AI score"}>
          {s.overall}/100{s.mode === "demo" && <span className="ml-1 font-normal text-amber-700">(demo)</span>}</span>
          : idea.access === "teaser" && idea.visibility === "restricted" ? <span className="flex items-center gap-1"><ShieldCheck className="h-3.5 w-3.5" />Request access</span> : <span>Not evaluated</span>}
      </div>
    </Card>
  );
}
