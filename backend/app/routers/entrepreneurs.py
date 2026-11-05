from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_entrepreneur
from ..models import Idea, SavedIdea, User
from ..permissions import idea_access
from ..services.matching import score_match
from ..services.serializers import idea_cards

router = APIRouter(tags=["entrepreneur"])


@router.get("/saved")
def list_saved(user: User = Depends(require_entrepreneur), db: Session = Depends(get_db)):
    rows = db.scalars(select(SavedIdea).where(SavedIdea.user_id == user.id).order_by(SavedIdea.created_at.desc()))
    ideas = [r.idea_id for r in rows]
    objs = {i.id: i for i in db.scalars(select(Idea).where(Idea.id.in_(ideas)))} if ideas else {}
    visible = [objs[i] for i in ideas if i in objs and idea_access(db, user, objs[i]) != "none"]
    return idea_cards(db, visible, user)


@router.post("/saved/{idea_id}", status_code=201)
def save_idea(idea_id: int, user: User = Depends(require_entrepreneur), db: Session = Depends(get_db)):
    idea = db.get(Idea, idea_id)
    if not idea or idea_access(db, user, idea) == "none":
        raise HTTPException(404, "Idea not found")
    if not db.scalar(select(SavedIdea.id).where(SavedIdea.user_id == user.id, SavedIdea.idea_id == idea_id)):
        db.add(SavedIdea(user_id=user.id, idea_id=idea_id))
        db.commit()
    return {"saved": True}


@router.delete("/saved/{idea_id}")
def unsave_idea(idea_id: int, user: User = Depends(require_entrepreneur), db: Session = Depends(get_db)):
    row = db.scalar(select(SavedIdea).where(SavedIdea.user_id == user.id, SavedIdea.idea_id == idea_id))
    if row:
        db.delete(row)
        db.commit()
    return {"saved": False}


@router.get("/recommendations")
def recommendations(limit: int = 20, user: User = Depends(require_entrepreneur), db: Session = Depends(get_db)):
    """Ideas ranked by match score against the entrepreneur's profile, with explanations."""
    profile = user.entrepreneur_profile
    if profile is None:
        return []
    ideas = list(db.scalars(select(Idea).where(Idea.moderation_status == "active", Idea.visibility.in_(("public", "restricted")))
                            .order_by(Idea.created_at.desc()).limit(300)))
    scored = {i.id: score_match(i, profile) for i in ideas}
    ideas.sort(key=lambda i: -scored[i.id]["score"])
    top = ideas[:max(1, min(limit, 50))]
    extra = {i.id: {"match": {"score": scored[i.id]["score"], "reasons": scored[i.id]["reasons"],
                              "breakdown": scored[i.id]["breakdown"]}} for i in top}
    return idea_cards(db, top, user, extra)
