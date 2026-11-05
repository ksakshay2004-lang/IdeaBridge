"""Parsing and normalisation of evaluation reports (no third-party validation library needed)."""
from __future__ import annotations

import json
import re
from typing import Any, List

LEVELS = ("low", "moderate", "high")


def clamp_score(v: Any, default: int = 50) -> int:
    try:
        return max(0, min(100, int(round(float(v)))))
    except (TypeError, ValueError):
        return default


def as_str(v: Any, limit: int = 2500) -> str:
    return (v if isinstance(v, str) else "").strip()[:limit]


def as_str_list(v: Any, max_items: int = 8, limit: int = 400) -> List[str]:
    if isinstance(v, str):
        v = [v]
    if not isinstance(v, list):
        return []
    return [s.strip()[:limit] for s in v if isinstance(s, str) and s.strip()][:max_items]


def as_level(v: Any, default: str = "moderate") -> str:
    s = str(v or "").strip().lower()
    return s if s in LEVELS else default


def extract_json(text: str) -> dict:
    """Pull a JSON object out of an LLM reply (tolerates code fences / surrounding prose)."""
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", (text or "").strip(), flags=re.I)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object found in model output")
    obj = json.loads(text[start:end + 1])
    if not isinstance(obj, dict):
        raise ValueError("model output is not a JSON object")
    return obj
