from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse, urlunparse
from urllib.robotparser import RobotFileParser

import httpx

from .config import cache_directory, load_app_config

logger = logging.getLogger(__name__)


@dataclass
class FetchResult:
    url: str
    status_code: int
    content: str
    fetched_at: datetime
    headers: Dict[str, str]
    from_cache: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class FetchCache:
    """File-based fetch cache keyed by URL hash."""

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        (self.cache_dir / "fetch").mkdir(parents=True, exist_ok=True)

    def _cache_path(self, url: str) -> Path:
        url_str = str(url)
        sha = hashlib.sha256(url_str.encode("utf-8")).hexdigest()
        return self.cache_dir / "fetch" / f"{sha}.json"

    def get(self, url: str) -> Optional[FetchResult]:
        path = self._cache_path(url)
        if not path.exists():
            return None
        try:
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Cache read failed for %s: %s", url, exc)
            return None
        return FetchResult(
            url=payload["url"],
            status_code=payload["status_code"],
            content=payload["content"],
            fetched_at=datetime.fromisoformat(payload["fetched_at"]),
            headers=payload.get("headers", {}),
            from_cache=True,
            metadata=payload.get("metadata", {}),
        )

    def set(self, result: FetchResult) -> None:
        path = self._cache_path(result.url)
        payload = {
            "url": result.url,
            "status_code": result.status_code,
            "content": result.content,
            "headers": result.headers,
            "fetched_at": result.fetched_at.isoformat(),
            "metadata": result.metadata,
        }
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle)


class RobotsChecker:
    """Minimal robots.txt checker."""

    def __init__(self, user_agent: str):
        self.user_agent = user_agent
        self._parsers: Dict[str, RobotFileParser] = {}

    def allowed(self, url: str) -> bool:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        parser = self._parsers.get(base)
        if parser is None:
            robots_url = f"{base}/robots.txt"
            parser = RobotFileParser()
            try:
                parser.set_url(robots_url)
                parser.read()
            except Exception:
                logger.debug("Failed to read robots.txt at %s, defaulting to allow.", robots_url)
            self._parsers[base] = parser
        allowed = parser.can_fetch(self.user_agent, url)
        return allowed if allowed is not None else True


class Fetcher:
    """HTTP client with caching and robots compliance."""

    def __init__(self, user_agent: str = "MiniPerplexity/0.1", timeout: float = 20.0):
        self.user_agent = user_agent
        self.timeout = timeout
        self.cache = FetchCache(cache_directory())
        self.robots = RobotsChecker(user_agent=user_agent)
        self.config = load_app_config()

    async def fetch(self, url: str, use_cache: bool = True) -> Optional[FetchResult]:
        requested_url = str(url)
        normalized_url = self._normalize_url(requested_url)

        if use_cache:
            cached = self.cache.get(normalized_url)
            if cached:
                return cached

        fetch_url = normalized_url
        via_proxy = False
        if not self.robots.allowed(fetch_url):
            proxy_url = self._proxy_url(fetch_url)
            if proxy_url:
                logger.info("Routing fetch for %s via proxy %s", fetch_url, proxy_url)
                fetch_url = proxy_url
                via_proxy = True
            else:
                logger.warning("Robots policy disallows fetching %s", fetch_url)
                return None

        headers = {"User-Agent": self.user_agent, "Accept": "text/html,application/pdf"}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(fetch_url, headers=headers)
        except httpx.HTTPError as exc:  # pragma: no cover - network failure
            logger.error("Fetch failed for %s: %s", fetch_url, exc)
            return None

        result = FetchResult(
            url=normalized_url,
            status_code=response.status_code,
            content=response.text,
            fetched_at=datetime.now(timezone.utc),
            headers=dict(response.headers),
            from_cache=False,
            metadata={
                "requested_url": requested_url,
                "fetch_url": fetch_url,
                "via_proxy": via_proxy,
            },
        )
        if response.status_code == 200:
            self.cache.set(result)
        else:
            logger.warning("Non-200 response for %s: %s", fetch_url, response.status_code)
        return result

    def _normalize_url(self, url: str) -> str:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        path = parsed.path

        if "arxiv.org" in host:
            if path.startswith("/pdf/"):
                entry = path[len("/pdf/") :]
                if entry.endswith(".pdf"):
                    entry = entry[:-4]
                path = f"/abs/{entry}"
                parsed = parsed._replace(path=path, query="", fragment="")
            elif path.endswith(".pdf"):
                path = path[:-4]
                parsed = parsed._replace(path=path, query="", fragment="")
            return urlunparse(parsed)

        return url

    def _proxy_url(self, url: str) -> Optional[str]:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        path = parsed.path or "/"
        query = f"?{parsed.query}" if parsed.query else ""

        if host in {"x.com", "www.x.com", "twitter.com", "mobile.twitter.com"}:
            return f"https://r.jina.ai/https://{host}{path}{query}"
        if host.endswith("reddit.com"):
            return f"https://r.jina.ai/https://{host}{path}{query}"
        return None
