from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_admin
from ..models import (AdminActivityLog, Category, CollaborationRequest, ContentReport, Evaluation, Idea, Message,
                      ReferenceProject, User)
from ..schemas import AdminIdeaUpdate, AdminReportResolve, AdminUserUpdate, CategoryIn, CategoryUpdate
from ..services import vectors
from ..services.files import delete_stored
from ..services.notifications import log_admin, notify
from ..services.serializers import iso, user_brief, user_out

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/analytics")
def analytics(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    def count(model, *conds):
        return db.scalar(select(func.count()).select_from(model).where(*conds)) or 0

    days = 14
    start = (datetime.now(timezone.utc) - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
    labels = [(start + timedelta(days=i)).date().isoformat() for i in range(days)]

    def series(model):
        c = Counter(r.date().isoformat() for r in db.scalars(select(model.created_at).where(model.created_at >= start)))
        return [c.get(d, 0) for d in labels]

    by_industry = db.execute(select(Idea.industry, func.count()).group_by(Idea.industry)
                             .order_by(func.count().desc()).limit(12)).all()
    avg = db.execute(select(func.avg(Evaluation.technical_score), func.avg(Evaluation.market_score),
                            func.avg(Evaluation.innovation_score)).where(Evaluation.status == "completed")).one()
    return {
        "totals": {"users": count(User), "creators": count(User, User.role == "creator"),
                   "entrepreneurs": count(User, User.role == "entrepreneur"),
                   "unverified_entrepreneurs": count(User, User.role == "entrepreneur", User.is_verified.is_(False)),
                   "ideas": count(Idea), "evaluations": count(Evaluation, Evaluation.status == "completed"),
                   "evaluations_demo": count(Evaluation, Evaluation.mode == "demo"),
                   "evaluations_live": count(Evaluation, Evaluation.mode == "live_llm"),
                   "collab_requests": count(CollaborationRequest), "messages": count(Message),
                   "open_reports": count(ContentReport, ContentReport.status == "open"),
                   "reference_projects": count(ReferenceProject)},
        "growth": {"labels": labels, "users": series(User), "ideas": series(Idea)},
        "ideas_by_industry": [{"industry": i, "count": c} for i, c in by_industry],
        "ideas_by_visibility": [{"visibility": v, "count": c} for v, c in
                                db.execute(select(Idea.visibility, func.count()).group_by(Idea.visibility)).all()],
        "collab_by_status": [{"status": s, "count": c} for s, c in db.execute(
            select(CollaborationRequest.status, func.count()).group_by(CollaborationRequest.status)).all()],
        "avg_scores": {"technical": round(avg[0] or 0), "market": round(avg[1] or 0), "innovation": round(avg[2] or 0)},
    }


@router.get("/users")
def users(q: Optional[str] = None, role: Optional[str] = None, page: int = Query(1, ge=1),
          admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    conds = []
    if q:
        like = f"%{q.lower()}%"
        conds.append(func.lower(User.email).like(like) | func.lower(User.full_name).like(like))
    if role:
        conds.append(User.role == role)
    total = db.scalar(select(func.count()).select_from(User).where(*conds)) or 0
    rows = db.scalars(select(User).where(*conds).order_by(User.created_at.desc()).offset((page - 1) * 25).limit(25))
    out = []
    for u in rows:
        d = user_out(u)
        d["company_name"] = u.entrepreneur_profile.company_name if u.entrepreneur_profile else None
        d["idea_count"] = len(u.ideas) if u.role == "creator" else None
        out.append(d)
    return {"items": out, "total": total, "page": page}


@router.patch("/users/{user_id}")
def update_user(user_id: int, body: AdminUserUpdate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "User not found")
    if u.id == admin.id and body.is_active is False:
        raise HTTPException(400, "You cannot deactivate your own account")
    if body.is_active is not None:
        u.is_active = body.is_active
        log_admin(db, admin, "user_activate" if body.is_active else "user_deactivate", "user", u.id, u.email)
    if body.is_verified is not None:
        if u.role != "entrepreneur":
            raise HTTPException(400, "Only entrepreneur profiles can be verified")
        u.is_verified = body.is_verified
        log_admin(db, admin, "user_verify" if body.is_verified else "user_unverify", "user", u.id, u.email)
        if body.is_verified:
            notify(db, u.id, "verified", "Your profile has been verified", "Creators will now see a verified badge.",
                   "/app/entrepreneur/profile")
    db.commit()
    return user_out(u)


@router.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "User not found")
    if u.id == admin.id or u.role == "admin":
        raise HTTPException(400, "Administrator accounts cannot be deleted here")
    for idea in u.ideas:
        for d in idea.documents:
            delete_stored(d.stored_name)
    log_admin(db, admin, "user_delete", "user", u.id, u.email)
    db.delete(u)
    db.commit()


@router.get("/ideas")
def ideas(q: Optional[str] = None, status: Optional[str] = None, page: int = Query(1, ge=1),
          admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    conds = []
    if q:
        conds.append(func.lower(Idea.title).like(f"%{q.lower()}%"))
    if status:
        conds.append(Idea.moderation_status == status)
    total = db.scalar(select(func.count()).select_from(Idea).where(*conds)) or 0
    rows = db.scalars(select(Idea).where(*conds).order_by(Idea.created_at.desc()).offset((page - 1) * 25).limit(25))
    return {"items": [{"id": i.id, "title": i.title, "industry": i.industry, "visibility": i.visibility,
                       "moderation_status": i.moderation_status, "stage": i.stage, "created_at": iso(i.created_at),
                       "creator": user_brief(i.creator),
                       "overall_score": next((e.overall_score for e in i.evaluations if e.status == "completed"), None),
                       "open_reports": sum(1 for r in db.scalars(select(ContentReport).where(
                           ContentReport.idea_id == i.id, ContentReport.status == "open")))} for i in rows],
            "total": total, "page": page}


@router.patch("/ideas/{idea_id}")
def moderate_idea(idea_id: int, body: AdminIdeaUpdate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    idea = db.get(Idea, idea_id)
    if not idea:
        raise HTTPException(404, "Idea not found")
    idea.moderation_status = body.moderation_status
    log_admin(db, admin, f"idea_{body.moderation_status}", "idea", idea.id, body.note or idea.title)
    if body.moderation_status != "active":
        notify(db, idea.creator_id, "moderation", f"Your idea was set to '{body.moderation_status}'",
               body.note or idea.title, f"/app/creator/ideas/{idea.id}")
    db.commit()
    return {"id": idea.id, "moderation_status": idea.moderation_status}


@router.delete("/ideas/{idea_id}", status_code=204)
def delete_idea(idea_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    idea = db.get(Idea, idea_id)
    if not idea:
        raise HTTPException(404, "Idea not found")
    for d in idea.documents:
        delete_stored(d.stored_name)
    log_admin(db, admin, "idea_delete", "idea", idea.id, idea.title)
    db.delete(idea)
    db.commit()


@router.get("/reports")
def reports(status: Optional[str] = "open", admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    q = select(ContentReport).order_by(ContentReport.created_at.desc()).limit(200)
    if status:
        q = q.where(ContentReport.status == status)
    return [{"id": r.id, "reason": r.reason, "details": r.details, "status": r.status, "created_at": iso(r.created_at),
             "resolution_note": r.resolution_note, "reporter": user_brief(r.reporter),
             "idea": {"id": r.idea.id, "title": r.idea.title, "moderation_status": r.idea.moderation_status,
                      "short_description": r.idea.short_description, "creator": user_brief(r.idea.creator)}}
            for r in db.scalars(q)]


@router.post("/reports/{report_id}/resolve")
def resolve_report(report_id: int, body: AdminReportResolve, admin: User = Depends(require_admin),
                   db: Session = Depends(get_db)):
    r = db.get(ContentReport, report_id)
    if not r:
        raise HTTPException(404, "Report not found")
    if r.status != "open":
        raise HTTPException(409, "Report already resolved")
    r.resolved_by, r.resolution_note = admin.id, body.note
    if body.action == "dismiss":
        r.status = "dismissed"
    else:
        r.status = "actioned"
        r.idea.moderation_status = "hidden" if body.action == "hide_idea" else "removed"
        notify(db, r.idea.creator_id, "moderation", f"Your idea was set to '{r.idea.moderation_status}'",
               body.note or "Following a content report.", f"/app/creator/ideas/{r.idea.id}")
    log_admin(db, admin, f"report_{body.action}", "report", r.id, body.note or r.reason)
    db.commit()
    return {"id": r.id, "status": r.status}


@router.get("/categories")
def categories(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    used = dict(db.execute(select(Idea.industry, func.count()).group_by(Idea.industry)).all())
    return [{"id": c.id, "name": c.name, "kind": c.kind, "description": c.description, "is_active": c.is_active,
             "idea_count": used.get(c.name, 0) if c.kind == "industry" else None}
            for c in db.scalars(select(Category).order_by(Category.kind, Category.name))]


@router.post("/categories", status_code=201)
def create_category(body: CategoryIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    if db.scalar(select(Category.id).where(func.lower(Category.name) == body.name.lower(), Category.kind == body.kind)):
        raise HTTPException(409, "Category already exists")
    c = Category(**body.model_dump())
    db.add(c)
    log_admin(db, admin, "category_create", "category", None, f"{body.kind}: {body.name}")
    db.commit()
    return {"id": c.id, "name": c.name, "kind": c.kind, "description": c.description, "is_active": c.is_active}


@router.patch("/categories/{category_id}")
def update_category(category_id: int, body: CategoryUpdate, admin: User = Depends(require_admin),
                    db: Session = Depends(get_db)):
    c = db.get(Category, category_id)
    if not c:
        raise HTTPException(404, "Category not found")
    changes = body.model_dump(exclude_unset=True)
    if "name" in changes and changes["name"] != c.name:
        if db.scalar(select(Category.id).where(func.lower(Category.name) == changes["name"].lower(),
                                               Category.kind == c.kind, Category.id != c.id)):
            raise HTTPException(409, "Category name already exists")
        if c.kind == "industry":  # keep existing ideas consistent
            for idea in db.scalars(select(Idea).where(Idea.industry == c.name)):
                idea.industry = changes["name"]
    for k, v in changes.items():
        setattr(c, k, v)
    log_admin(db, admin, "category_update", "category", c.id, c.name)
    db.commit()
    return {"id": c.id, "name": c.name, "kind": c.kind, "description": c.description, "is_active": c.is_active}


@router.delete("/categories/{category_id}", status_code=204)
def delete_category(category_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    c = db.get(Category, category_id)
    if not c:
        raise HTTPException(404, "Category not found")
    if c.kind == "industry" and db.scalar(select(func.count()).select_from(Idea).where(Idea.industry == c.name)):
        raise HTTPException(409, "Category is used by existing ideas; deactivate it instead")
    log_admin(db, admin, "category_delete", "category", c.id, c.name)
    db.delete(c)
    db.commit()


@router.get("/logs")
def logs(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.scalars(select(AdminActivityLog).order_by(AdminActivityLog.created_at.desc()).limit(100))
    names = {u.id: u.full_name for u in db.scalars(select(User).where(User.role == "admin"))}
    return [{"id": l.id, "admin": names.get(l.admin_id, "—"), "action": l.action, "target_type": l.target_type,
             "target_id": l.target_id, "detail": l.detail, "created_at": iso(l.created_at)} for l in rows]


@router.post("/reindex")
def reindex(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Re-embed reference projects, ideas and entrepreneur profiles with the configured embedding model."""
    from ..models import EntrepreneurProfile
    n_ref = vectors.ensure_reference_projects(db)
    n_ideas = n_prof = 0
    for idea in db.scalars(select(Idea)):
        vectors.refresh_idea_embedding(db, idea)
        n_ideas += 1
    for p in db.scalars(select(EntrepreneurProfile)):
        vectors.refresh_profile_embedding(db, p)
        n_prof += 1
    log_admin(db, admin, "reindex", "system", None, f"refs={n_ref} ideas={n_ideas} profiles={n_prof}")
    db.commit()
    return {"reference_projects": n_ref, "ideas": n_ideas, "profiles": n_prof, "embedding": vectors.embedder().describe()}
