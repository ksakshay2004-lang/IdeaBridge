from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import CreatorProfile, EntrepreneurProfile, User
from ..schemas import ChangePasswordIn, LoginIn, RegisterIn
from ..security import create_access_token, hash_password, login_throttle, verify_password
from ..services.serializers import user_out

router = APIRouter(prefix="/auth", tags=["auth"])


def _login(db: Session, email: str, password: str, request: Request) -> dict:
    email = email.lower().strip()
    key = f"{email}|{request.client.host if request.client else '?'}"
    if login_throttle.blocked(key):
        raise HTTPException(429, "Too many failed attempts. Try again in a few minutes.")
    user = db.scalar(select(User).where(func.lower(User.email) == email))
    if not user or not verify_password(password, user.password_hash):
        login_throttle.fail(key)
        raise HTTPException(401, "Incorrect email or password")
    if not user.is_active:
        raise HTTPException(403, "This account has been deactivated")
    login_throttle.reset(key)
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    return {"access_token": create_access_token(user.id, user.role), "token_type": "bearer", "user": user_out(user)}


@router.post("/register", status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.scalar(select(User.id).where(func.lower(User.email) == email)):
        raise HTTPException(409, "An account with this email already exists")
    user = User(email=email, password_hash=hash_password(body.password), full_name=body.full_name, role=body.role)
    db.add(user)
    db.flush()
    if body.role == "creator":
        db.add(CreatorProfile(user_id=user.id))
    else:
        db.add(EntrepreneurProfile(user_id=user.id, company_name=(body.company_name or "").strip()))
    db.commit()
    return {"access_token": create_access_token(user.id, user.role), "token_type": "bearer", "user": user_out(user)}


@router.post("/login")
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)):
    return _login(db, body.email, body.password, request)


@router.post("/token", include_in_schema=True)
def token(request: Request, form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """OAuth2 password-flow endpoint (used by the Swagger 'Authorize' button)."""
    return _login(db, form.username, form.password, request)


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return user_out(user)


@router.post("/change-password")
def change_password(body: ChangePasswordIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(400, "Current password is incorrect")
    user.password_hash = hash_password(body.new_password)
    db.commit()
    return {"ok": True}
