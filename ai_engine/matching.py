"""Idea <-> entrepreneur matching with an explainable score (0-100)."""
from __future__ import annotations

import re
from typing import Dict, List, Optional

from .similarity import cosine

STAGES = ["concept", "research", "prototype", "mvp", "launched"]
WEIGHTS = {"industry": 25, "technology": 20, "interests": 15, "stage": 15, "market": 10, "investment": 15}


def _norm(items) -> set:
    return {str(i).strip().lower() for i in (items or []) if str(i).strip()}


def _tokens(s: str) -> set:
    return {t for t in re.findall(r"[a-z0-9]+", (s or "").lower()) if len(t) > 3}


def match_idea_to_profile(idea: Dict, profile: Dict, idea_vec: Optional[List[float]] = None,
                          profile_vec: Optional[List[float]] = None, floor: float = 0.1,
                          ceiling: float = 0.45) -> Dict:
    """idea/profile are plain dicts. Returns {score, breakdown:{dim:{score,max,reason}}, reasons:[...]}."""
    parts: Dict[str, Dict] = {}

    def put(dim: str, frac: float, reason: str):
        frac = max(0.0, min(1.0, frac))
        parts[dim] = {"score": round(frac * WEIGHTS[dim], 1), "max": WEIGHTS[dim], "reason": reason}

    p_ind = _norm(profile.get("industries"))
    if not p_ind:
        put("industry", 0.4, "No industry focus set on the entrepreneur profile (neutral).")
    elif str(idea.get("industry", "")).lower() in p_ind:
        put("industry", 1.0, f"Idea industry '{idea.get('industry')}' is one of their focus industries.")
    else:
        put("industry", 0.0, f"Idea industry '{idea.get('industry')}' is outside their stated focus.")

    i_tech, p_tech = _norm(idea.get("technologies")), _norm(profile.get("technologies"))
    if not p_tech or not i_tech:
        put("technology", 0.4, "Technology preferences or idea technologies not specified (neutral).")
    else:
        shared = sorted(i_tech & p_tech)
        put("technology", len(shared) / min(len(i_tech), 3) if shared else 0.0,
            ("Shared technologies: " + ", ".join(shared)) if shared else "No overlapping technologies.")

    if idea_vec is not None and profile_vec is not None:
        rel = max(0.0, min(1.0, (cosine(idea_vec, profile_vec) - floor) / max(ceiling - floor, 1e-6)))
        put("interests", rel, f"Text similarity between idea and stated interests ~{rel * 100:.0f}% of the scale.")
    else:
        ov = _tokens(profile.get("interests", "")) & _tokens(
            " ".join(str(idea.get(k, "")) for k in ("title", "short_description", "problem", "solution")))
        put("interests", min(1.0, len(ov) / 3), ("Interest keywords found in the idea: " + ", ".join(sorted(ov)))
            if ov else "No stated interest keywords found in the idea text.")

    p_st = [s for s in (profile.get("preferred_stages") or []) if s in STAGES]
    st = str(idea.get("stage", "")).lower()
    if not p_st:
        put("stage", 0.5, "No preferred project stages set (neutral).")
    elif st in p_st:
        put("stage", 1.0, f"Project stage '{st}' matches their preferred stages.")
    elif st in STAGES and min(abs(STAGES.index(st) - STAGES.index(s)) for s in p_st) == 1:
        put("stage", 0.5, f"Project stage '{st}' is adjacent to a preferred stage.")
    else:
        put("stage", 0.0, f"Project stage '{st}' is outside their preferred stages.")

    markets = _norm(profile.get("target_markets"))
    if not markets:
        put("market", 0.5, "No target markets set (neutral).")
    else:
        aud = " ".join(str(idea.get(k, "")) for k in ("target_audience", "title", "short_description")).lower()
        hit = sorted(m for m in markets if m in aud)
        put("market", 1.0 if hit else 0.0, ("Target market overlap: " + ", ".join(hit)) if hit
            else "Idea audience does not mention their target markets.")

    need, lo, hi = idea.get("funding_needed"), profile.get("investment_min"), profile.get("investment_max")
    if not need or (lo is None and hi is None):
        put("investment", 0.5, "Funding sought or investment range not specified (neutral).")
    else:
        lo, hi = lo or 0, hi or float("inf")
        if lo <= need <= hi:
            put("investment", 1.0, f"Funding sought (${need:,}) is within their investment range.")
        elif need < lo * 1.0 and need >= lo * 0.5 or (hi != float("inf") and hi < need <= hi * 2):
            put("investment", 0.5, f"Funding sought (${need:,}) is close to their investment range.")
        else:
            put("investment", 0.0, f"Funding sought (${need:,}) is outside their investment range.")

    score = round(sum(p["score"] for p in parts.values()))
    reasons = [p["reason"] for p in sorted(parts.values(), key=lambda p: -p["score"]) if p["score"] > 0][:4]
    return {"score": score, "breakdown": parts, "reasons": reasons or ["Little overlap with the stated preferences."]}
