import logging

from ai_engine.embeddings import EmbeddingError

log = logging.getLogger("ideabridge")


def safe_embed(fn) -> bool:
    """Run an embedding refresh; an embedding-service outage must not block saving user data."""
    try:
        fn()
        return True
    except EmbeddingError as e:
        log.warning("embedding refresh skipped: %s", e)
        return False
