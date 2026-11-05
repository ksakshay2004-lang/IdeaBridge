"""Embedding access + vector search. PostgreSQL uses pgvector (<=> cosine distance, run in the database);
SQLite (dev/tests) falls back to exact in-process cosine search with the same semantics."""
import json
from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Tuple

from sqlalchemy import or_, select, text
from sqlalchemy.orm import Session

from ai_engine import get_embedder
from ai_engine.similarity import top_k

from ..config import get_settings
from ..models import EntrepreneurProfile, Idea, ReferenceProject

DATA_FILE = Path(__file__).resolve().parents[3] / "ai_engine" / "data" / "reference_projects.json"


@lru_cache
def embedder():
    s = get_settings()
    return get_embedder(s.embedding_provider, s.embedding_model, s.embedding_dim, s.openai_api_key, s.openai_base_url)


def idea_text(idea: Idea) -> str:
    return ". ".join([idea.title, idea.short_description, idea.problem, idea.solution, idea.industry,
                      ", ".join(idea.technologies or []), idea.target_audience])


def profile_text(p: EntrepreneurProfile) -> str:
    return ". ".join([", ".join(p.industries or []), ", ".join(p.technologies or []), p.interests or "",
                      ", ".join(p.target_markets or []), p.bio or ""])


def _lit(vec) -> str:
    return "[" + ",".join(f"{float(x):.7f}" for x in vec) + "]"


def refresh_idea_embedding(db: Session, idea: Idea) -> None:
    emb = embedder()
    idea.embedding = emb.embed_one(idea_text(idea))
    idea.embedding_model = emb.model


def refresh_profile_embedding(db: Session, profile: EntrepreneurProfile) -> None:
    text_ = profile_text(profile).strip(" .")
    emb = embedder()
    profile.embedding = emb.embed_one(text_) if text_ else None
    profile.embedding_model = emb.model if text_ else None


def ensure_reference_projects(db: Session) -> int:
    """Load the curated dataset and (re)embed rows whose embedding model differs from the configured one."""
    emb = embedder()
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    existing = {r.slug: r for r in db.scalars(select(ReferenceProject))}
    todo = []
    for d in data:
        row = existing.get(d["slug"])
        if row is None:
            row = ReferenceProject(slug=d["slug"], name=d["name"], category=d["category"],
                                   description=d["description"], url=d.get("url"))
            db.add(row)
        else:
            row.name, row.category, row.description, row.url = d["name"], d["category"], d["description"], d.get("url")
        if row.embedding is None or row.embedding_model != emb.model:
            todo.append(row)
    if todo:
        vecs = emb.embed([f"{r.name}. {r.description}" for r in todo])
        for r, v in zip(todo, vecs):
            r.embedding, r.embedding_model = v, emb.model
    db.commit()
    return len(data)


def search_references(db: Session, vec, k: int = 8) -> List[Tuple[ReferenceProject, float]]:
    model = embedder().model
    if db.bind.dialect.name == "postgresql":
        rows = db.execute(text(
            "SELECT id, 1 - (embedding <=> CAST(:q AS vector)) AS sim FROM reference_projects "
            "WHERE embedding IS NOT NULL AND embedding_model = :m "
            "ORDER BY embedding <=> CAST(:q AS vector) LIMIT :k"), {"q": _lit(vec), "m": model, "k": k}).all()
        ranked = [(r.id, float(r.sim)) for r in rows]
    else:
        items = db.execute(select(ReferenceProject.id, ReferenceProject.embedding).where(
            ReferenceProject.embedding.is_not(None), ReferenceProject.embedding_model == model)).all()
        ranked = top_k(vec, [(i, v) for i, v in items if v is not None], k)
    objs = {o.id: o for o in db.scalars(select(ReferenceProject).where(ReferenceProject.id.in_([i for i, _ in ranked])))}
    return [(objs[i], s) for i, s in ranked if i in objs]


def _platform_filter(model: str, exclude_id: Optional[int], creator_id: Optional[int]):
    conds = [Idea.embedding.is_not(None), Idea.embedding_model == model, Idea.moderation_status == "active",
             or_(Idea.visibility.in_(("public", "restricted")), Idea.creator_id == creator_id)]
    if exclude_id is not None:
        conds.append(Idea.id != exclude_id)
    return conds


def count_platform_ideas(db: Session, exclude_id: Optional[int], creator_id: Optional[int]) -> int:
    from sqlalchemy import func
    return db.scalar(select(func.count()).select_from(Idea).where(
        *_platform_filter(embedder().model, exclude_id, creator_id))) or 0


def search_platform_ideas(db: Session, vec, k: int = 5, exclude_id: Optional[int] = None,
                          creator_id: Optional[int] = None) -> List[Tuple[Idea, float]]:
    """Nearest platform ideas. Private ideas of OTHER creators are never searched (no existence oracle)."""
    model = embedder().model
    if db.bind.dialect.name == "postgresql":
        rows = db.execute(text(
            "SELECT id, 1 - (embedding <=> CAST(:q AS vector)) AS sim FROM ideas "
            "WHERE embedding IS NOT NULL AND embedding_model = :m AND moderation_status = 'active' "
            "AND (visibility IN ('public','restricted') OR creator_id = :c) AND id <> :ex "
            "ORDER BY embedding <=> CAST(:q AS vector) LIMIT :k"),
            {"q": _lit(vec), "m": model, "c": creator_id or -1, "ex": exclude_id or -1, "k": k}).all()
        ranked = [(r.id, float(r.sim)) for r in rows]
    else:
        items = db.execute(select(Idea.id, Idea.embedding).where(*_platform_filter(model, exclude_id, creator_id))).all()
        ranked = top_k(vec, [(i, v) for i, v in items if v is not None], k)
    objs = {o.id: o for o in db.scalars(select(Idea).where(Idea.id.in_([i for i, _ in ranked])))}
    return [(objs[i], s) for i, s in ranked if i in objs]
