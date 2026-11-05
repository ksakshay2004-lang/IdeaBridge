from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_optional_user
from ..models import Evaluation, Idea, User
from ..permissions import idea_access
from ..services.serializers import evaluation_out

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


@router.get("")
def my_evaluations(user: User = Depends(get_optional_user), db: Session = Depends(get_db)):
    """Latest evaluation of each of the creator's ideas (for the 'AI Evaluation Reports' page)."""
    if user is None or user.role != "creator":
        raise HTTPException(403, "Only creators can list their evaluations")
    out = []
    for idea in db.scalars(select(Idea).where(Idea.creator_id == user.id).order_by(Idea.created_at.desc())):
        if idea.evaluations:
            ev = evaluation_out(db, idea.evaluations[0], False)
            ev["idea_title"] = idea.title
            out.append(ev)
    return out


@router.get("/{evaluation_id}")
def read_evaluation(evaluation_id: int, user: User = Depends(get_optional_user), db: Session = Depends(get_db)):
    """Polling endpoint for progress; full report only when the caller has full access to the idea."""
    ev = db.get(Evaluation, evaluation_id)
    if not ev or idea_access(db, user, ev.idea) != "full":
        raise HTTPException(404, "Evaluation not found")
    owner = user is not None and (user.id == ev.idea.creator_id or user.role == "admin")
    if not owner and ev.status != "completed":
        raise HTTPException(404, "Evaluation not found")
    return evaluation_out(db, ev)
