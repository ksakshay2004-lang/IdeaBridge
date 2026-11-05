"""Central authorisation rules for ideas. Every idea-returning endpoint must go through idea_access()."""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import CollaborationRequest, Idea, User


def has_accepted_collab(db: Session, user_id: int, idea_id: int) -> bool:
    return db.scalar(select(CollaborationRequest.id).where(
        CollaborationRequest.idea_id == idea_id, CollaborationRequest.entrepreneur_id == user_id,
        CollaborationRequest.status == "accepted").limit(1)) is not None


def idea_access(db: Session, user: Optional[User], idea: Idea) -> str:
    """Return 'full' | 'teaser' | 'none'.

    full   - owner, admin, any signed-in user for PUBLIC ideas, and entrepreneurs whose collaboration
             request for a RESTRICTED idea was accepted.
    teaser - title/short description/industry only (public ideas for anonymous visitors; restricted ideas
             for everyone without an accepted request).
    none   - private ideas, and anything hidden/removed by moderation (unless owner/admin).
    """
    if user is not None and user.role == "admin":
        return "full"
    if user is not None and idea.creator_id == user.id:
        return "full"
    if idea.moderation_status != "active" or idea.visibility == "private":
        return "none"
    if idea.visibility == "public":
        return "full" if user is not None else "teaser"
    if user is None:
        return "none"
    if user.role == "entrepreneur" and has_accepted_collab(db, user.id, idea.id):
        return "full"
    return "teaser"
