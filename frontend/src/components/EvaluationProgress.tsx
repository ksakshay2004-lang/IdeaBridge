import { useEffect, useRef } from "react";
import { CheckCircle2, Circle, Loader2 } from "lucide-react";
import { api } from "../lib/api";
import type { Evaluation } from "../lib/types";
import { Card, ProgressBar } from "./ui";

const STEPS = [["understanding", "Understanding the idea"], ["embedding", "Creating vector embedding"], ["retrieving", "Searching similar projects & ideas"],
  ["analysing", "Analysing feasibility, market and novelty"], ["finalizing", "Building the report"]];

export default function EvaluationProgress({ evaluation, onUpdate, onDone }: { evaluation: Evaluation; onUpdate: (e: Evaluation) => void; onDone: () => void }) {
  const doneRef = useRef(onDone); doneRef.current = onDone;
  const upRef = useRef(onUpdate); upRef.current = onUpdate;
  useEffect(() => {
    if (evaluation.status === "completed" || evaluation.status === "failed") return;
    const t = setInterval(async () => {
      try {
        const e = await api.get<Evaluation>(`/evaluations/${evaluation.id}`);
        upRef.current(e);
        if (e.status === "completed" || e.status === "failed") { clearInterval(t); doneRef.current(); }
      } catch { /* keep polling */ }
    }, 1500);
    return () => clearInterval(t);
  }, [evaluation.id, evaluation.status]);
  const idx = STEPS.findIndex(([k]) => k === evaluation.stage);
  return (
    <Card className="mx-auto max-w-xl p-8">
      <h2 className="text-lg font-semibold">AI evaluation in progress</h2>
      <p className="mb-5 mt-1 text-sm text-slate-500">This usually takes a few seconds. You can leave this page – we'll notify you when it's ready.</p>
      <ProgressBar value={evaluation.progress} />
      <ul className="mt-6 space-y-3">
        {STEPS.map(([k, label], i) => (
          <li key={k} className="flex items-center gap-3 text-sm">
            {i < idx || evaluation.progress === 100 ? <CheckCircle2 className="h-5 w-5 text-emerald-600" /> : i === idx ? <Loader2 className="h-5 w-5 animate-spin text-navy-600" /> : <Circle className="h-5 w-5 text-slate-300" />}
            <span className={i === idx ? "font-medium text-navy-900" : i < idx ? "text-slate-700" : "text-slate-400"}>{label}</span>
          </li>))}
      </ul>
    </Card>
  );
}
