from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Iterable, List, Optional

from .schemas import PlaybookCounter, PlaybookItem

logger = logging.getLogger(__name__)


class PlaybookStore:
    """SQLite-backed store for ACE playbook items."""

    def __init__(self, path: str = "playbook.db"):
        self.path = Path(path)
        self._ensure_tables()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_tables(self) -> None:
        conn = self._connect()
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS playbook_items (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    helpful INTEGER DEFAULT 0,
                    harmful INTEGER DEFAULT 0,
                    tags TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS counters (
                    key TEXT PRIMARY KEY,
                    value INTEGER NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            conn.commit()
        finally:
            conn.close()

    def upsert_item(self, item: PlaybookItem) -> None:
        logger.debug("Upserting playbook item %s", item.id)
        conn = self._connect()
        try:
            conn.execute(
                """
                INSERT INTO playbook_items (id, type, content, helpful, harmful, tags, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    type=excluded.type,
                    content=excluded.content,
                    helpful=excluded.helpful,
                    harmful=excluded.harmful,
                    tags=excluded.tags,
                    updated_at=excluded.updated_at
                """,
                (
                    item.id,
                    item.type.value,
                    item.content,
                    item.helpful,
                    item.harmful,
                    ",".join(item.tags),
                    item.created_at.isoformat(),
                    item.updated_at.isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def list_items(self, tag_filter: Optional[str] = None) -> List[PlaybookItem]:
        conn = self._connect()
        try:
            if tag_filter:
                rows = conn.execute(
                    "SELECT * FROM playbook_items WHERE tags LIKE ? ORDER BY helpful DESC",
                    (f"%{tag_filter}%",),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM playbook_items ORDER BY helpful DESC"
                ).fetchall()
            return [self._row_to_item(row) for row in rows]
        finally:
            conn.close()

    def search_by_keywords(self, keywords: Iterable[str], limit: int = 5) -> List[PlaybookItem]:
        conn = self._connect()
        try:
            keywords_list = list(keywords)
            if not keywords_list:
                return self.list_items()[:limit]
            placeholders = " OR ".join("content LIKE ?" for _ in keywords_list)
            query = f"SELECT * FROM playbook_items WHERE {placeholders} ORDER BY helpful DESC LIMIT ?"
            params = [f"%{kw}%" for kw in keywords_list] + [limit]
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_item(row) for row in rows]
        finally:
            conn.close()

    def record_counter(self, counter: PlaybookCounter) -> None:
        conn = self._connect()
        try:
            conn.execute(
                """
                INSERT INTO counters (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value=excluded.value,
                    updated_at=excluded.updated_at
                """,
                (counter.key, counter.value, counter.updated_at.isoformat()),
            )
            conn.commit()
        finally:
            conn.close()

    def _row_to_item(self, row: sqlite3.Row) -> PlaybookItem:
        return PlaybookItem(
            id=row["id"],
            type=row["type"],
            content=row["content"],
            helpful=row["helpful"],
            harmful=row["harmful"],
            tags=[tag for tag in row["tags"].split(",") if tag],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
