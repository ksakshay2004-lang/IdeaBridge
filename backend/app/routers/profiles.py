from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import CreatorProfile, EntrepreneurProfile, User
from ..schemas import CreatorProfileIn, EntrepreneurProfileIn
from ..services import vectors
from ..services.serializers import user_out
from ..embedding_guard import safe_embed

router = APIRouter(tags=["profiles"])


def creator_profile_out(u: User) -> dict:
    p = u.creator_profile
    return {"headline": p.headline, "bio": p.bio, "organization": p.organization, "location": p.location,
            "website": p.website, "skills": p.skills or []} if p else {}


def entrepreneur_profile_out(u: User, private: bool = True) -> dict:
    p = u.entrepreneur_profile
    if not p:
        return {}
    out = {"company_name": p.company_name, "company_type": p.company_type, "bio": p.bio, "website": p.website,
           "location": p.location, "industries": p.industries or [], "technologies": p.technologies or [],
           "interests": p.interests, "preferred_stages": p.preferred_stages or [],
           "target_markets": p.target_markets or [], "investment_min": p.investment_min,
           "investment_max": p.investment_max}
    return out


@router.get("/profile/me")
def get_my_profile(user: User = Depends(get_current_user)):
    prof = creator_profile_out(user) if user.role == "creator" else \
        entrepreneur_profile_out(user) if user.role == "entrepreneur" else {}
    return {"user": user_out(user), "profile": prof}


@router.put("/profile/me/creator")
def update_creator(body: CreatorProfileIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "creator":
        raise HTTPException(403, "Only idea creators have a creator profile")
    p = user.creator_profile or CreatorProfile(user_id=user.id)
    for k, v in body.model_dump(exclude={"full_name"}).items():
        setattr(p, k, v)
    if body.full_name:
        user.full_name = " ".join(body.full_name.split())
    db.add(p)
    db.commit()
    db.refresh(user)
    return get_my_profile(user)


@router.put("/profile/me/entrepreneur")
def update_entrepreneur(body: EntrepreneurProfileIn, user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    if user.role != "entrepreneur":
        raise HTTPException(403, "Only entrepreneurs have a company profile")
    p = user.entrepreneur_profile or EntrepreneurProfile(user_id=user.id)
    for k, v in body.model_dump(exclude={"full_name"}).items():
        setattr(p, k, v)
    if body.full_name:
        user.full_name = " ".join(body.full_name.split())
    safe_embed(lambda: vectors.refresh_profile_embedding(db, p))
    db.add(p)
    db.commit()
    db.refresh(user)
    return get_my_profile(user)


@router.get("/entrepreneurs/{user_id}")
def public_entrepreneur(user_id: int, viewer: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Public company card (no private fields). Visible to signed-in users."""
    u = db.get(User, user_id)
    if not u or u.role != "entrepreneur" or not u.is_active:
        raise HTTPException(404, "Not found")
    p = entrepreneur_profile_out(u)
    return {"id": u.id, "name": u.full_name, "is_verified": u.is_verified, "company_name": p.get("company_name"),
            "company_type": p.get("company_type"), "bio": p.get("bio"), "website": p.get("website"),
            "location": p.get("location"), "industries": p.get("industries"), "technologies": p.get("technologies"),
            "preferred_stages": p.get("preferred_stages")}
