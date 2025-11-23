from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Iterable, List, Optional, Tuple

from .config import load_app_config, load_sources_config
from .fetch import Fetcher
from .llm import LLMClientFactory
from .planner import Planner, PlannerConfig
from .search import BraveSearchProvider, SearchProvider, SearchQuery, SearchService
from .chunks import chunk_corpus
from .parse import extract_document
from .rank import Retriever, RetrieverConfig
from .synth import Synthesizer, SynthesizerConfig
from .types import (
    AnswerResponse,
    DocumentChunk,
    PlannerStep,
    QueryRequest,
    RetrievedDocument,
    RunMetadata,
    SearchResult,
)
from .validate import validate_answer

logger = logging.getLogger(__name__)


class Pipeline:
    """High-level orchestrator for the Mini-Perplexity workflow."""

    def __init__(self) -> None:
        self.app_config = load_app_config()
        self.sources_config = load_sources_config()
        self.llm_factory = LLMClientFactory(self.app_config.get("models", {}))
        self.planner = Planner(
            PlannerConfig(),
            llm_factory=self.llm_factory,
            sources_config=self.sources_config,
        )
        self.fetcher = Fetcher()
        self.synthesizer = Synthesizer(SynthesizerConfig(), llm_factory=self.llm_factory)
        self.retriever = Retriever(
            RetrieverConfig(
                embedding_model=self.app_config.get("models", {})
                .get("embeddings", {})
                .get("model", "intfloat/e5-large-v2"),
                reranker_model=self.app_config.get("models", {})
                .get("reranker", {})
                .get("model", "BAAI/bge-reranker-base"),
                use_reranker=True,
            )
        )
        self.search_service = SearchService(self._build_search_provider())

    def _build_search_provider(self) -> SearchProvider:
        search_cfg = self.app_config.get("search", {})
        provider_name = search_cfg.get("provider", "brave")
        if provider_name == "brave":
            brave_cfg = search_cfg.get("brave", {})
            return BraveSearchProvider(
                api_key=brave_cfg.get("api_key", ""),
                endpoint=brave_cfg.get("endpoint", "https://api.search.brave.com/res/v1/web/search"),
                timeout=self.app_config.get("limits", {}).get("request_timeout_seconds", 20),
            )
        raise ValueError(f"Unsupported search provider: {provider_name}")

    async def run(
        self,
        request: QueryRequest,
        playbook_hints: Optional[Iterable[str]] = None,
    ) -> Tuple[AnswerResponse, RunMetadata]:
        run_id = str(uuid.uuid4())
        planner_steps = await self.planner.plan(request, playbook_hints=playbook_hints)
        search_queries: List[SearchQuery] = [
            query for step in planner_steps for query in step.search_queries
        ]

        search_results = await self.search_service.batch_search(
            search_queries, top_k=request.max_sources
        )

        documents = await self._fetch_and_parse(search_results[: request.max_sources])
        chunks = chunk_corpus(documents)
        ranked_chunks = self.retriever.rank(
            request.question,
            chunks,
            top_k=min(len(chunks), self.app_config.get("limits", {}).get("max_chunks", 40)),
        )
        answer, synth_metadata = await self.synthesizer.synthesize(request, ranked_chunks, run_id)
        report = validate_answer(answer)
        metadata = RunMetadata(
            run_id=run_id,
            question=request.question,
            planner_steps=planner_steps,
            search_results=search_results,
            fetched_documents=documents,
            selected_chunks=ranked_chunks,
            citations=synth_metadata.citations,
            validator_report=report,
            extra={"synthesizer": synth_metadata.extra.get("synthesizer", {})},
        )
        answer.metadata["validation"] = report.model_dump()
        return answer, metadata

    async def _fetch_and_parse(
        self,
        search_results: Iterable[SearchResult],
    ) -> List[RetrievedDocument]:
        documents: List[RetrievedDocument] = []

        async def fetch_single(result: SearchResult) -> Optional[RetrievedDocument]:
            fetch_result = await self.fetcher.fetch(str(result.url))
            
            # Fallback to snippet if fetch fails or is blocked
            if not fetch_result or fetch_result.status_code >= 400 or len(fetch_result.content) < 200:
                 logger.warning(f"Fetch failed or blocked for {result.url}, using snippet.")
                 return RetrievedDocument(
                     url=result.url,
                     title=result.title,
                     text=result.snippet, # Use snippet as text
                     source_type=result.source_type,
                     published_at=result.published_at,
                     metadata={"fallback": True}
                 )

            document = extract_document(
                fetch_result,
                source_type=result.source_type,
                title_hint=result.title,
            )
            
            # If extraction failed (empty text), fallback to snippet
            if not document or not document.text.strip():
                 return RetrievedDocument(
                     url=result.url,
                     title=result.title,
                     text=result.snippet,
                     source_type=result.source_type,
                     published_at=result.published_at,
                     metadata={"fallback": True}
                 )
            return document

        tasks = [fetch_single(result) for result in search_results]
        for coro in asyncio.as_completed(tasks):
            document = await coro
            if document:
                documents.append(document)
        return documents
