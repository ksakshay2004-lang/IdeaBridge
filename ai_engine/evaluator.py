"""Evaluation orchestration: retrieval evidence -> LLM (or local demo engine) -> validated report.

Anti-fabrication rules enforced in code (not just in the prompt):
  * similar_projects are built ONLY from retrieved items; similarity % is the computed cosine.
  * competitor ids / per-item notes returned by the LLM are ignored unless they match a retrieved id.
  * hidden (non-public) platform ideas are never sent to the LLM.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

from . import schema as S
from .demo_engine import demo_evaluate
from .llm import LLMProvider

SYSTEM_PROMPT = """You are the evaluation agent of IdeaBridge, an innovation marketplace.
Assess ONE submitted idea objectively and critically using ONLY the idea text and the retrieved evidence provided.
Rules:
- NEVER invent companies, products, papers, URLs or statistics. Refer to other work only via the provided retrieved_items (by id).
- similarity_pct values are computed by software; do not restate or alter them.
- If evidence is thin, say so. Be balanced; do not flatter. Scores are integers 0-100.
- Respond with ONE JSON object only, no markdown, with exactly these keys:
{"idea_summary":str,"problem_statement":str,"proposed_solution":str,
 "similar_project_notes":[{"id":str,"key_differences":str}],
 "novelty_assessment":{"level":"low|moderate|high","rationale":str},
 "scores":{"technical_feasibility":int,"market_opportunity":int,"innovation_differentiation":int},
 "development_complexity":{"level":"low|moderate|high","rationale":str},
 "target_users":[str],"revenue_models":[str],"competitor_ids":[str],
 "strengths":[str],"weaknesses":[str],"risks":[str],"recommended_improvements":[str],"overall_evaluation":str}"""


@dataclass
class Retrieved:
    id: str
    kind: str            # reference | platform | research_paper
    title: str
    description: str
    similarity: float    # cosine, -1..1
    url: Optional[str] = None
    category: Optional[str] = None
    visible: bool = True  # False => details must not leave the platform (not sent to LLM, not shown)


class EvaluationEngine:
    def __init__(self, llm: Optional[LLMProvider], embedder_info: Optional[dict] = None):
        self.llm = llm
        self.embedder_info = embedder_info or {"name": "unknown", "kind": "lexical", "model": ""}

    @property
    def floor(self) -> float:
        return 0.10 if self.embedder_info.get("kind") == "lexical" else 0.25

    @property
    def ceiling(self) -> float:
        return 0.45 if self.embedder_info.get("kind") == "lexical" else 0.75

    def evaluate(self, idea: Dict, retrieved: List[Retrieved], corpus: Optional[Dict] = None,
                 sim_floor: Optional[float] = None) -> Dict:
        corpus = dict(corpus or {})
        corpus.setdefault("embedding_kind", self.embedder_info.get("kind"))
        floor = self.floor if sim_floor is None else sim_floor
        retrieved = sorted(retrieved, key=lambda r: -r.similarity)
        meta = {"generated_at": datetime.now(timezone.utc).isoformat(), "embedding": self.embedder_info}
        body, fallback_reason = None, None
        if self.llm is not None:
            try:
                body = self._run_llm(idea, retrieved)
                meta.update(mode="live_llm", provider=self.llm.name, model=self.llm.model, notice=None)
            except Exception as e:  # any failure => clearly labelled demo fallback
                fallback_reason = f"{type(e).__name__}: {e}"[:200]
        if body is None:
            body = demo_evaluate(idea, retrieved, floor, self.ceiling, corpus)
            meta.update(mode="demo", provider="local-rule-engine", model="demo-v1", notice=(
                "DEMO MODE: this report was produced by a local rule-based engine, not by an AI model. "
                "Scores are rough heuristics. Similarity percentages are real vector-similarity calculations."))
            if fallback_reason:
                meta["fallback_reason"] = fallback_reason
                meta["notice"] += " The configured live LLM call failed, so the demo engine was used instead."
        return self._assemble(body, retrieved, meta, corpus, floor)

    # ---------------------------------------------------------------- LLM path
    def _run_llm(self, idea: Dict, retrieved: List[Retrieved]) -> Dict:
        items = [{"id": r.id, "kind": r.kind, "title": r.title, "description": r.description[:600],
                  "url": r.url, "similarity_pct": round(max(0.0, r.similarity) * 100, 1)}
                 for r in retrieved if r.visible]
        hidden = sum(1 for r in retrieved if not r.visible)
        user = json.dumps({
            "idea": {k: idea.get(k) for k in ("title", "short_description", "problem", "solution", "industry",
                                               "target_audience", "technologies", "stage", "expected_impact",
                                               "business_potential", "funding_needed")},
            "retrieved_items": items,
            "notes": {"similarity_method": self.embedder_info, "hidden_platform_matches": hidden,
                      "limitation": "retrieved_items is a small curated comparison set, not the whole market"},
        }, ensure_ascii=False)
        raw = self.llm.complete_json(SYSTEM_PROMPT, user)
        return S.extract_json(raw)

    # ---------------------------------------------------------------- assembly
    def _assemble(self, body: Dict, retrieved: List[Retrieved], meta: Dict, corpus: Dict, floor: float) -> Dict:
        by_id = {r.id: r for r in retrieved}
        notes = body.get("similar_project_notes") or {}
        if isinstance(notes, list):
            notes = {n.get("id"): n.get("key_differences") for n in notes if isinstance(n, dict)}
        similar = []
        for r in retrieved:
            similar.append({
                "ref_id": r.id, "kind": r.kind,
                "title": r.title if r.visible else "Another idea on IdeaBridge (details withheld)",
                "url": r.url if r.visible else None,
                "similarity_pct": round(max(0.0, r.similarity) * 100, 1),
                "key_differences": S.as_str(notes.get(r.id), 600) if r.visible else "",
            })
        comp_ids = [c for c in S.as_str_list(body.get("competitor_ids"), 6, 120)
                    if c in by_id and by_id[c].visible and by_id[c].kind != "platform"]
        competitors = [{"ref_id": c, "name": by_id[c].title, "url": by_id[c].url,
                        "similarity_pct": round(max(0.0, by_id[c].similarity) * 100, 1)} for c in comp_ids]

        sc = body.get("scores") or {}
        tech = S.clamp_score(sc.get("technical_feasibility"))
        market = S.clamp_score(sc.get("market_opportunity"))
        innov = S.clamp_score(sc.get("innovation_differentiation"))
        max_sim = max((r.similarity for r in retrieved), default=0.0)
        if self.embedder_info.get("kind") != "lexical" and max_sim >= 0.85:
            innov = min(innov, 40)  # near-duplicate evidence caps the differentiation score
        overall = round(0.35 * tech + 0.35 * market + 0.30 * innov)

        nov = body.get("novelty_assessment") or {}
        cplx = body.get("development_complexity") or {}
        return {
            "meta": meta,
            "idea_summary": S.as_str(body.get("idea_summary")),
            "problem_statement": S.as_str(body.get("problem_statement")),
            "proposed_solution": S.as_str(body.get("proposed_solution")),
            "similar_projects": similar,
            "novelty_assessment": {"level": S.as_level(nov.get("level")), "rationale": S.as_str(nov.get("rationale"))},
            "scores": {"technical_feasibility": tech, "market_opportunity": market,
                       "innovation_differentiation": innov, "overall": overall},
            "development_complexity": {"level": S.as_level(cplx.get("level")),
                                       "rationale": S.as_str(cplx.get("rationale"))},
            "target_users": S.as_str_list(body.get("target_users")),
            "revenue_models": S.as_str_list(body.get("revenue_models")),
            "competitors": competitors,
            "strengths": S.as_str_list(body.get("strengths")),
            "weaknesses": S.as_str_list(body.get("weaknesses")),
            "risks": S.as_str_list(body.get("risks")),
            "recommended_improvements": S.as_str_list(body.get("recommended_improvements")),
            "overall_evaluation": S.as_str(body.get("overall_evaluation")),
            "evidence": {
                "retrieved_count": len(retrieved), "max_similarity_pct": round(max(0.0, max_sim) * 100, 1),
                "reference_projects_searched": corpus.get("reference_count", 0),
                "platform_ideas_searched": corpus.get("platform_count", 0),
                "research_papers_searched": corpus.get("paper_count", 0),
                "similarity_method": ("lexical word-overlap (offline hashing embeddings)"
                                      if self.embedder_info.get("kind") == "lexical"
                                      else "semantic text embeddings"),
                "relevance_floor_pct": round(floor * 100, 1),
                "limitation": "Compared only with the curated dataset, public/restricted platform ideas"
                              " and (optionally) arXiv results, not the whole market.",
            },
        }
