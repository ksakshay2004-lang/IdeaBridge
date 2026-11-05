"""LOCAL RULE-BASED EVALUATION ("DEMO MODE").

This is NOT an AI model. It applies transparent keyword/length heuristics plus the real
vector-similarity numbers. Scores are rough indicators for demonstration only.
"""
from __future__ import annotations

import re
from typing import Dict, List

HARD_TERMS = ["blockchain", "quantum", "self-driving", "autonomous vehicle", "agi", "fusion", "brain-computer",
              "satellite", "biotech", "drug discovery", "genome", "genomic", "robot", "hardware", "drone",
              "semiconductor", "medical device", "5g", "ar/vr", "augmented reality", "virtual reality", "lidar"]
EASY_TERMS = ["web app", "website", "mobile app", "dashboard", "api", "saas", "chatbot", "marketplace", "portal",
              "crm", "notification", "analytics", "recommendation", "automation", "scheduling"]
REVENUE_TERMS = {"subscription": "Subscription / SaaS", "license": "Licensing", "licence": "Licensing",
                 "commission": "Transaction commission", "freemium": "Freemium with paid tiers",
                 "advertis": "Advertising", "b2b": "B2B contracts", "enterprise": "Enterprise plans",
                 "consult": "Consulting / services", "marketplace": "Marketplace fees", "hardware": "Hardware sales",
                 "grant": "Grants / sponsorship", "data": "Data / insights products"}
INDUSTRY_MARKET = {"healthcare": 72, "fintech": 72, "ai / machine learning": 70, "ai": 70, "cleantech": 66,
                   "e-commerce": 66, "edtech": 62, "agritech": 60, "logistics": 62, "cybersecurity": 70,
                   "iot": 62, "social impact": 52, "entertainment": 55, "real estate": 58}
STAGE_BONUS = {"concept": 0, "research": 2, "prototype": 6, "mvp": 9, "launched": 12}
INDUSTRY_REVENUE = {"healthcare": ["B2B contracts with providers", "Subscription / SaaS"],
                    "fintech": ["Transaction commission", "Subscription / SaaS"],
                    "edtech": ["Freemium with paid tiers", "Institutional licensing"],
                    "agritech": ["Subscription / SaaS", "Cooperative / B2B contracts"]}


def _words(s: str) -> int:
    return len(re.findall(r"\w+", s or ""))


def _hits(text: str, terms: List[str]) -> int:
    t = text.lower()
    return sum(1 for term in terms if term in t)


def _split_list(s: str) -> List[str]:
    parts = [p.strip(" .") for p in re.split(r",|;|\band\b|/", s or "") if p.strip(" .")]
    return [p[:80] for p in parts][:6]


def _first_sentences(text: str, n: int = 2, limit: int = 420) -> str:
    sents = re.split(r"(?<=[.!?])\s+", (text or "").strip())
    return " ".join(sents[:n])[:limit]


def demo_evaluate(idea: Dict, retrieved: List, floor: float, ceiling: float, corpus: Dict) -> Dict:
    text = " ".join(str(idea.get(k, "")) for k in
                    ("title", "short_description", "problem", "solution", "business_potential")) \
        + " " + " ".join(idea.get("technologies") or [])
    tech = 68
    tech -= min(32, 8 * _hits(text, HARD_TERMS))
    tech += min(12, 4 * _hits(text, EASY_TERMS))
    tech += STAGE_BONUS.get(str(idea.get("stage", "")).lower(), 0)
    if _words(idea.get("solution", "")) >= 60:
        tech += 4
    tech = max(5, min(95, tech))

    industry = str(idea.get("industry", "")).lower()
    market = INDUSTRY_MARKET.get(industry, 55)
    market += min(9, 3 * _hits(str(idea.get("business_potential", "")), list(REVENUE_TERMS)))
    if _words(idea.get("target_audience", "")) >= 4:
        market += 3
    if _words(idea.get("business_potential", "")) >= 30:
        market += 3
    if idea.get("funding_needed"):
        market += 1
    market = max(5, min(95, market))

    sims = [r.similarity for r in retrieved]
    max_sim = max(sims) if sims else 0.0
    over = min(1.0, max(0.0, max_sim - floor) / max(1e-6, ceiling - floor))
    innov = max(5, min(95, round(100 - over * 90)))

    complexity = "high" if tech < 45 else "moderate" if tech < 70 else "low"
    novelty = "high" if innov >= 75 else "moderate" if innov >= 45 else "low"

    strengths, weaknesses, risks, recs = [], [], [], []
    if innov >= 70:
        strengths.append("Little vocabulary overlap with the projects and ideas in the comparison set.")
    if _hits(text, EASY_TERMS):
        strengths.append("Relies on well-understood product patterns (web/mobile/API), which lowers build risk.")
    if idea.get("stage", "concept") in ("prototype", "mvp", "launched"):
        strengths.append(f"Already at the '{idea.get('stage')}' stage, which shows execution progress.")
    if _words(idea.get("target_audience", "")) >= 4:
        strengths.append("Target audience is described in some detail.")
    if not strengths:
        strengths.append("Clear enough problem/solution framing to be assessed.")
    if _words(idea.get("problem", "")) < 40:
        weaknesses.append("Problem statement is short; quantify who is affected and how badly.")
        recs.append("Expand the problem statement with a concrete user story and an estimate of how many people face it.")
    if _words(idea.get("solution", "")) < 60:
        weaknesses.append("Solution description is brief; the core mechanism is not fully specified.")
        recs.append("Describe the core mechanism step by step and what is technically new about it.")
    if not str(idea.get("business_potential", "")).strip():
        weaknesses.append("No business model or monetisation described.")
        recs.append("Add a first revenue hypothesis (who pays, for what, how much).")
    if max_sim > floor + 0.15:
        weaknesses.append("Noticeable overlap with at least one comparison item (see similar projects).")
        recs.append("State explicitly how your approach differs from the most similar items listed.")
    if _hits(text, HARD_TERMS):
        risks.append("Involves technically demanding areas (e.g. hardware, regulated or frontier technology).")
        recs.append("Scope a thin vertical slice or proof-of-concept to retire the biggest technical risk first.")
    if industry in ("healthcare", "fintech"):
        risks.append("Regulated sector: compliance, privacy and data-protection requirements are likely.")
    risks.append("Demand is unvalidated by this tool; talk to potential users before investing heavily.")
    risks.append("Novelty is judged only against a limited comparison set, not the entire market.")
    recs.append("Run 5-10 interviews with the target audience and record what they currently use instead.")
    if not idea.get("technologies"):
        recs.append("List the key technologies/stack so feasibility can be assessed more precisely.")

    revenue = []
    for kw, label in REVENUE_TERMS.items():
        if kw in str(idea.get("business_potential", "")).lower() and label not in revenue:
            revenue.append(label)
    for label in INDUSTRY_REVENUE.get(industry, []):
        if label not in revenue:
            revenue.append(label)
    if not revenue:
        revenue = ["Subscription / SaaS", "Freemium with paid tiers"]

    users = _split_list(idea.get("target_audience", "")) or ["Not specified"]
    comp = [r for r in retrieved if r.visible and r.kind == "reference" and r.similarity >= floor + 0.08][:4]

    overall_scores = round(0.35 * tech + 0.35 * market + 0.30 * innov)
    overall = (f"Rule-based assessment: technical feasibility {tech}/100, market opportunity {market}/100, "
               f"differentiation {innov}/100 (overall {overall_scores}/100). Compared against "
               f"{corpus.get('reference_count', 0)} curated projects and {corpus.get('platform_count', 0)} "
               f"platform ideas only; this is a heuristic screen, not market research.")
    return {
        "idea_summary": _first_sentences(idea.get("short_description", "")) or str(idea.get("title", "")),
        "problem_statement": _first_sentences(idea.get("problem", ""), 3, 600),
        "proposed_solution": _first_sentences(idea.get("solution", ""), 3, 600),
        "similar_project_notes": {},
        "novelty_assessment": {"level": novelty, "rationale": (
            f"Highest similarity to any comparison item is {max_sim * 100:.1f}% "
            f"({'lexical word-overlap' if corpus.get('embedding_kind') == 'lexical' else 'semantic'} measure). "
            "Higher similarity means lower measured novelty within the comparison set.")},
        "scores": {"technical_feasibility": tech, "market_opportunity": market, "innovation_differentiation": innov},
        "development_complexity": {"level": complexity, "rationale":
                                   "Estimated from technology keywords, project stage and level of detail provided."},
        "target_users": users, "revenue_models": revenue[:5],
        "competitor_ids": [c.id for c in comp],
        "strengths": strengths[:6], "weaknesses": weaknesses[:6], "risks": risks[:6],
        "recommended_improvements": recs[:7], "overall_evaluation": overall,
    }
