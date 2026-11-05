from typing import Optional

from sqlalchemy.orm import Session

from ai_engine import match_idea_to_profile

from ..models import EntrepreneurProfile, Idea
from . import vectors


def profile_dict(p: EntrepreneurProfile) -> dict:
    return {"industries": p.industries, "technologies": p.technologies, "interests": p.interests,
            "preferred_stages": p.preferred_stages, "target_markets": p.target_markets,
            "investment_min": p.investment_min, "investment_max": p.investment_max}


def idea_dict(i: Idea) -> dict:
    return {"industry": i.industry, "technologies": i.technologies, "title": i.title,
            "short_description": i.short_description, "problem": i.problem, "solution": i.solution,
            "target_audience": i.target_audience, "stage": i.stage, "funding_needed": i.funding_needed}


def score_match(idea: Idea, profile: EntrepreneurProfile) -> dict:
    emb = vectors.embedder()
    same_model = (idea.embedding is not None and profile.embedding is not None
                  and idea.embedding_model == emb.model and profile.embedding_model == emb.model)
    return match_idea_to_profile(idea_dict(idea), profile_dict(profile),
                                 idea.embedding if same_model else None,
                                 profile.embedding if same_model else None, emb.sim_floor, emb.sim_ceiling)
