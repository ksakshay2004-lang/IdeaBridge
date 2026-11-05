"""Turn ORM objects into JSON-safe dicts, enforcing idea privacy (teaser vs full)."""
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import CollaborationRequest, Evaluation, Idea, SavedIdea, User
from ..permissions import idea_access

WITHHELD = "Another idea on IdeaBridge (details withheld)"


def iso(dt):
    return dt.isoformat() if dt else None


def user_brief(u: User) -> dict:
    headline = ""
    if u.creator_profile:
        headline = u.creator_profile.headline
    elif u.entrepreneur_profile:
        headline = u.entrepreneur_profile.company_name
    return {"id": u.id, "name": u.full_name, "role": u.role, "headline": headline, "is_verified": u.is_verified}


def user_out(u: User) -> dict:
    return {"id": u.id, "email": u.email, "full_name": u.full_name, "role": u.role, "is_active": u.is_active,
            "is_verified": u.is_verified, "created_at": iso(u.created_at), "last_login_at": iso(u.last_login_at)}


def latest_completed(db: Session, idea_ids: List[int]) -> Dict[int, Evaluation]:
    if not idea_ids:
        return {}
    rows = db.scalars(select(Evaluation).where(Evaluation.idea_id.in_(idea_ids), Evaluation.status == "completed")
                      .order_by(Evaluation.version.desc()))
    out: Dict[int, Evaluation] = {}
    for ev in rows:
        out.setdefault(ev.idea_id, ev)
    return out


def scores_of(ev: Optional[Evaluation]) -> Optional[dict]:
    if ev is None:
        return None
    return {"technical_feasibility": ev.technical_score, "market_opportunity": ev.market_score,
            "innovation_differentiation": ev.innovation_score, "overall": ev.overall_score,
            "mode": ev.mode, "evaluated_at": iso(ev.completed_at)}


def idea_cards(db: Session, ideas: List[Idea], user: Optional[User], extra: Optional[Dict[int, dict]] = None) -> List[dict]:
    """List representation. Never contains problem/solution text; scores only if public or fully accessible."""
    ids = [i.id for i in ideas]
    evs = latest_completed(db, ids)
    saved, mine = set(), {}
    if user is not None and ids:
        saved = set(db.scalars(select(SavedIdea.idea_id).where(SavedIdea.user_id == user.id, SavedIdea.idea_id.in_(ids))))
        if user.role == "entrepreneur":
            for r in db.scalars(select(CollaborationRequest).where(CollaborationRequest.entrepreneur_id == user.id,
                                                                  CollaborationRequest.idea_id.in_(ids))
                                .order_by(CollaborationRequest.created_at)):
                mine[r.idea_id] = {"id": r.id, "status": r.status}
    out = []
    for idea in ideas:
        access = idea_access(db, user, idea)
        owner_view = user is not None and (user.id == idea.creator_id or user.role == "admin")
        show_scores = access == "full" or idea.visibility == "public"
        card = {
            "id": idea.id, "title": idea.title, "short_description": idea.short_description,
            "industry": idea.industry, "technologies": idea.technologies or [], "stage": idea.stage,
            "visibility": idea.visibility, "created_at": iso(idea.created_at), "updated_at": iso(idea.updated_at),
            "access": access, "creator": user_brief(idea.creator),
            "scores": scores_of(evs.get(idea.id)) if show_scores else None,
            "is_saved": idea.id in saved, "my_request": mine.get(idea.id),
            "funding_needed": idea.funding_needed if access == "full" else None,
        }
        if owner_view:
            card["moderation_status"] = idea.moderation_status
        if extra and idea.id in extra:
            card.update(extra[idea.id])
        out.append(card)
    return out


def idea_detail(db: Session, idea: Idea, user: Optional[User], access: str) -> dict:
    card = idea_cards(db, [idea], user)[0]
    if access != "full":
        return card
    card.update({
        "problem": idea.problem, "solution": idea.solution, "target_audience": idea.target_audience,
        "expected_impact": idea.expected_impact, "business_potential": idea.business_potential,
        "documents": [{"id": d.id, "filename": d.filename, "size": d.size, "content_type": d.content_type,
                       "uploaded_at": iso(d.uploaded_at)} for d in idea.documents],
    })
    owner_view = user is not None and (user.id == idea.creator_id or user.role == "admin")
    if owner_view:
        latest = idea.evaluations[0] if idea.evaluations else None
        card["latest_evaluation"] = {"id": latest.id, "status": latest.status, "stage": latest.stage,
                                     "progress": latest.progress} if latest else None
    else:
        card["target_audience"] = idea.target_audience
    return card


def evaluation_out(db: Session, ev: Evaluation, with_report: bool = True) -> dict:
    out = {"id": ev.id, "idea_id": ev.idea_id, "version": ev.version, "status": ev.status, "stage": ev.stage,
           "progress": ev.progress, "mode": ev.mode, "provider": ev.provider, "model": ev.model, "error": ev.error,
           "created_at": iso(ev.created_at), "completed_at": iso(ev.completed_at),
           "outdated": bool(ev.completed_at and ev.idea and ev.idea.updated_at
                            and _aware(ev.idea.updated_at) > _aware(ev.completed_at)),
           "scores": scores_of(ev)}
    if with_report and ev.status == "completed" and ev.report:
        report = dict(ev.report)
        similar = []
        for r in ev.similar:  # privacy re-checked at read time (visibility may have changed since the run)
            title, url, diff = r.title, r.url, r.differences
            if r.source_type == "platform":
                other = db.get(Idea, int(r.source_ref)) if r.source_ref.isdigit() else None
                if not (other and other.visibility == "public" and other.moderation_status == "active"):
                    title, url, diff = WITHHELD, None, ""
                else:
                    title = other.title
            similar.append({"ref_id": r.source_ref, "kind": r.source_type, "title": title, "url": url,
                            "similarity_pct": r.similarity, "key_differences": diff,
                            "is_competitor": r.is_competitor})
        report["similar_projects"] = similar
        out["report"] = report
    return out


def _aware(dt):
    from datetime import timezone
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
