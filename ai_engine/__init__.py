"""IdeaBridge AI engine: embeddings, similarity retrieval, evaluation and matching.

Pure Python + numpy. Network calls use only the standard library (urllib) so the
engine can be tested without any web framework installed.
"""
from .embeddings import EmbeddingProvider, LocalHashEmbedder, OpenAIEmbedder, get_embedder
from .evaluator import EvaluationEngine, Retrieved
from .llm import LLMProvider, get_llm
from .matching import match_idea_to_profile

__all__ = [
    "EmbeddingProvider", "LocalHashEmbedder", "OpenAIEmbedder", "get_embedder",
    "EvaluationEngine", "Retrieved", "LLMProvider", "get_llm", "match_idea_to_profile",
]
