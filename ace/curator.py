from __future__ import annotations

import logging
from typing import Iterable, List

from .playbook_store import PlaybookStore
from .schemas import PlaybookDelta, PlaybookItem

logger = logging.getLogger(__name__)


class Curator:
    """Deterministically merges reflector deltas into the playbook."""

    def __init__(self, store: PlaybookStore):
        self.store = store

    def merge(self, deltas: Iterable[PlaybookDelta]) -> List[PlaybookItem]:
        if not deltas:
            return []
        existing = self.store.list_items()
        merged: List[PlaybookItem] = []
        for delta in deltas:
            if self._is_duplicate(delta.item, existing):
                logger.debug("Skipping duplicate delta %s", delta.item.id)
                continue
            self.store.upsert_item(delta.item)
            merged.append(delta.item)
            existing.append(delta.item)
        logger.info("Curator merged %s new playbook items.", len(merged))
        return merged

    def _is_duplicate(self, candidate: PlaybookItem, existing: Iterable[PlaybookItem]) -> bool:
        for item in existing:
            if item.id == candidate.id:
                return True
            if item.type == candidate.type and self._content_similarity(item.content, candidate.content) > 0.8:
                return True
        return False

    def _content_similarity(self, a: str, b: str) -> float:
        set_a = {token.lower() for token in a.split()}
        set_b = {token.lower() for token in b.split()}
        if not set_a or not set_b:
            return 0.0
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        return intersection / union
