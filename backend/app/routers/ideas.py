from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ai_engine.embeddings import EmbeddingError
from ai_engine.similarity import cosine

from ..database import get_db
from ..deps import get_current_user, get_optional_user, require_creator
from ..embedding_guard import safe_embed
from ..models import (Category, ContentReport, EntrepreneurProfile, Evaluation, Idea, User)
from ..permissions import idea_access
from ..schemas import IdeaIn, IdeaUpdate, ReportIn
from ..services import vectors
from ..services.evaluation import create_evaluation, run_evaluation
from ..services.files import delete_stored
from ..services.matching import score_match
from ..services.notifications import notify
from ..services.serializers import evaluation_out, idea_cards, idea_detail, latest_completed, user_brief

router = APIRouter(prefix="/ideas", tags=["ideas"])
CORE_FIELDS = {"title", "short_description", "problem", "solution", "industry", "technologies", "target_audience"}


def canonical_industry(db: Session, name: str) -> str:
    cat = db.scalar(select(Category).where(Category.kind == "industry", Category.is_active.is_(True),
                                           func.lower(Category.name) == name.strip().lower()))
    if not cat:
        raise HTTPException(422, "Unknown industry. Choose one from the list of categories.")
    return cat.name


def get_idea_or_404(db: Session, idea_id: int) -> Idea:
    idea = db.get(Idea, idea_id)
    if not idea:
        raise HTTPException(404, "Idea not found")
    return idea


def visible_idea(db: Session, idea_id: int, user: Optional[User]):
    """Load an idea and compute access; 404 (never 403) when the caller may not even know it exists."""
    idea = get_idea_or_404(db, idea_id)
    access = idea_access(db, user, idea)
    if access == "none":
        raise HTTPException(404, "Idea not found")
    return idea, access


def require_owner(idea: Idea, user: User) -> None:
    if idea.creator_id != user.id:
        raise HTTPException(404, "Idea not found")


@router.get("/featured")
def featured(limit: int = Query(6, ge=1, le=12), db: Session = Depends(get_db)):
    ideas = list(db.scalars(select(Idea).where(Idea.visibility == "public", Idea.moderation_status == "active")
                            .order_by(Idea.created_at.desc()).limit(60)))
    evs = latest_completed(db, [i.id for i in ideas])
    ideas.sort(key=lambda i: -(evs[i.id].overall_score if i.id in evs else -1))
    return idea_cards(db, ideas[:limit], None)


@router.get("/mine")
def my_ideas(user: User = Depends(require_creator), db: Session = Depends(get_db)):
    ideas = list(db.scalars(select(Idea).where(Idea.creator_id == user.id).order_by(Idea.created_at.desc())))
    extra = {}
    for i in ideas:
        ev = i.evaluations[0] if i.evaluations else None
        extra[i.id] = {"evaluation": {"id": ev.id, "status": ev.status, "progress": ev.progress,
                                      "mode": ev.mode} if ev else None,
                       "pending_requests": 0}
    from ..models import CollaborationRequest
    counts = dict(db.execute(select(CollaborationRequest.idea_id, func.count()).where(
        CollaborationRequest.creator_id == user.id, CollaborationRequest.status == "pending")
        .group_by(CollaborationRequest.idea_id)).all())
    for iid, c in counts.items():
        if iid in extra:
            extra[iid]["pending_requests"] = c
    return idea_cards(db, ideas, user, extra)


@router.get("")
def explore(q: Optional[str] = Query(None, max_length=200), industry: Optional[str] = None,
            technology: Optional[str] = None, stage: Optional[str] = None,
            sort: str = Query("newest", pattern="^(newest|score|relevance)$"), semantic: bool = False,
            page: int = Query(1, ge=1), page_size: int = Query(12, ge=1, le=50),
            user: Optional[User] = Depends(get_optional_user), db: Session = Depends(get_db)):
    vis = ("public",) if user is None else ("public", "restricted")
    conds = [Idea.moderation_status == "active", Idea.visibility.in_(vis)]
    if industry:
        conds.append(func.lower(Idea.industry) == industry.lower())
    if stage:
        conds.append(Idea.stage == stage)
    if q and not semantic:
        like = f"%{q.strip().lower()}%"
        conds.append(or_(func.lower(Idea.title).like(like), func.lower(Idea.short_description).like(like),
                         func.lower(Idea.industry).like(like)))
    ideas: List[Idea] = list(db.scalars(select(Idea).where(*conds).order_by(Idea.created_at.desc()).limit(1000)))
    if technology:
        t = technology.lower()
        ideas = [i for i in ideas if t in [x.lower() for x in (i.technologies or [])]]
    relevance = {}
    if q and semantic:
        try:
            qv = vectors.embedder().embed_one(q)
            model = vectors.embedder().model
            for i in ideas:
                if i.embedding is not None and i.embedding_model == model:
                    relevance[i.id] = cosine(qv, i.embedding)
            ideas = [i for i in ideas if i.id in relevance]
            sort = "relevance"
        except EmbeddingError:
            like = q.lower()
            ideas = [i for i in ideas if like in (i.title + " " + i.short_description).lower()]
    evs = latest_completed(db, [i.id for i in ideas])
    if sort == "score":
        ideas.sort(key=lambda i: -(evs[i.id].overall_score if i.id in evs else -1))
    elif sort == "relevance" and relevance:
        ideas.sort(key=lambda i: -relevance.get(i.id, -1))
    total = len(ideas)
    chunk = ideas[(page - 1) * page_size: page * page_size]
    extra = {i.id: {"relevance": round(max(0.0, relevance[i.id]) * 100, 1)} for i in chunk if i.id in relevance}
    return {"items": idea_cards(db, chunk, user, extra), "total": total, "page": page, "page_size": page_size}


@router.post("", status_code=201)
def create_idea(body: IdeaIn, background: BackgroundTasks, user: User = Depends(require_creator),
                db: Session = Depends(get_db)):
    data = body.model_dump()
    data["industry"] = canonical_industry(db, data["industry"])
    idea = Idea(creator_id=user.id, **data)
    db.add(idea)
    db.commit()
    db.refresh(idea)
    ev = create_evaluation(db, idea)
    background.add_task(run_evaluation, ev.id)
    return {"idea": idea_detail(db, idea, user, "full"), "evaluation": evaluation_out(db, ev, False)}


@router.get("/{idea_id}")
def read_idea(idea_id: int, user: Optional[User] = Depends(get_optional_user), db: Session = Depends(get_db)):
    idea, access = visible_idea(db, idea_id, user)
    return idea_detail(db, idea, user, access)


@router.put("/{idea_id}")
def update_idea(idea_id: int, body: IdeaUpdate, user: User = Depends(require_creator), db: Session = Depends(get_db)):
    idea = get_idea_or_404(db, idea_id)
    require_owner(idea, user)
    changes = body.model_dump(exclude_unset=True)
    for k in ("title", "short_description", "problem", "solution", "industry", "target_audience"):
        if k in changes and changes[k] is None:
            raise HTTPException(422, f"{k} cannot be empty")
    if "industry" in changes:
        changes["industry"] = canonical_industry(db, changes["industry"])
    for k, v in changes.items():
        setattr(idea, k, v)
    if CORE_FIELDS & changes.keys():
        safe_embed(lambda: vectors.refresh_idea_embedding(db, idea))
    db.commit()
    db.refresh(idea)
    return idea_detail(db, idea, user, "full")


@router.delete("/{idea_id}", status_code=204)
def delete_idea(idea_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    idea = get_idea_or_404(db, idea_id)
    if idea.creator_id != user.id:
        raise HTTPException(404, "Idea not found")
    for d in idea.documents:
        delete_stored(d.stored_name)
    db.delete(idea)
    db.commit()


@router.post("/{idea_id}/evaluate", status_code=202)
def re_evaluate(idea_id: int, background: BackgroundTasks, user: User = Depends(require_creator),
                db: Session = Depends(get_db)):
    idea = get_idea_or_404(db, idea_id)
    require_owner(idea, user)
    latest = idea.evaluations[0] if idea.evaluations else None
    if latest and latest.status in ("queued", "running") and \
            (datetime.now(timezone.utc) - (latest.created_at if latest.created_at.tzinfo else
                                           latest.created_at.replace(tzinfo=timezone.utc))) < timedelta(minutes=10):
        raise HTTPException(409, "An evaluation is already in progress for this idea")
    ev = create_evaluation(db, idea)
    background.add_task(run_evaluation, ev.id)
    return evaluation_out(db, ev, False)


@router.get("/{idea_id}/evaluation")
def idea_evaluation(idea_id: int, user: Optional[User] = Depends(get_optional_user), db: Session = Depends(get_db)):
    idea, access = visible_idea(db, idea_id, user)
    if access != "full":
        raise HTTPException(403, "The evaluation report is not available for this idea")
    owner = user is not None and (user.id == idea.creator_id or user.role == "admin")
    evs = list(idea.evaluations)
    done = next((e for e in evs if e.status == "completed"), None)
    latest = evs[0] if evs else None
    if owner and latest and latest.status != "completed" and (done is None or latest.version > done.version):
        return {"current": evaluation_out(db, latest, False), "latest_completed": evaluation_out(db, done) if done else None}
    if done is None:
        raise HTTPException(404, "No completed evaluation yet")
    return {"current": evaluation_out(db, done), "latest_completed": evaluation_out(db, done)}


@router.get("/{idea_id}/matches")
def idea_matches(idea_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    idea = get_idea_or_404(db, idea_id)
    if user.role != "admin" and idea.creator_id != user.id:
        raise HTTPException(404, "Idea not found")
    profiles = db.scalars(select(EntrepreneurProfile).join(User, User.id == EntrepreneurProfile.user_id)
                          .where(User.is_active.is_(True)).limit(500))
    out = []
    for p in profiles:
        m = score_match(idea, p)
        if m["score"] > 0:
            out.append({"entrepreneur": {**user_brief(p.user), "company_name": p.company_name,
                                         "company_type": p.company_type, "industries": p.industries or []},
                        "score": m["score"], "reasons": m["reasons"], "breakdown": m["breakdown"]})
    out.sort(key=lambda r: -r["score"])
    return out[:10]


@router.post("/{idea_id}/report", status_code=201)
def report_idea(idea_id: int, body: ReportIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    idea, _ = visible_idea(db, idea_id, user)
    if idea.creator_id == user.id:
        raise HTTPException(400, "You cannot report your own idea")
    dup = db.scalar(select(ContentReport.id).where(ContentReport.idea_id == idea.id, ContentReport.reporter_id == user.id,
                                                   ContentReport.status == "open"))
    if dup:
        raise HTTPException(409, "You have already reported this idea")
    db.add(ContentReport(reporter_id=user.id, idea_id=idea.id, reason=body.reason, details=body.details.strip()))
    db.commit()
    return {"ok": True}
