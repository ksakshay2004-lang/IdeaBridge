from typing import Optional

from sqlalchemy.orm import Session

from ..models import AdminActivityLog, Notification, User


def notify(db: Session, user_id: int, kind: str, title: str, body: str = "", link: Optional[str] = None) -> None:
    """Queue a notification; the caller commits."""
    db.add(Notification(user_id=user_id, kind=kind, title=title[:200], body=body[:500], link=link))


def log_admin(db: Session, admin: User, action: str, target_type: str, target_id: Optional[int], detail: str = "") -> None:
    db.add(AdminActivityLog(admin_id=admin.id, action=action, target_type=target_type, target_id=target_id,
                            detail=detail[:400]))
