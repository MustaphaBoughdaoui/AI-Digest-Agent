"""Run evaluation queries against the Mini-Perplexity pipeline."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Ensure project root is on sys.path when executed via `python scripts/...`
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ace.generator import Generator
from core.types import QueryRequest


async def run_eval(seeds_path: str) -> None:
    generator = Generator()
    questions = json.loads(Path(seeds_path).read_text(encoding="utf-8"))
    for question in questions:
        request = QueryRequest(question=question, fresh_only=True, max_sources=6)
        answer, metadata = await generator.answer(request)
        print("===")
        print(question)
        print("\n".join(f"- {bullet.text}" for bullet in answer.bullets))
        print("Coverage:", metadata.validator_report.coverage if metadata.validator_report else "n/a")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run evaluation set.")
    parser.add_argument("--seeds", default="data/seeds/questions.json", help="Path to questions JSON.")
    args = parser.parse_args()
    asyncio.run(run_eval(args.seeds))
