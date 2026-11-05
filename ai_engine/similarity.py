"""Vector similarity helpers (used directly for SQLite/dev and as the reference for pgvector)."""
from __future__ import annotations

from typing import Hashable, List, Sequence, Tuple

import numpy as np


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    va, vb = np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)
    na, nb = np.linalg.norm(va), np.linalg.norm(vb)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(va, vb) / (na * nb))


def top_k(query: Sequence[float], items: Sequence[Tuple[Hashable, Sequence[float]]], k: int = 5
          ) -> List[Tuple[Hashable, float]]:
    """Return the k (id, cosine) pairs most similar to ``query``, best first."""
    if not items or k <= 0:
        return []
    ids = [i for i, _ in items]
    mat = np.asarray([v for _, v in items], dtype=np.float64)
    q = np.asarray(query, dtype=np.float64)
    norms = np.linalg.norm(mat, axis=1) * (np.linalg.norm(q) or 1.0)
    norms[norms == 0] = 1.0
    sims = mat @ q / norms
    order = np.argsort(-sims)[:k]
    return [(ids[i], float(sims[i])) for i in order]
