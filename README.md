# Mini-Perplexity ACE

Mini-Perplexity ACE is a focused research digester for the AI/ML ecosystem. It combines a ReAct + Self-Ask planner, web search, retrieval-augmented reading, and chain-of-density summarisation to produce citation-backed answers. An ACE loop (Generator -> Reflector -> Curator) continuously updates a structured playbook of heuristics so the system improves over time.

## Key Capabilities
- AI/ML niche awareness: planner query rewrites cover arXiv, GitHub, Hugging Face, analyst blogs, trusted news, and freshness-weighted Twitter/X plus Reddit streams.
- Two-stage retrieval: E5 embeddings for recall, BGE cross-encoder for precision, windowed snippets, and caching for latency.
- Cited synthesis: chain-of-density summariser emits up to seven bullets with inline `[n]` citations and a source list.
- AIS-style validation: ensures every bullet is attributable to sources; otherwise the reflector proposes corrective playbook items.
- ACE self-improvement: run metadata feeds the reflector, which emits playbook deltas that the curator merges deterministically into SQLite.
- Minimal web UI: FastAPI backend with a static "Mini Perplexity" front-end for quick testing.

## Directory Layout
```
mini-perplexity-ace/
├─ app/         FastAPI app + static UI
├─ core/        Planner, search, fetch, rank, synthesis, validation
├─ ace/         Self-improvement loop (playbook, reflector, curator)
├─ configs/     App + niche source configuration
├─ data/        Seed questions and evaluation hooks
├─ scripts/     Utilities for seeding the playbook and running evals
└─ README.md
```

## Getting Started
1. **Install dependencies**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. **Configure API keys**
   - Edit `configs/app.yaml` with your Brave Search key and OpenRouter key (sample keys are pre-filled for local testing).
   - Optionally customise `configs/niche_sources.yaml`.
3. **Seed the playbook**
   ```bash
   python scripts/backfill_playbook.py --db playbook.db
   ```
4. **Launch the API**
   ```bash
   uvicorn app.api:app --reload
   ```
   Visit `http://localhost:8000/ui/index.html` for the minimal interface.

## Usage Notes
- Query payload: POST `/answer` with JSON `{ "question": "...", "fresh_only": true, "max_sources": 6 }`.
- Playbook insights: GET `/ace/playbook` to inspect current heuristics.
- Evaluation loop: `python scripts/run_eval.py` runs through the seed questions and prints bullet digests.

## ACE Loop
1. **Generator** runs the full planner -> retriever -> synthesiser pipeline and logs traces.
2. **Reflector** inspects validation, freshness, and coverage to propose `PlaybookDelta` entries.
3. **Curator** deduplicates and merges deltas into the SQLite-backed playbook.

Each `/answer` call automatically triggers the reflector and curator, and annotates the response metadata with merged delta IDs.

## Extending the System
- Swap `BraveSearchProvider` with a custom provider by implementing `SearchProvider`.
- Add validators in `core/validate.py` (for example, hallucination scoring or redundancy checks).
- Create additional playbook item types by extending `ace/schemas.py`.
- Tie into dashboards by streaming `RunMetadata` objects to your analytics stack.

## Roadmap Ideas
- Background cron to auto-run weekly digests and publish to email or Substack.
- W&B or LangSmith tracing for richer experiments.
- Queue-based ingestion for higher throughput workloads.

Mini-Perplexity ACE is designed to be a practical, inspectable research assistant for teams shipping ML systems. Contributions and customisation are encouraged. Happy summarising!
