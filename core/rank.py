from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple

import numpy as np

from .types import DocumentChunk

logger = logging.getLogger(__name__)

try:
    from sentence_transformers import CrossEncoder, SentenceTransformer, util
except ImportError:  # pragma: no cover - optional dependency
    SentenceTransformer = None
    CrossEncoder = None
    util = None


@dataclass
class RetrieverConfig:
    embedding_model: str = "intfloat/e5-large-v2"
    reranker_model: str = "BAAI/bge-reranker-base"
    use_reranker: bool = True
    top_k: int = 12


class Retriever:
    """Two-stage embedding + reranker retriever."""

    def __init__(self, config: RetrieverConfig):
        self.config = config
        self._embedder = None
        self._reranker = None
        if SentenceTransformer:
            try:
                self._embedder = SentenceTransformer(config.embedding_model)
            except Exception as exc:
                logger.warning("Failed to load embeddings model %s: %s", config.embedding_model, exc)
        if config.use_reranker and CrossEncoder:
            try:
                self._reranker = CrossEncoder(config.reranker_model)
            except Exception as exc:
                logger.warning("Failed to load reranker model %s: %s", config.reranker_model, exc)

    def _embed(self, texts: Sequence[str]) -> np.ndarray:
        if self._embedder is None:  # pragma: no cover - fallback
            logger.debug("SentenceTransformer not available; returning zero embeddings.")
            return np.zeros((len(texts), 768))
        return self._embedder.encode(
            texts, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False
        )

    def _rerank(self, query: str, candidates: Sequence[DocumentChunk]) -> List[Tuple[DocumentChunk, float]]:
        if self._reranker is None:  # pragma: no cover - fallback
            return [(chunk, chunk.score) for chunk in candidates]
        pairs = [[query, chunk.text] for chunk in candidates]
        scores = self._reranker.predict(pairs)
        return list(zip(candidates, scores))

    def rank(self, query: str, chunks: Iterable[DocumentChunk], top_k: Optional[int] = None) -> List[DocumentChunk]:
        chunks_list = list(chunks)
        if not chunks_list:
            return []
        top_k = top_k or self.config.top_k
        embeddings = self._embed([chunk.text for chunk in chunks_list])
        if embeddings.size == 0:
            # fallback lexical scoring
            logger.debug("No embeddings available; using lexical overlap scoring.")
            scored = [(chunk, self._lexical_score(query, chunk)) for chunk in chunks_list]
        else:
            query_embedding = self._embed([query])[0]
            scores = np.dot(embeddings, query_embedding)
            for chunk, score in zip(chunks_list, scores):
                chunk.score = float(score)
            scored = sorted(zip(chunks_list, scores), key=lambda item: item[1], reverse=True)[: top_k * 2]
        candidates = [item[0] for item in scored]
        reranked = self._rerank(query, candidates)
        reranked.sort(key=lambda item: item[1], reverse=True)
        top_chunks: List[DocumentChunk] = []
        for chunk, score in reranked[:top_k]:
            chunk.score = float(score)
            top_chunks.append(chunk)
        return top_chunks

    @staticmethod
    def _lexical_score(query: str, chunk: DocumentChunk) -> float:
        query_terms = {term.lower() for term in query.split()}
        chunk_terms = {term.lower() for term in chunk.text.split()}
        if not chunk_terms:
            return 0.0
        overlap = query_terms.intersection(chunk_terms)
        return len(overlap) / len(query_terms or {1})
