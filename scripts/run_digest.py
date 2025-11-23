"""Test the Daily Digest functionality."""

import asyncio
import sys
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ace.generator import Generator
from core.types import QueryRequest, SourceType

async def test_digest():
    print("Initializing Generator...")
    generator = Generator()
    
    question = "Give me a daily digest of the latest AI news and tricks"
    print(f"\nRunning query: {question}")
    
    request = QueryRequest(
        question=question,
        fresh_only=True,
        max_sources=8
    )
    
    try:
        answer, metadata = await generator.answer(request)
        
        if not answer.bullets:
             print("\n[WARNING] No bullets parsed. Raw LLM output:")
             print(metadata.extra.get("synthesizer", {}).get("raw_refined", "N/A"))

        print("\n=== Digest Output ===")
        for bullet in answer.bullets:
            print(f"- {bullet.text}")
            
        print("\n=== Sources Used ===")
        source_types = set()
        for source in answer.sources:
            print(f"- [{source.source_type}] {source.title}: {source.url}")
            source_types.add(source.source_type)
            
        print("\n=== Validation ===")
        print(f"Source Types Found: {source_types}")
        
        # Check if we hit the expected sources for a digest
        expected_types = {SourceType.TWITTER, SourceType.REDDIT, SourceType.NEWS}
        found_expected = source_types.intersection(expected_types)
        
        if found_expected:
            print(f"SUCCESS: Found expected source types: {found_expected}")
        else:
            print(f"WARNING: Did not find expected source types (Twitter, Reddit, News). Found: {source_types}")
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_digest())
