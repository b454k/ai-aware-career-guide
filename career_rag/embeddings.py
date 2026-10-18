"""The embedding model, run locally: Qwen3-Embedding-0.6B (Apache-2.0), for the follow-up ranker and the research
pipeline (CHANGELOG 104). Texts are embedded as they are; queries get an instruction saying what they are for, as
the model expects ("Instruct: ...\\nQuery:")."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from career_rag.config import EMBEDDING_MODEL_NAME, EMBEDDING_MODEL_REVISION


@lru_cache(maxsize=1)
def embedding_model() -> Any:
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBEDDING_MODEL_NAME, revision=EMBEDDING_MODEL_REVISION, device="cpu")


def embed_documents(texts: list[str]) -> Any:
    """Normalized vectors (float32), one row per text."""
    return embedding_model().encode(texts, batch_size=32, normalize_embeddings=True, show_progress_bar=False)


def embed_queries(texts: list[str], instruction: str) -> Any:
    """Normalized vectors for queries, each with the instruction that says what is being searched for."""
    return embedding_model().encode(texts, prompt=f"Instruct: {instruction}\nQuery:", batch_size=32,
                                    normalize_embeddings=True, show_progress_bar=False)
