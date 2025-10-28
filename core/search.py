from __future__ import annotations

import abc
import logging
from datetime import datetime
from typing import Dict, Iterable, List, Optional
from urllib.parse import urlencode

import httpx

from .types import SearchQuery, SearchResult, SourceType

logger = logging.getLogger(__name__)


class SearchProvider(abc.ABC):
    """Abstract search provider."""

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout

    @abc.abstractmethod
    async def search(self, query: SearchQuery, top_k: int = 10) -> List[SearchResult]:
        raise NotImplementedError


class BraveSearchProvider(SearchProvider):
    """Brave search API implementation."""

    def __init__(self, api_key: str, endpoint: str, timeout: float = 10.0):
        super().__init__(timeout=timeout)
        self.api_key = api_key
        self.endpoint = endpoint.rstrip("/")
        if not api_key:
            logger.warning("Brave API key not provided. Search will be mocked.")

    async def search(self, query: SearchQuery, top_k: int = 10) -> List[SearchResult]:
        if not self.api_key:
            return self._offline_results(query, top_k)

        params = {
            "q": query.query,
            "count": top_k,
            "freshness": self._freshness_param(query),
        }
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self.api_key,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(self.endpoint, params=params, headers=headers)
            response.raise_for_status()
            payload = response.json()
        return self._parse(payload, query)

    def _parse(self, payload: Dict, query: SearchQuery) -> List[SearchResult]:
        web_results = payload.get("web", {}).get("results", [])
        results: List[SearchResult] = []
        for item in web_results:
            url = item.get("url")
            if not url:
                continue
            published_at = item.get("published")
            dt = None
            if published_at:
                try:
                    dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                except ValueError:
                    dt = None
            results.append(
                SearchResult(
                    url=url,
                    title=item.get("title", "Untitled"),
                    snippet=item.get("snippet", ""),
                    score=float(item.get("score", 0.0)),
                    source_type=query.source_type,
                    published_at=dt,
                )
            )
        return results

    def _freshness_param(self, query: SearchQuery) -> Optional[str]:
        if query.freshness_days:
            return f"pd:{query.freshness_days}d"
        return None

    def _offline_results(self, query: SearchQuery, top_k: int) -> List[SearchResult]:
        logger.info("Returning offline mock results for query %s", query.query)
        return [
            SearchResult(
                url=f"https://example.com/{idx}?{urlencode({'q': query.query})}",
                title=f"Mock result {idx} for {query.query}",
                snippet="No API key configured. This is a stub result.",
                score=1.0 / (idx + 1),
                source_type=query.source_type,
            )
            for idx in range(top_k)
        ]


class SearchService:
    """High-level search orchestrator."""

    def __init__(self, provider: SearchProvider, dedupe: bool = True):
        self.provider = provider
        self.dedupe = dedupe

    async def batch_search(
        self, queries: Iterable[SearchQuery], top_k: int = 8
    ) -> List[SearchResult]:
        seen_urls: Dict[str, SearchResult] = {}
        all_results: List[SearchResult] = []
        for search_query in queries:
            provider_results = await self.provider.search(search_query, top_k=top_k)
            for result in provider_results:
                if not self.dedupe:
                    all_results.append(result)
                    continue
                key = str(result.url)
                existing = seen_urls.get(key)
                if existing:
                    if result.score > existing.score:
                        seen_urls[key] = result
                else:
                    seen_urls[key] = result
        if not self.dedupe:
            return self._limit_with_diversity(all_results, top_k)
        deduped = list(seen_urls.values())
        return self._limit_with_diversity(deduped, top_k)

    def _limit_with_diversity(self, results: List[SearchResult], top_k: int) -> List[SearchResult]:
        if len(results) <= top_k:
            return results
        buckets: Dict[SourceType, List[SearchResult]] = {}
        for result in results:
            buckets.setdefault(result.source_type, []).append(result)
        for bucket in buckets.values():
            bucket.sort(key=lambda item: item.score, reverse=True)
        ordered: List[SearchResult] = []
        # first pass: round-robin highest scoring per source to guarantee coverage
        while len(ordered) < top_k:
            progressed = False
            for source_type, bucket in sorted(
                buckets.items(),
                key=lambda entry: entry[1][0].score if entry[1] else 0,
                reverse=True,
            ):
                if not bucket:
                    continue
                ordered.append(bucket.pop(0))
                progressed = True
                if len(ordered) >= top_k:
                    break
            if not progressed:
                break
        if len(ordered) >= top_k:
            return ordered[:top_k]
        # fill with remaining highest scoring irrespective of source
        remaining = [result for bucket in buckets.values() for result in bucket]
        remaining.sort(key=lambda item: item.score, reverse=True)
        for result in remaining:
            if len(ordered) >= top_k:
                break
            ordered.append(result)
        return ordered[:top_k]
