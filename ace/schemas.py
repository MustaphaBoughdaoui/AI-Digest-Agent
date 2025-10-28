from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class PlaybookItemType(str, Enum):
    QUERY_REWRITE = "query_rewrite"
    SOURCE_RULE = "source_rule"
    TEMPLATE_RULE = "template_rule"
    VALIDATION_RULE = "validation_rule"


class PlaybookItem(BaseModel):
    id: str
    type: PlaybookItemType
    content: str
    helpful: int = 0
    harmful: int = 0
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PlaybookCounter(BaseModel):
    key: str
    value: int = 0
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PlaybookDelta(BaseModel):
    item: PlaybookItem
    rationale: str
    run_id: str
