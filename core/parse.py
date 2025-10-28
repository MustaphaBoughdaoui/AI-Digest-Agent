from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

import trafilatura
from bs4 import BeautifulSoup

from .fetch import FetchResult
from .types import RetrievedDocument, SourceType

logger = logging.getLogger(__name__)


def _detect_title(html: str) -> str:
    try:
        soup = BeautifulSoup(html, "lxml")
        if soup.title and soup.title.text:
            return soup.title.text.strip()
    except Exception:
        pass
    return "Untitled"


def _detect_published_at(html: str) -> Optional[datetime]:
    try:
        soup = BeautifulSoup(html, "lxml")
        meta = soup.find("meta", {"property": "article:published_time"})
        if meta and meta.get("content"):
            try:
                return datetime.fromisoformat(meta["content"].replace("Z", "+00:00"))
            except ValueError:
                return None
    except Exception:
        return None
    return None


def extract_document(
    fetch_result: FetchResult,
    source_type: SourceType,
    title_hint: Optional[str] = None,
) -> Optional[RetrievedDocument]:
    if fetch_result.status_code != 200:
        logger.debug("Skipping parse for %s due to status %s", fetch_result.url, fetch_result.status_code)
        return None
    downloaded = trafilatura.extract(
        fetch_result.content,
        url=fetch_result.metadata.get("fetch_url", fetch_result.url),
        include_images=False,
        include_comments=False,
        include_tables=False,
        no_fallback=True,
    )
    if not downloaded:
        logger.debug("Trafilatura extraction failed for %s, attempting plaintext fallback.", fetch_result.url)
        downloaded = _fallback_plain_text(fetch_result.content)
        if not downloaded:
            return None
    title = title_hint or _detect_title(fetch_result.content)
    if not title or title == "Untitled":
        # fall back to first sentence for social posts
        title = downloaded.strip().split("\n")[0][:120] or "Untitled"
    published_at = _detect_published_at(fetch_result.content)
    metadata = {
        "from_cache": fetch_result.from_cache,
        **fetch_result.metadata,
    }
    return RetrievedDocument(
        url=fetch_result.url,
        title=title,
        text=downloaded.strip(),
        raw_html=fetch_result.content,
        source_type=source_type,
        published_at=published_at,
        metadata=metadata,
    )


def _fallback_plain_text(content: str) -> Optional[str]:
    stripped = content.strip()
    if not stripped:
        return None
    soup = BeautifulSoup(content, "lxml")
    text = soup.get_text("\n", strip=True)
    if not text:
        text = stripped
    return text if text else None
