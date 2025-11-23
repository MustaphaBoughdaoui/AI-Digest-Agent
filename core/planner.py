from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence

from .config import load_sources_config
from .llm import LLMClient, LLMClientFactory, LLMMessage
from .types import PlannerStep, QueryRequest, SearchQuery, SourceType

logger = logging.getLogger(__name__)


_SOURCE_ALIASES = {
    SourceType.ARXIV: {
        "paper", "arxiv", "research", "publication", "preprint", "pdf", "study", "journal"
    },
    SourceType.GITHUB: {
        "github", "repo", "repository", "framework", "code", "implementation", 
        "library", "sdk", "api", "install", "pip", "rust", "python"
    },
    SourceType.HUGGINGFACE: {
        "huggingface", "model", "checkpoint", "dataset", "weights", "lora", "gguf", "quantized"
    },
    SourceType.NEWS: {
        "news", "announce", "launch", "report", "release", "update", "breaking", 
        "business", "startup", "funding"
    },
    SourceType.BLOG: {
        "blog", "analysis", "review", "opinion", "newsletter", "guide", "tutorial", 
        "how-to", "explained", "deep dive"
    },
    SourceType.TWITTER: {
        "twitter", "tweet", "tweets", "x.com", "x", "reaction", "sentiment", 
        "community", "thread", "digest", "influencers"
    },
    SourceType.REDDIT: {
        "reddit", "thread", "discussion", "subreddit", "tricks", "hacks", "tips", 
        "experience", "review", "comparison", "vs"
    },
}


def _match_source_types(question: str, include_defaults: bool = True) -> List[SourceType]:
    normalized = question.lower()
    matches: List[SourceType] = []
    for source_type, keywords in _SOURCE_ALIASES.items():
        if any(keyword in normalized for keyword in keywords):
            matches.append(source_type)
    
    # Special handling for "latest" keywords triggering social sources
    if any(term in normalized for term in {"latest", "breaking", "today", "recent", "updates", "digest", "tricks", "hacks", "tips"}):
        if SourceType.TWITTER not in matches:
            matches.append(SourceType.TWITTER)
        if SourceType.REDDIT not in matches:
            matches.append(SourceType.REDDIT)
            
    if not matches and include_defaults:
        # default to broad coverage for discovery queries
        matches = [
            SourceType.ARXIV,
            SourceType.GITHUB,
            SourceType.HUGGINGFACE,
            SourceType.NEWS,
            SourceType.BLOG,
        ]
    return matches


def _tokenize(question: str) -> List[str]:
    return [token for token in re.split(r"[^a-z0-9]+", question.lower()) if token]


def _generate_focus_terms(tokens: Sequence[str]) -> List[str]:
    focus_terms: List[str] = []
    for token in tokens:
        if len(token) <= 3:
            continue
        if token in {"what", "whats", "new", "latest", "compare", "versus", "vs", "digest"}:
            continue
        focus_terms.append(token)
    return focus_terms[:6]


@dataclass
class PlannerConfig:
    max_steps: int = 3
    llm_section: str = "planner"


class Planner:
    """Simple ReAct + Self-Ask style planner."""

    def __init__(
        self,
        config: PlannerConfig,
        llm_factory: LLMClientFactory,
        sources_config: Optional[dict] = None,
    ) -> None:
        self.config = config
        self._llm = llm_factory.build(config.llm_section)
        self.sources_config = sources_config or load_sources_config()

    async def plan(
        self,
        request: QueryRequest,
        playbook_hints: Optional[Iterable[str]] = None,
    ) -> List[PlannerStep]:
        logger.info("Planning for question: %s", request.question)
        tokens = _tokenize(request.question)
        focus_terms = _generate_focus_terms(tokens)
        matched_sources = _match_source_types(request.question)

        hints_text = "\n".join(playbook_hints or [])
        steps: List[PlannerStep] = []

        # Step 1: Generate sub-questions via LLM (Self-Ask style)
        llm_messages = [
            LLMMessage(
                role="system",
                content=(
                    "You are a planning assistant that decomposes research questions "
                    "about AI/ML into focused search tasks. "
                    "Return 2-4 bullet points each describing a sub-task. "
                    "Keep bullets short."
                ),
            ),
            LLMMessage(role="user", content=f"Question: {request.question}\n{hints_text}"),
        ]
        try:
            llm_response = await self._llm.generate(llm_messages, temperature=0.2)
            sub_tasks = [
                line.strip("- ").strip()
                for line in llm_response.content.splitlines()
                if line.strip()
            ]
        except Exception as exc:  # pragma: no cover - network fallback
            logger.exception("Planner LLM failed, falling back to heuristics: %s", exc)
            sub_tasks = [f"Investigate {term}" for term in focus_terms[:3]]

        if not sub_tasks:
            sub_tasks = ["Gather recent AI/ML updates relevant to the query."]

        for idx, task in enumerate(sub_tasks[: self.config.max_steps]):
            search_queries: List[SearchQuery] = []
            
            # Determine sources relevant to this specific task
            task_sources = _match_source_types(task, include_defaults=False)
            
            # If task has specific sources, prioritize them. Otherwise fallback to global matches.
            # We union them to ensure we don't miss global intent (e.g. "Check reddit" in main prompt)
            effective_sources = set(task_sources) | set(matched_sources)
            
            # If still empty (unlikely due to defaults in matched_sources), use defaults
            if not effective_sources:
                 effective_sources = {
                    SourceType.ARXIV, SourceType.GITHUB, SourceType.NEWS, SourceType.BLOG
                 }

            for source_type in effective_sources:
                cfg = self.sources_config.get(source_type.value)
                if not cfg:
                    continue
                query_base: str = cfg.get("query_base", "")
                freshness_days = cfg.get("freshness_days")
                augmented_terms = " ".join(focus_terms[:6]) or request.question
                rewrite = self._apply_playbook(
                    task,
                    request.question,
                    source_type,
                    playbook_hints,
                )
                
                # Split query_base if it contains many OR clauses to avoid URI length limits
                base_parts = [p.strip() for p in query_base.split(" OR ")]
                chunk_size = 8  # Conservative chunk size for search engines
                chunks = [base_parts[i:i + chunk_size] for i in range(0, len(base_parts), chunk_size)]

                for chunk in chunks:
                    chunk_base = " OR ".join(chunk)
                    parts = [chunk_base]
                    if augmented_terms:
                        parts.append(augmented_terms)
                    if rewrite:
                        parts.append(rewrite)
                    final_query = " ".join(filter(None, parts))
                    search_queries.append(
                        SearchQuery(
                            query=final_query.strip(),
                            source_type=source_type,
                            rationale=f"Focus on {source_type.value} sources for task: {task}",
                            freshness_days=freshness_days,
                        )
                    )
            steps.append(
                PlannerStep(
                    thought=f"Step {idx + 1}: {task}",
                    search_queries=search_queries,
                )
            )
        return steps

    def _apply_playbook(
        self,
        task: str,
        question: str,
        source_type: SourceType,
        playbook_hints: Optional[Iterable[str]],
    ) -> Optional[str]:
        """Apply simple heuristic rewrites using playbook hints."""

        if not playbook_hints:
            return None
        task_lower = task.lower()
        question_lower = question.lower()
        for hint in playbook_hints:
            hint_lower = hint.lower()
            rewrite = None
            if "=>" in hint:
                parts = hint.split("=>", 1)
                trigger_part = parts[0].strip()
                rewrite = parts[1].strip()
                if not rewrite:
                    continue
                source_filter: Optional[str] = None
                trigger = trigger_part
                if ":" in trigger_part:
                    source_filter, trigger = [segment.strip().lower() for segment in trigger_part.split(":", 1)]
                trigger = trigger.lower()
                if source_filter and not self._source_matches(source_filter, source_type):
                    continue
                if trigger:
                    if trigger in task_lower or trigger in question_lower:
                        logger.debug(
                            "Applying playbook trigger '%s' for source '%s'", trigger_part, source_type.value
                        )
                        return rewrite
                else:
                    logger.debug(
                        "Applying playbook source-only rule '%s' for source '%s'",
                        trigger_part,
                        source_type.value,
                    )
                    return rewrite
            if any(alias in hint_lower for alias in _SOURCE_ALIASES.get(source_type, set())) and rewrite:
                return rewrite
        return None

    def _source_matches(self, key: str, source_type: SourceType) -> bool:
        if key == source_type.value:
            return True
        aliases = _SOURCE_ALIASES.get(source_type, set())
        return key in aliases
