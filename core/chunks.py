from __future__ import annotations

import hashlib
import logging
from typing import Iterable, List

from .types import DocumentChunk, RetrievedDocument

logger = logging.getLogger(__name__)


def _chunk_id(document: RetrievedDocument, index: int) -> str:
    digest = hashlib.md5(f"{document.url}-{index}".encode("utf-8")).hexdigest()
    return f"chunk-{digest[:12]}"


def split_into_chunks(
    document: RetrievedDocument,
    max_tokens: int = 220,
    stride: int = 60,
) -> List[DocumentChunk]:
    """Split document text into overlapping token windows."""

    words = document.text.split()
    chunks: List[DocumentChunk] = []
    if not words:
        return chunks
    start = 0
    index = 0
    while start < len(words):
        window = words[start : start + max_tokens]
        snippet = " ".join(window)
        chunk = DocumentChunk(
            id=_chunk_id(document, index),
            url=document.url,
            title=document.title,
            text=snippet,
            score=0.0,
            source_type=document.source_type,
            published_at=document.published_at,
            metadata={
                "start_word": start,
                "end_word": min(len(words), start + max_tokens),
            },
        )
        chunks.append(chunk)
        index += 1
        start += max(1, max_tokens - stride)
    return chunks


def chunk_corpus(documents: Iterable[RetrievedDocument]) -> List[DocumentChunk]:
    documents_list = list(documents)
    aggregated: List[DocumentChunk] = []
    for doc in documents_list:
        aggregated.extend(split_into_chunks(doc))
    logger.info("Chunked %s documents into %s windows.", len(documents_list), len(aggregated))
    return aggregated
