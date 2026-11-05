from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select, true
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, require_creator, require_entrepreneur
from ..models import CollaborationRequest, Idea, User
from ..permissions import idea_access
from ..schemas import CollabIn, CollabRespondIn
from ..services.notifications import notify
from ..services.serializers import iso, user_brief

router = APIRouter(prefix="/collaboration", tags=["collaboration"])


def out(r: CollaborationRequest) -> dict:
    return {"id": r.id, "idea_id": r.idea_id, "idea_title": r.idea.title, "kind": r.kind, "message": r.message,
            "status": r.status, "response_message": r.response_message, "created_at": iso(r.created_at),
            "updated_at": iso(r.updated_at), "entrepreneur": user_brief(r.entrepreneur), "creator": user_brief(r.creator)}


@router.post("", status_code=201)
def create_request(body: CollabIn, user: User = Depends(require_entrepreneur), db: Session = Depends(get_db)):
    idea = db.get(Idea, body.idea_id)
    if not idea or idea_access(db, user, idea) == "none":
        raise HTTPException(404, "Idea not found")
    open_req = db.scalar(select(CollaborationRequest.id).where(
        CollaborationRequest.idea_id == idea.id, CollaborationRequest.entrepreneur_id == user.id,
        CollaborationRequest.status.in_(("pending", "accepted"))))
    if open_req:
        raise HTTPException(409, "You already have an active request for this idea")
    req = CollaborationRequest(idea_id=idea.id, entrepreneur_id=user.id, creator_id=idea.creator_id,
                               kind=body.kind, message=body.message.strip())
    db.add(req)
    company = user.entrepreneur_profile.company_name if user.entrepreneur_profile else ""
    notify(db, idea.creator_id, "collab_request", "New collaboration request",
           f"{user.full_name}{' (' + company + ')' if company else ''} wants to {body.kind} on “{idea.title}”",
           "/app/creator/collaboration")
    db.commit()
    db.refresh(req)
    return out(req)


@router.get("")
def list_requests(status: Optional[str] = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role == "creator":
        cond = CollaborationRequest.creator_id == user.id
    elif user.role == "entrepreneur":
        cond = CollaborationRequest.entrepreneur_id == user.id
    else:
        cond = true()
    q = select(CollaborationRequest).where(cond).order_by(CollaborationRequest.created_at.desc())
    if status:
        q = q.where(CollaborationRequest.status == status)
    return [out(r) for r in db.scalars(q.limit(200))]


@router.post("/{request_id}/respond")
def respond(request_id: int, body: CollabRespondIn, user: User = Depends(require_creator), db: Session = Depends(get_db)):
    r = db.get(CollaborationRequest, request_id)
    if not r or r.creator_id != user.id:
        raise HTTPException(404, "Request not found")
    if r.status != "pending":
        raise HTTPException(409, f"This request is already {r.status}")
    r.status = "accepted" if body.action == "accept" else "declined"
    r.response_message = body.message.strip()
    notify(db, r.entrepreneur_id, "collab_" + r.status, f"Request {r.status}",
           f"{user.full_name} {r.status} your request for “{r.idea.title}”." +
           (" You now have full access to the idea." if r.status == "accepted" else ""), f"/app/entrepreneur/ideas/{r.idea_id}")
    db.commit()
    return out(r)


@router.post("/{request_id}/withdraw")
def withdraw(request_id: int, user: User = Depends(require_entrepreneur), db: Session = Depends(get_db)):
    r = db.get(CollaborationRequest, request_id)
    if not r or r.entrepreneur_id != user.id:
        raise HTTPException(404, "Request not found")
    if r.status not in ("pending", "accepted"):
        raise HTTPException(409, f"This request is already {r.status}")
    r.status = "withdrawn"
    notify(db, r.creator_id, "collab_withdrawn", "Request withdrawn",
           f"{user.full_name} withdrew their request for “{r.idea.title}”.", "/app/creator/collaboration")
    db.commit()
    return out(r)
