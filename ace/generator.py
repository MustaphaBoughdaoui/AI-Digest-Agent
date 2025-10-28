from __future__ import annotations

import logging
from typing import Iterable, List, Optional, Tuple

from core.pipeline import Pipeline
from core.types import AnswerResponse, QueryRequest, RunMetadata

from .playbook_store import PlaybookStore

logger = logging.getLogger(__name__)


class Generator:
    """Wraps the core pipeline with playbook retrieval."""

    def __init__(self, pipeline: Optional[Pipeline] = None, store: Optional[PlaybookStore] = None):
        self.pipeline = pipeline or Pipeline()
        self.store = store or PlaybookStore()

    async def answer(self, request: QueryRequest) -> Tuple[AnswerResponse, RunMetadata]:
        hints = self._retrieve_playbook_hints(request.question) if request.include_playbook else []
        answer, metadata = await self.pipeline.run(request, playbook_hints=hints)
        metadata.extra["playbook_hints"] = hints
        return answer, metadata

    def _retrieve_playbook_hints(self, question: str) -> List[str]:
        keywords = self._extract_keywords(question)
        items = self.store.search_by_keywords(keywords, limit=5)
        hints = [item.content for item in items]
        logger.debug("Retrieved %s playbook hints for question.", len(hints))
        return hints

    def _extract_keywords(self, text: str) -> Iterable[str]:
        words = {word.lower() for word in text.split() if len(word) > 3}
        return list(words)
