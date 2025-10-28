from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl


class SourceType(str, Enum):
    """Supported source buckets."""

    ARXIV = "arxiv"
    GITHUB = "github"
    HUGGINGFACE = "huggingface"
    NEWS = "news"
    BLOG = "blogs"
    TWITTER = "twitter"
    REDDIT = "reddit"
    OTHER = "other"


class QueryRequest(BaseModel):
    """Incoming request to the QA pipeline."""

    question: str = Field(..., min_length=4, description="Natural language question.")
    fresh_only: bool = Field(
        default=False,
        description="If true, only include sources within the configured freshness window.",
    )
    max_sources: int = Field(
        default=8,
        ge=1,
        le=20,
        description="Maximum number of unique sources to retrieve.",
    )
    include_playbook: bool = Field(
        default=True,
        description="Whether to enrich reasoning with ACE playbook guidance.",
    )


class SearchQuery(BaseModel):
    """Planner produced search query."""

    query: str
    source_type: SourceType = SourceType.OTHER
    rationale: str = ""
    freshness_days: Optional[int] = None


class PlannerStep(BaseModel):
    """Reasoning and actions taken by the planner."""

    thought: str
    search_queries: List[SearchQuery] = Field(default_factory=list)
    follow_up: Optional[str] = None


class SearchResult(BaseModel):
    """SERP result entry."""

    url: HttpUrl
    title: str
    snippet: str = ""
    score: float = 0.0
    source_type: SourceType = SourceType.OTHER
    published_at: Optional[datetime] = None


class RetrievedDocument(BaseModel):
    """Fetched and parsed document."""

    url: HttpUrl
    title: str
    text: str
    source_type: SourceType
    published_at: Optional[datetime] = None
    raw_html: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentChunk(BaseModel):
    """Chunked and ranked snippet from a document."""

    id: str
    url: HttpUrl
    title: str
    text: str
    score: float
    source_type: SourceType
    published_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Citation(BaseModel):
    """Citation metadata for synthesized answers."""

    label: str
    url: HttpUrl
    title: str
    source_type: SourceType
    published_at: Optional[datetime] = None


class AnswerBullet(BaseModel):
    """Single bullet in the final answer."""

    text: str
    citations: List[str] = Field(default_factory=list, description="Citation labels.")


class AnswerResponse(BaseModel):
    """Primary API response."""

    question: str
    bullets: List[AnswerBullet]
    sources: List[Citation]
    run_id: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ValidationIssueSeverity(str, Enum):
    WARNING = "warning"
    ERROR = "error"


class ValidationIssue(BaseModel):
    """Single validation warning/issue."""

    message: str
    severity: ValidationIssueSeverity = ValidationIssueSeverity.WARNING
    bullet_index: Optional[int] = None
    citation_label: Optional[str] = None


class ValidationReport(BaseModel):
    """Result of AIS-style validation."""

    passed: bool
    coverage: float
    issues: List[ValidationIssue] = Field(default_factory=list)


class RunMetadata(BaseModel):
    """Telemetry emitted by the pipeline for ACE."""

    run_id: str
    question: str
    planner_steps: List[PlannerStep] = Field(default_factory=list)
    search_results: List[SearchResult] = Field(default_factory=list)
    fetched_documents: List[RetrievedDocument] = Field(default_factory=list)
    selected_chunks: List[DocumentChunk] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)
    validator_report: Optional[ValidationReport] = None
    extra: Dict[str, Any] = Field(default_factory=dict)
