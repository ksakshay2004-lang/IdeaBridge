from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Message, Notification, User
from ..services.serializers import iso

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
def list_notifications(limit: int = 50, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Notification).where(Notification.user_id == user.id)
                      .order_by(Notification.created_at.desc()).limit(max(1, min(limit, 200))))
    return [{"id": n.id, "kind": n.kind, "title": n.title, "body": n.body, "link": n.link, "is_read": n.is_read,
             "created_at": iso(n.created_at)} for n in rows]


@router.get("/unread-count")
def unread_count(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    n = db.scalar(select(func.count()).select_from(Notification).where(Notification.user_id == user.id,
                                                                       Notification.is_read.is_(False)))
    m = db.scalar(select(func.count()).select_from(Message).where(Message.recipient_id == user.id,
                                                                  Message.read_at.is_(None)))
    return {"notifications": n or 0, "messages": m or 0}


@router.post("/read-all")
def read_all(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.execute(update(Notification).where(Notification.user_id == user.id, Notification.is_read.is_(False))
               .values(is_read=True))
    db.commit()
    return {"ok": True}


@router.post("/{notification_id}/read")
def read_one(notification_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    n = db.get(Notification, notification_id)
    if not n or n.user_id != user.id:
        raise HTTPException(404, "Notification not found")
    n.is_read = True
    db.commit()
    return {"ok": True}
