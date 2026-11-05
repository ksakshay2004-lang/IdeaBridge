"""Background AI evaluation pipeline: understand -> embed -> retrieve (pgvector) -> analyse -> persist."""
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ai_engine import EvaluationEngine, Retrieved, get_llm
from ai_engine.embeddings import EmbeddingError, keywords
from ai_engine.external import fetch_arxiv
from ai_engine.similarity import cosine

from ..config import get_settings
from ..database import SessionLocal
from ..models import Evaluation, Idea, ReferenceProject, SimilarityResult
from . import vectors
from .notifications import notify

log = logging.getLogger("ideabridge.evaluation")


def idea_payload(idea: Idea) -> dict:
    return {k: getattr(idea, k) for k in ("title", "short_description", "problem", "solution", "industry",
                                          "target_audience", "technologies", "stage", "expected_impact",
                                          "business_potential", "funding_needed")}


def build_engine(force_demo: bool = False) -> EvaluationEngine:
    s = get_settings()
    llm = None if force_demo else get_llm(s.llm_provider, s.llm_model, s.anthropic_api_key, s.openai_api_key,
                                          s.openai_base_url)
    return EvaluationEngine(llm, vectors.embedder().describe())


def system_status() -> dict:
    s, emb = get_settings(), vectors.embedder()
    llm = get_llm(s.llm_provider, s.llm_model, s.anthropic_api_key, s.openai_api_key, s.openai_base_url)
    return {"evaluation_mode": "live_llm" if llm else "demo",
            "llm_provider": llm.name if llm else None, "llm_model": llm.model if llm else None,
            "embedding": emb.describe(), "external_retrieval": s.external_retrieval,
            "demo_notice": None if llm else ("DEMO MODE: no LLM API key is configured, so evaluations use a "
                                              "local rule-based engine instead of an AI model.")}


def create_evaluation(db: Session, idea: Idea) -> Evaluation:
    last = db.scalar(select(func.max(Evaluation.version)).where(Evaluation.idea_id == idea.id)) or 0
    ev = Evaluation(idea_id=idea.id, version=last + 1, status="queued", stage="queued", progress=0)
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev


def _set(db: Session, ev: Evaluation, stage: str, progress: int) -> None:
    ev.status, ev.stage, ev.progress = "running", stage, progress
    db.commit()


def run_evaluation(evaluation_id: int, force_demo: bool = False) -> None:
    """Entry point for BackgroundTasks. Owns its own DB session."""
    with SessionLocal() as db:
        ev = db.get(Evaluation, evaluation_id)
        if ev is None:
            return
        try:
            _pipeline(db, ev, force_demo)
        except EmbeddingError as e:
            _fail(db, ev, f"Embedding service error: {e}")
        except Exception:  # noqa: BLE001
            log.exception("evaluation %s failed", evaluation_id)
            _fail(db, ev, "Evaluation failed unexpectedly. Please try again.")


def _fail(db: Session, ev: Evaluation, msg: str) -> None:
    db.rollback()
    ev = db.get(Evaluation, ev.id)
    ev.status, ev.stage, ev.error, ev.completed_at = "failed", "failed", msg[:300], datetime.now(timezone.utc)
    idea = db.get(Idea, ev.idea_id)
    if idea:
        notify(db, idea.creator_id, "evaluation_failed", "AI evaluation failed", f"{idea.title}: {msg}"[:500],
               f"/app/creator/ideas/{idea.id}")
    db.commit()


def _pipeline(db: Session, ev: Evaluation, force_demo: bool) -> None:
    idea = db.get(Idea, ev.idea_id)
    s, emb = get_settings(), vectors.embedder()
    engine = build_engine(force_demo)
    _set(db, ev, "understanding", 10)
    text = vectors.idea_text(idea)

    _set(db, ev, "embedding", 30)
    vec = emb.embed_one(text)
    idea.embedding, idea.embedding_model = vec, emb.model
    db.commit()

    _set(db, ev, "retrieving", 50)
    floor = engine.floor
    refs = vectors.search_references(db, vec, 8)
    keep = [r for i, r in enumerate(refs) if i < 3 or r[1] >= floor]
    retrieved = [Retrieved(id=r.slug, kind="reference", title=r.name, description=r.description, similarity=sim,
                           url=r.url, category=r.category) for r, sim in keep]
    for other, sim in vectors.search_platform_ideas(db, vec, 4, idea.id, idea.creator_id):
        if sim < floor:
            continue
        public = other.visibility == "public" and other.moderation_status == "active"
        retrieved.append(Retrieved(id=f"idea:{other.id}", kind="platform",
                                   title=other.title if public else "Another idea on IdeaBridge (details withheld)",
                                   description=other.short_description if public else "", similarity=sim,
                                   visible=public))
    papers = 0
    if s.external_retrieval == "arxiv":
        try:
            found = fetch_arxiv(keywords(text, 6) + list(idea.technologies or [])[:2], 5)
            if found:
                pvecs = emb.embed([f"{p['title']}. {p['summary']}" for p in found])
                for p, pv in zip(found, pvecs):
                    retrieved.append(Retrieved(id=p["id"], kind="research_paper", title=p["title"],
                                               description=p["summary"][:600], similarity=cosine(vec, pv), url=p["url"]))
                papers = len(found)
        except Exception as e:  # optional feature: never fail the evaluation because of it
            log.warning("arXiv retrieval skipped: %s", type(e).__name__)

    _set(db, ev, "analysing", 75)
    corpus = {"reference_count": db.scalar(select(func.count()).select_from(ReferenceProject)) or 0,
              "platform_count": vectors.count_platform_ideas(db, idea.id, idea.creator_id),
              "paper_count": papers, "embedding_kind": emb.kind}
    report = engine.evaluate(idea_payload(idea), retrieved, corpus)

    _set(db, ev, "finalizing", 92)
    sc, meta = report["scores"], report["meta"]
    ev.report, ev.mode, ev.provider, ev.model = report, meta["mode"], meta["provider"], meta["model"]
    ev.technical_score, ev.market_score = sc["technical_feasibility"], sc["market_opportunity"]
    ev.innovation_score, ev.overall_score = sc["innovation_differentiation"], sc["overall"]
    competitors = {c["ref_id"] for c in report["competitors"]}
    for sp in report["similar_projects"]:
        ref = sp["ref_id"].split(":", 1)[1] if sp["kind"] == "platform" else sp["ref_id"]
        db.add(SimilarityResult(evaluation_id=ev.id, source_type=sp["kind"], source_ref=ref[:300], title=sp["title"][:300],
                                url=(sp["url"] or None), similarity=sp["similarity_pct"],
                                differences=sp["key_differences"], is_competitor=sp["ref_id"] in competitors))
    ev.status, ev.stage, ev.progress, ev.error = "completed", "completed", 100, None
    ev.completed_at = datetime.now(timezone.utc)
    notify(db, idea.creator_id, "evaluation_done", "AI evaluation ready",
           f"{idea.title} — overall score {sc['overall']}/100 ({'demo' if meta['mode'] == 'demo' else 'live AI'})",
           f"/app/creator/ideas/{idea.id}")
    db.commit()
