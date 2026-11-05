from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from .security import decode_token

oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)


def get_optional_user(token: Optional[str] = Depends(oauth2), db: Session = Depends(get_db)) -> Optional[User]:
    if not token:
        return None
    uid = decode_token(token)
    user = db.get(User, uid) if uid else None
    return user if user and user.is_active else None


def get_current_user(user: Optional[User] = Depends(get_optional_user)) -> User:
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated",
                            headers={"WWW-Authenticate": "Bearer"})
    return user


def require_roles(*roles: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have permission to do that")
        return user
    return checker


require_creator = require_roles("creator")
require_entrepreneur = require_roles("entrepreneur")
require_admin = require_roles("admin")
