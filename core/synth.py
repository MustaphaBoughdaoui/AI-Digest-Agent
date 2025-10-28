from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

from .llm import LLMClient, LLMClientFactory, LLMMessage
from .types import (
    AnswerBullet,
    AnswerResponse,
    Citation,
    DocumentChunk,
    QueryRequest,
    RunMetadata,
)

logger = logging.getLogger(__name__)


@dataclass
class SynthesizerConfig:
    llm_section: str = "synthesizer"
    max_bullets: int = 7
    min_bullets: int = 3


class Synthesizer:
    def __init__(self, config: SynthesizerConfig, llm_factory: LLMClientFactory):
        self.config = config
        self._llm: LLMClient = llm_factory.build(config.llm_section)

    async def synthesize(
        self,
        request: QueryRequest,
        chunks: Iterable[DocumentChunk],
        run_id: str,
    ) -> Tuple[AnswerResponse, RunMetadata]:
        chunk_list = list(chunks)
        if not chunk_list:
            raise ValueError("No supporting chunks available for synthesis.")

        citations = self._build_citations(chunk_list)
        context = self._build_context(chunk_list, citations)

        initial = await self._initial_summary(request.question, context)
        refined = await self._chain_of_density(request.question, context, initial)

        bullets = self._parse_bullets(refined)
        if not bullets:
            logger.warning("Synthesizer returned no bullets; generating fallback from top chunks.")
            bullets = self._fallback_bullets(chunk_list, citations)
        answer = AnswerResponse(
            question=request.question,
            bullets=bullets,
            sources=list(citations.values()),
            run_id=run_id,
            metadata={"raw_initial": initial, "raw_refined": refined},
        )
        metadata = RunMetadata(
            run_id=run_id,
            question=request.question,
            citations=list(citations.values()),
            extra={"synthesizer": {"initial_bullets": len(bullets), "usage": {}}},
        )
        return answer, metadata

    async def _initial_summary(self, question: str, context: str) -> str:
        messages = [
            LLMMessage(
                role="system",
                content=(
                    "You are an expert AI/ML research analyst. "
                    "Synthesize concise bullet points with precise inline citations."
                ),
            ),
            LLMMessage(
                role="user",
                content=(
                    f"Question: {question}\n\n"
                    "Context snippets:\n"
                    f"{context}\n\n"
                    "Write 3-7 bullets. Each bullet:\n"
                    "- contains exactly one primary claim enriched with metrics if available.\n"
                    "- includes citation tags like [1] referencing the snippet IDs.\n"
                    "- stays within two lines.\n"
                    "After the bullets, list Sources with titles and URLs."
                ),
            ),
        ]
        response = await self._llm.generate(messages, temperature=0.4, max_tokens=400)
        return response.content.strip()

    async def _chain_of_density(self, question: str, context: str, draft: str) -> str:
        messages = [
            LLMMessage(
                role="system",
                content=(
                    "You enhance AI research summaries using chain-of-density: "
                    "add missing entities, metrics, and comparisons without increasing length."
                ),
            ),
            LLMMessage(
                role="user",
                content=(
                    f"Question: {question}\n"
                    f"Context:\n{context}\n\n"
                    "Draft summary:\n"
                    f"{draft}\n\n"
                    "Improve density with the rules:\n"
                    "1. Preserve number of bullets.\n"
                    "2. Insert missing proper nouns, datasets, benchmarks, and license info.\n"
                    "3. Do not introduce information absent from the context.\n"
                    "Return the refined bullets and Sources list."
                ),
            ),
        ]
        response = await self._llm.generate(messages, temperature=0.3, max_tokens=400)
        return response.content.strip()

    def _parse_bullets(self, text: str) -> List[AnswerBullet]:
        bullet_lines: List[str] = []
        sources_started = False
        bullet_pattern = re.compile(r"^\d+[\).\s]")
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.lower().startswith("sources"):
                sources_started = True
                break
            if stripped.startswith(("-", "*", "•")) or bullet_pattern.match(stripped):
                cleaned = stripped.lstrip("-*• ").strip()
                cleaned = re.sub(r"^\d+[\).\s]+", "", cleaned).strip()
                bullet_lines.append(cleaned)
            else:
                if bullet_lines:
                    bullet_lines[-1] = bullet_lines[-1] + " " + stripped
        bullets: List[AnswerBullet] = []
        citation_pattern = re.compile(r"\[(\d+)\]")
        for line in bullet_lines:
            citations = citation_pattern.findall(line)
            bullets.append(AnswerBullet(text=line, citations=citations))
        return bullets

    def _build_citations(self, chunks: List[DocumentChunk]) -> Dict[str, Citation]:
        citations: Dict[str, Citation] = {}
        for chunk in chunks:
            if chunk.url in citations:
                continue
            label = str(len(citations) + 1)
            citations[chunk.url] = Citation(
                label=label,
                url=chunk.url,
                title=chunk.title,
                source_type=chunk.source_type,
                published_at=chunk.published_at,
            )
        return citations

    def _build_context(
        self,
        chunks: List[DocumentChunk],
        citations: Dict[str, Citation],
    ) -> str:
        lines = []
        for chunk in chunks:
            citation = citations[chunk.url]
            lines.append(
                f"[{citation.label}] {chunk.title} ({chunk.source_type.value})\n"
                f"URL: {chunk.url}\n"
                f"Snippet: {chunk.text}\n"
            )
        return "\n".join(lines)

    def _fallback_bullets(
        self,
        chunks: List[DocumentChunk],
        citations: Dict[str, Citation],
    ) -> List[AnswerBullet]:
        bullets: List[AnswerBullet] = []
        seen_urls = set()
        limit = max(self.config.min_bullets, min(self.config.max_bullets, len(citations)))
        for chunk in chunks:
            if chunk.url in seen_urls:
                continue
            seen_urls.add(chunk.url)
            citation = citations[chunk.url]
            snippet_sentence = chunk.text.strip().split(". ")[0].strip()
            snippet_sentence = snippet_sentence[:220]
            if not snippet_sentence:
                snippet_sentence = chunk.text.strip()[:220]
            bullet_text = f"{chunk.title}: {snippet_sentence} [{citation.label}]"
            bullets.append(AnswerBullet(text=bullet_text, citations=[citation.label]))
            if len(bullets) >= limit:
                break
        return bullets
