from __future__ import annotations

import logging
import re
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import List

from core.types import RunMetadata, SourceType

from .schemas import PlaybookDelta, PlaybookItem, PlaybookItemType

logger = logging.getLogger(__name__)


class Reflector:
    """Analyzes run traces to propose playbook deltas."""

    def __init__(self, freshness_buffer_days: int = 2):
        self.freshness_buffer_days = freshness_buffer_days

    def critique(self, metadata: RunMetadata) -> List[PlaybookDelta]:
        deltas: List[PlaybookDelta] = []
        deltas.extend(self._check_validation(metadata))
        deltas.extend(self._check_freshness(metadata))
        deltas.extend(self._check_source_coverage(metadata))
        return deltas

    def _check_validation(self, metadata: RunMetadata) -> List[PlaybookDelta]:
        if not metadata.validator_report or metadata.validator_report.passed:
            return []
        missing = [
            issue for issue in metadata.validator_report.issues if "missing citation" in issue.message.lower()
        ]
        if not missing:
            return []
        content = (
            "Ensure every bullet references at least one snippet; "
            "if evidence is weak, rerun retrieval with broader filters."
        )
        item = PlaybookItem(
            id=f"validation:{uuid.uuid4().hex[:8]}",
            type=PlaybookItemType.VALIDATION_RULE,
            content=content,
            helpful=1,
            harmful=0,
            tags=["validation", "citations"],
        )
        return [PlaybookDelta(item=item, rationale="Validation coverage below threshold.", run_id=metadata.run_id)]

    def _check_freshness(self, metadata: RunMetadata) -> List[PlaybookDelta]:
        deltas: List[PlaybookDelta] = []
        now = datetime.now(timezone.utc)
        stale_counts: Counter = Counter()
        for citation in metadata.citations:
            if citation.published_at is None:
                continue
            age_days = (now - citation.published_at).days
            if citation.source_type in {SourceType.TWITTER, SourceType.REDDIT}:
                freshness_limit = 5
            elif citation.source_type == SourceType.NEWS:
                freshness_limit = 10
            else:
                freshness_limit = 14
            if age_days > freshness_limit + self.freshness_buffer_days:
                stale_counts[citation.source_type] += 1
        for source_type, count in stale_counts.items():
            content = (
                f"For {source_type.value} sources, add 'sort:recent' or date filters when "
                f"question includes 'new' or 'latest'."
            )
            item = PlaybookItem(
                id=f"freshness:{source_type.value}:{uuid.uuid4().hex[:6]}",
                type=PlaybookItemType.QUERY_REWRITE,
                content=content,
                helpful=count,
                harmful=0,
                tags=[source_type.value, "fresh"],
            )
            deltas.append(
                PlaybookDelta(
                    item=item,
                    rationale=f"{count} citation(s) exceeded freshness window.",
                    run_id=metadata.run_id,
                )
            )
        return deltas

    def _check_source_coverage(self, metadata: RunMetadata) -> List[PlaybookDelta]:
        question_tokens = set(re.findall(r"[a-zA-Z0-9]+", metadata.question.lower()))
        expected_sources = self._infer_expected_sources(question_tokens)
        present_sources = {result.source_type for result in metadata.search_results}
        missing = expected_sources - present_sources
        deltas: List[PlaybookDelta] = []
        for source_type in missing:
            content = (
                f"When question mentions {source_type.value}, add explicit site filter "
                f"for {source_type.value} in the planner search queries."
            )
            item = PlaybookItem(
                id=f"coverage:{source_type.value}:{uuid.uuid4().hex[:6]}",
                type=PlaybookItemType.QUERY_REWRITE,
                content=content,
                helpful=1,
                harmful=0,
                tags=[source_type.value, "coverage"],
            )
            deltas.append(
                PlaybookDelta(
                    item=item,
                    rationale=f"Planner missed {source_type.value} coverage.",
                    run_id=metadata.run_id,
                )
            )
        return deltas

    def _infer_expected_sources(self, tokens: set[str]) -> set[SourceType]:
        expected: set[SourceType] = set()
        if {"git", "github", "repo"}.intersection(tokens):
            expected.add(SourceType.GITHUB)
        if {"huggingface", "model", "checkpoint"}.intersection(tokens):
            expected.add(SourceType.HUGGINGFACE)
        if {"paper", "arxiv", "research"}.intersection(tokens):
            expected.add(SourceType.ARXIV)
        if {"news", "launch", "latest"}.intersection(tokens):
            expected.add(SourceType.NEWS)
        if {"twitter", "tweet", "x"}.intersection(tokens):
            expected.add(SourceType.TWITTER)
        if {"reddit", "discussion", "thread"}.intersection(tokens):
            expected.add(SourceType.REDDIT)
        return expected
