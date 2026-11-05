from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import CollaborationRequest, Idea, Message, User
from ..permissions import idea_access
from ..schemas import MessageIn
from ..services.notifications import notify
from ..services.serializers import iso, user_brief

router = APIRouter(prefix="/messages", tags=["messages"])


def can_message(db: Session, sender: User, recipient: User) -> bool:
    """Anti-spam: entrepreneurs may contact creators; creators may reply or write to entrepreneurs
    who have a collaboration request with them or have already written to them."""
    if sender.id == recipient.id or not recipient.is_active:
        return False
    if sender.role == "admin" or recipient.role == "admin":
        return True
    if sender.role == "entrepreneur" and recipient.role == "creator":
        return True
    if sender.role == "creator" and recipient.role == "entrepreneur":
        had_request = db.scalar(select(CollaborationRequest.id).where(
            CollaborationRequest.creator_id == sender.id, CollaborationRequest.entrepreneur_id == recipient.id).limit(1))
        had_message = db.scalar(select(Message.id).where(Message.sender_id == recipient.id,
                                                         Message.recipient_id == sender.id).limit(1))
        return bool(had_request or had_message)
    return False


@router.get("/conversations")
def conversations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    msgs = db.scalars(select(Message).where(or_(Message.sender_id == user.id, Message.recipient_id == user.id))
                      .order_by(Message.created_at.desc()).limit(2000))
    seen, out = {}, []
    for m in msgs:
        other = m.recipient_id if m.sender_id == user.id else m.sender_id
        if other not in seen:
            seen[other] = {"user_id": other, "last_message": m.body[:140], "last_at": iso(m.created_at),
                           "last_from_me": m.sender_id == user.id, "unread": 0}
            out.append(seen[other])
        if m.recipient_id == user.id and m.read_at is None:
            seen[other]["unread"] += 1
    users = {u.id: u for u in db.scalars(select(User).where(User.id.in_(list(seen))))} if seen else {}
    for c in out:
        c["user"] = user_brief(users[c["user_id"]]) if c["user_id"] in users else None
    return [c for c in out if c["user"]]


@router.get("/thread/{other_id}")
def thread(other_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    other = db.get(User, other_id)
    if not other:
        raise HTTPException(404, "User not found")
    pair = or_(and_(Message.sender_id == user.id, Message.recipient_id == other_id),
               and_(Message.sender_id == other_id, Message.recipient_id == user.id))
    msgs = list(db.scalars(select(Message).where(pair).order_by(Message.created_at).limit(500)))
    db.execute(update(Message).where(Message.sender_id == other_id, Message.recipient_id == user.id,
                                     Message.read_at.is_(None)).values(read_at=datetime.now(timezone.utc)))
    db.commit()
    return {"user": user_brief(other), "can_send": can_message(db, user, other),
            "messages": [{"id": m.id, "sender_id": m.sender_id, "body": m.body, "idea_id": m.idea_id,
                          "created_at": iso(m.created_at)} for m in msgs]}


@router.post("", status_code=201)
def send(body: MessageIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    recipient = db.get(User, body.recipient_id)
    if not recipient or not can_message(db, user, recipient):
        raise HTTPException(403, "You cannot message this user")
    idea_id = None
    if body.idea_id:
        idea = db.get(Idea, body.idea_id)
        if idea and idea_access(db, user, idea) != "none":
            idea_id = idea.id
    m = Message(sender_id=user.id, recipient_id=recipient.id, idea_id=idea_id, body=body.body.strip())
    db.add(m)
    notify(db, recipient.id, "message", f"New message from {user.full_name}", body.body.strip()[:140],
           f"/app/{recipient.role}/messages?with={user.id}")
    db.commit()
    return {"id": m.id, "sender_id": m.sender_id, "body": m.body, "idea_id": m.idea_id, "created_at": iso(m.created_at)}
