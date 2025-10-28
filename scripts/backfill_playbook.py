"""Seed the ACE playbook with starter heuristics."""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Ensure project root is on sys.path when executed via `python scripts/...`
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ace.playbook_store import PlaybookStore
from ace.schemas import PlaybookItem, PlaybookItemType

DEFAULT_ITEMS = [
    PlaybookItem(
        id="query_rewrite:hf-new-models",
        type=PlaybookItemType.QUERY_REWRITE,
        content="huggingface:new models => sort:recent",
        helpful=5,
        harmful=0,
        tags=["models", "fresh"],
    ),
    PlaybookItem(
        id="source_rule:avoid-stale-medium",
        type=PlaybookItemType.SOURCE_RULE,
        content="Avoid medium.com posts older than 60 days unless explicitly requested.",
        helpful=3,
        harmful=0,
        tags=["blogs", "fresh"],
    ),
    PlaybookItem(
        id="template_rule:model-compare",
        type=PlaybookItemType.TEMPLATE_RULE,
        content="When comparing models, include parameter count, training data summary, benchmark score, and license line.",
        helpful=4,
        harmful=0,
        tags=["comparison", "models"],
    ),
    PlaybookItem(
        id="query_rewrite:twitter-latest-ai",
        type=PlaybookItemType.QUERY_REWRITE,
        content="twitter:latest => sort:recent",
        helpful=2,
        harmful=0,
        tags=["social", "fresh", "twitter"],
    ),
    PlaybookItem(
        id="query_rewrite:reddit-discussion",
        type=PlaybookItemType.QUERY_REWRITE,
        content="reddit:discussion => sort:recent",
        helpful=2,
        harmful=0,
        tags=["community", "reddit"],
    ),
]


def main(path: str) -> None:
    store = PlaybookStore(path)
    for item in DEFAULT_ITEMS:
        item.created_at = datetime.utcnow()
        item.updated_at = datetime.utcnow()
        store.upsert_item(item)
    print(f"Seeded {len(DEFAULT_ITEMS)} playbook items at {path}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed ACE playbook.")
    parser.add_argument("--db", default="playbook.db", help="Path to playbook sqlite database.")
    args = parser.parse_args()
    main(args.db)
