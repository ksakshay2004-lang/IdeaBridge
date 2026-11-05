"""Embedding providers.

* LocalHashEmbedder  - deterministic, offline, LEXICAL (feature hashing of stemmed
  words, bigrams and character trigrams). It captures shared vocabulary, NOT deep
  meaning. It is the fallback when no embedding API key is configured.
* OpenAIEmbedder     - SEMANTIC embeddings from an OpenAI-compatible endpoint.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import urllib.error
import urllib.request
from collections import Counter
from typing import List, Sequence

import numpy as np

DEFAULT_DIM = 384

_STOP = set("""a an and are as at be but by for from has have he her his i if in into is it its of on or our
she so than that the their them then there these they this to was we were what when where which who will with you
your can could should would may might also more most other some such only own same very just not no nor all any each
few both about above after again against between during before below up down out over under further once here why how
platform app application system solution using use used based provide provides allow allows help helps users user
people""".split())
_TOKEN = re.compile(r"[a-z0-9]+")
_SUFFIXES = ("ations", "ation", "ings", "ing", "edly", "ed", "ies", "es", "s")


class EmbeddingError(RuntimeError):
    pass


def _stem(tok: str) -> str:
    for suf in _SUFFIXES:
        if tok.endswith(suf) and len(tok) - len(suf) >= 3:
            return tok[: -len(suf)] + ("y" if suf == "ies" else "")
    return tok


def tokenize(text: str) -> List[str]:
    return [t for t in _TOKEN.findall((text or "").lower()) if len(t) > 1 and t not in _STOP]


def keywords(text: str, limit: int = 8) -> List[str]:
    counts = Counter(_stem(t) for t in tokenize(text) if len(t) > 3)
    return [w for w, _ in counts.most_common(limit)]


def _normalize(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    return v / n if n > 0 else v


class EmbeddingProvider:
    name = "base"
    model = "base"
    kind = "semantic"  # "semantic" | "lexical"
    dim = DEFAULT_DIM
    # Cosine range used to rescale raw similarity into relevance (0..1) for scoring/matching.
    sim_floor = 0.0
    sim_ceiling = 1.0

    def embed(self, texts: Sequence[str]) -> List[List[float]]:  # pragma: no cover
        raise NotImplementedError

    def embed_one(self, text: str) -> List[float]:
        return self.embed([text])[0]

    def describe(self) -> dict:
        return {"name": self.name, "model": self.model, "kind": self.kind, "dim": self.dim}

    def relevance(self, cosine: float) -> float:
        span = max(self.sim_ceiling - self.sim_floor, 1e-6)
        return float(min(1.0, max(0.0, (cosine - self.sim_floor) / span)))


class LocalHashEmbedder(EmbeddingProvider):
    name = "local-hash"
    model = "local-hash-v1"
    kind = "lexical"
    sim_floor = 0.10   # unrelated texts score ~0.10-0.12 with hashed lexical vectors
    sim_ceiling = 0.45  # clearly related texts score ~0.2-0.3; near-duplicates > 0.45

    def __init__(self, dim: int = DEFAULT_DIM):
        self.dim = dim

    def _slot(self, feature: str):
        h = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
        n = int.from_bytes(h, "big")
        return n % self.dim, 1.0 if (n >> 63) & 1 else -1.0

    def _vector(self, text: str) -> List[float]:
        stems = [_stem(t) for t in tokenize(text)]
        counts: Counter = Counter()
        for s in stems:
            counts["u:" + s] += 1
        for a, b in zip(stems, stems[1:]):
            counts["b:" + a + " " + b] += 1
        for s in stems:
            if len(s) >= 6:
                for i in range(len(s) - 2):
                    counts["c:" + s[i:i + 3]] += 0.25
        vec = np.zeros(self.dim, dtype=np.float64)
        for feat, c in counts.items():
            idx, sign = self._slot(feat)
            weight = (1.0 + math.log(c)) if c >= 1 else c
            if feat.startswith("b:"):
                weight *= 1.5
            vec[idx] += sign * weight
        return _normalize(vec).tolist()

    def embed(self, texts: Sequence[str]) -> List[List[float]]:
        return [self._vector(t) for t in texts]


class OpenAIEmbedder(EmbeddingProvider):
    name = "openai"
    kind = "semantic"
    sim_floor = 0.25
    sim_ceiling = 0.75

    def __init__(self, api_key: str, model: str = "text-embedding-3-small", dim: int = DEFAULT_DIM,
                 base_url: str = "https://api.openai.com/v1", timeout: int = 60):
        if not api_key:
            raise EmbeddingError("OpenAI API key missing")
        self.api_key, self.model, self.dim = api_key, model, dim
        self.base_url, self.timeout = base_url.rstrip("/"), timeout

    def embed(self, texts: Sequence[str]) -> List[List[float]]:
        payload = {"model": self.model, "input": [t[:8000] for t in texts]}
        if self.model.startswith("text-embedding-3"):
            payload["dimensions"] = self.dim
        req = urllib.request.Request(
            self.base_url + "/embeddings", data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                data = json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            raise EmbeddingError(f"Embedding API returned HTTP {e.code}") from None
        except Exception as e:  # network, timeout, json
            raise EmbeddingError(f"Embedding request failed: {type(e).__name__}") from None
        out = []
        for item in sorted(data.get("data", []), key=lambda d: d.get("index", 0)):
            v = np.asarray(item["embedding"], dtype=np.float64)
            if v.shape[0] != self.dim:
                raise EmbeddingError(f"Embedding dimension {v.shape[0]} != configured {self.dim}")
            out.append(_normalize(v).tolist())
        if len(out) != len(texts):
            raise EmbeddingError("Embedding API returned an unexpected number of vectors")
        return out


def get_embedder(provider: str = "local", model: str = "", dim: int = DEFAULT_DIM,
                 api_key: str = "", base_url: str = "https://api.openai.com/v1") -> EmbeddingProvider:
    """Return the configured provider; falls back to the local lexical embedder if no key is set."""
    if provider == "openai" and api_key:
        return OpenAIEmbedder(api_key, model or "text-embedding-3-small", dim, base_url)
    return LocalHashEmbedder(dim)
