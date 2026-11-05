from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Category, Evaluation, Idea, User
from ..services.evaluation import system_status

router = APIRouter(tags=["public"])


@router.get("/categories")
def categories(db: Session = Depends(get_db)):
    rows = db.scalars(select(Category).where(Category.is_active.is_(True)).order_by(Category.name))
    out = {"industries": [], "technologies": []}
    for c in rows:
        out["industries" if c.kind == "industry" else "technologies"].append(
            {"id": c.id, "name": c.name, "description": c.description})
    return out


@router.get("/system/status")
def status(db: Session = Depends(get_db)):
    return system_status()


@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    """Aggregate numbers for the landing page (no personal data)."""
    return {
        "ideas": db.scalar(select(func.count()).select_from(Idea).where(Idea.visibility != "private",
                                                                        Idea.moderation_status == "active")) or 0,
        "creators": db.scalar(select(func.count()).select_from(User).where(User.role == "creator")) or 0,
        "entrepreneurs": db.scalar(select(func.count()).select_from(User).where(User.role == "entrepreneur")) or 0,
        "evaluations": db.scalar(select(func.count()).select_from(Evaluation).where(Evaluation.status == "completed")) or 0,
    }
