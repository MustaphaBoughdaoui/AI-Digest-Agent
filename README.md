# 🤖 AI Digest Agent

> An intelligent research assistant that delivers citation-backed answers through retrieval-augmented generation and self-improving ACE architecture.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-009688.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

AI Digest Agent is a sophisticated research digester specifically designed for the AI/ML ecosystem. It combines advanced planning algorithms (ReAct + Self-Ask), real-time web search, retrieval-augmented reading, and chain-of-density summarization to produce accurate, citation-backed answers. The system continuously improves through an **ACE loop** (Autonomous Cognitive Entity) that learns from each query.

---

## ✨ Key Features

### 🎯 Intelligent Query Planning
- **ReAct + Self-Ask planner** breaks down complex questions into targeted sub-queries
- **AI/ML niche awareness** with specialized source handling:
  - Academic papers (arXiv, research blogs)
  - Code repositories (GitHub, Hugging Face)
  - Community discussions (Reddit, X/Twitter)
  - Industry news and analyst reports
- **Freshness-weighted search** prioritizes recent content

### 🔍 Advanced Retrieval System
- **Two-stage ranking**: E5 embeddings for recall + BGE cross-encoder for precision
- **Windowed snippet extraction** for optimal context
- **Smart caching** reduces latency on repeated queries
- **Document chunking** with overlap for comprehensive coverage

### 📝 Citation-Backed Synthesis
- **Chain-of-density summarization** produces concise, information-dense answers
- **Inline citations** `[n]` for every claim
- **Automated validation** ensures all bullets are attributable to sources
- Up to 7 key insights per answer with full source transparency

### 🔄 Self-Improvement (ACE Loop)
- **Generator**: Executes the complete research pipeline
- **Reflector**: Analyzes run quality, identifies gaps in validation, freshness, and coverage
- **Curator**: Merges learnings into a SQLite-backed playbook
- System improves automatically with each query

### 🎨 Modern Web Interface
- Clean, minimal UI for quick testing
- Real-time answer streaming
- Source exploration and citation tracking
- FastAPI backend with CORS support

---

## 🏗️ Architecture

```
┌─────────────┐
│   User UI   │
└──────┬──────┘
       │
┌──────▼───────────────────────────────────────┐
│              FastAPI Server                   │
│  ┌──────────────────────────────────────┐   │
│  │           Pipeline Flow              │   │
│  │                                       │   │
│  │  1. Planner  →  Search Queries       │   │
│  │       ↓                               │   │
│  │  2. Search  →  Web Results           │   │
│  │       ↓                               │   │
│  │  3. Fetch   →  Documents             │   │
│  │       ↓                               │   │
│  │  4. Rank    →  Top Chunks            │   │
│  │       ↓                               │   │
│  │  5. Synth   →  Answer + Citations    │   │
│  │       ↓                               │   │
│  │  6. Validate → Quality Check         │   │
│  └──────────────────────────────────────┘   │
│                                              │
│  ┌──────────────────────────────────────┐   │
│  │         ACE Loop (Async)             │   │
│  │                                       │   │
│  │  Reflector  →  Analyze Quality       │   │
│  │       ↓                               │   │
│  │  Curator    →  Update Playbook       │   │
│  └──────────────────────────────────────┘   │
└──────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
AiDigestAgent/
├── app/                      # FastAPI application
│   ├── api.py               # Main API routes
│   └── ui/                  # Static web interface
│       ├── index.html
│       ├── main.js
│       └── styles.css
├── core/                     # Core pipeline components
│   ├── pipeline.py          # Main orchestrator
│   ├── planner.py           # Query planning & decomposition
│   ├── search.py            # Web search integration
│   ├── fetch.py             # Document fetching
│   ├── parse.py             # Content extraction
│   ├── chunks.py            # Text chunking
│   ├── rank.py              # Two-stage ranking
│   ├── synth.py             # Answer synthesis
│   ├── validate.py          # Citation validation
│   ├── llm.py               # LLM client factory
│   └── types.py             # Shared data models
├── ace/                      # ACE self-improvement loop
│   ├── generator.py         # Run generator
│   ├── reflector.py         # Quality analysis
│   ├── curator.py           # Playbook management
│   ├── playbook_store.py    # SQLite persistence
│   └── schemas.py           # ACE data models
├── configs/                  # Configuration files
│   ├── app.yaml             # Main app config (API keys, models)
│   ├── niche_sources.yaml   # Source type definitions
│   └── blocked_sites.yaml   # Site blocklist
├── scripts/                  # Utility scripts
│   ├── backfill_playbook.py # Initialize playbook
│   ├── run_digest.py        # CLI digest runner
│   └── run_eval.py          # Evaluation suite
├── data/
│   └── seeds/
│       └── questions.json   # Test questions
├── requirements.txt
├── start_server.bat         # Windows quick-start
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9 or higher
- Brave Search API key ([Get free key](https://brave.com/search/api/))
- OpenRouter API key ([Get free key](https://openrouter.ai/keys))

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/AiDigestAgent.git
   cd AiDigestAgent
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   
   # On Windows
   .venv\Scripts\activate
   
   # On macOS/Linux
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure API keys**
   
   Edit `configs/app.yaml` and add your API keys:
   ```yaml
   search:
     brave:
       api_key: "YOUR_BRAVE_API_KEY"
   
   models:
     planner:
       api_key: "YOUR_OPENROUTER_API_KEY"
     synthesizer:
       api_key: "YOUR_OPENROUTER_API_KEY"
     reflector:
       api_key: "YOUR_OPENROUTER_API_KEY"
   ```
   
   **Note**: The project uses `mistralai/devstral-2512:free` which is free on OpenRouter!

5. **Initialize the playbook** (optional but recommended)
   ```bash
   python scripts/backfill_playbook.py
   ```

6. **Start the server**
   
   **Windows**: Double-click `start_server.bat`
   
   **macOS/Linux**:
   ```bash
   python -m uvicorn app.api:app --host 127.0.0.1 --port 8000
   ```

7. **Open the UI**
   
   Navigate to: **http://127.0.0.1:8000/ui/index.html**

---

## 💡 Usage

### Web Interface

1. Open the UI at `http://127.0.0.1:8000/ui/index.html`
2. Type your question in the input field
3. Click "Search" and wait 30-40 seconds
4. Review the citation-backed answer with sources

### API

**Query endpoint:**
```bash
curl -X POST http://127.0.0.1:8000/answer \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the latest breakthroughs in large language models?",
    "fresh_only": true,
    "max_sources": 6
  }'
```

**Response format:**
```json
{
  "question": "What are the latest breakthroughs...",
  "bullets": [
    {
      "text": "Recent models achieve 95% accuracy on benchmarks [1][2]",
      "citations": [1, 2]
    }
  ],
  "sources": [
    {
      "id": 1,
      "title": "...",
      "url": "...",
      "snippet": "..."
    }
  ],
  "metadata": {
    "run_id": "...",
    "ace": {
      "deltas_proposed": [...],
      "deltas_merged": [...]
    }
  }
}
```

**Other endpoints:**
- `GET /health` - Health check
- `GET /ace/playbook` - Inspect learned heuristics
- `GET /ace/playbook?tag=validation` - Filter playbook by tag

### Command Line

Run a digest directly:
```bash
python scripts/run_digest.py "What are the latest AI safety research developments?"
```
*Edit the script to customize your question.*

Run evaluation on seed questions:
```bash
python scripts/run_eval.py
```

---

## ⚙️ Configuration

### Main Config (`configs/app.yaml`)

```yaml
environment: "development"
log_level: "INFO"
cache_dir: "./.cache"

search:
  provider: "brave"
  brave:
    max_results: 20

models:
  planner:
    provider: "openrouter"
    model: "mistralai/devstral-2512:free"
  embeddings:
    provider: "sentence_transformers"
    model: "intfloat/e5-large-v2"
  reranker:
    model: "BAAI/bge-reranker-base"

limits:
  max_sources: 8
  max_chunks: 40
  request_timeout_seconds: 20

freshness:
  default_days: 14
  enforce_source_window: true

validation:
  min_citation_coverage: 0.95
```

### Niche Sources (`configs/niche_sources.yaml`)

Define AI/ML-specific sources:
- Academic repositories (arXiv)
- Code platforms (GitHub, Hugging Face)
- Community discussions (Reddit, HackerNews)
- Analyst blogs and industry news

---

## 🧪 How the ACE Loop Works

Every query triggers the self-improvement cycle:

### 1. **Generator**
- Executes the full pipeline (plan → search → fetch → rank → synthesize)
- Collects detailed `RunMetadata` (timing, sources, validation scores)

### 2. **Reflector**
Analyzes the run and proposes improvements:
- **Validation checks**: Are all bullets properly cited?
- **Freshness checks**: Are sources recent enough?
- **Coverage checks**: Are all relevant source types represented?

Creates `PlaybookDelta` entries with rationale.

### 3. **Curator**
- Deduplicates similar playbook items
- Merges approved deltas into SQLite database
- Maintains helpful/harmful counters for future prioritization

### Continuous Learning
- Playbook insights guide future planner decisions
- System gets smarter with each query
- Inspect learnings via `/ace/playbook` endpoint

---

## 🔧 Extending the System

### Add a Custom Search Provider

```python
from core.search import SearchProvider

class MySearchProvider(SearchProvider):
    async def search(self, query: str) -> List[SearchResult]:
        # Your implementation
        pass

# In pipeline.py
def _build_search_provider(self):
    if provider_name == "mysearch":
        return MySearchProvider(...)
```

### Add Custom Validators

```python
# In core/validate.py
def validate_custom_rule(answer: AnswerResponse) -> ValidatorIssue:
    # Your validation logic
    pass
```

### Extend Playbook Item Types

```python
# In ace/schemas.py
class PlaybookItemType(str, Enum):
    VALIDATION_RULE = "validation_rule"
    CUSTOM_RULE = "custom_rule"  # Add your type
```

---

## 📊 Performance Optimization

The system includes several optimizations:

- **Parallel fetching** with connection pooling (30-40% faster)
- **Search result caching** (instant for repeated queries)
- **Lazy model loading** (2-3s faster startup)
- **Batch LLM calls** (1-2s saved per query)

---

## 🛠️ Tech Stack

- **Backend**: FastAPI, Uvicorn
- **LLM Integration**: OpenRouter API (free tier available)
- **Search**: Brave Search API
- **Embeddings**: Sentence Transformers (E5-large-v2)
- **Reranking**: BGE reranker
- **Content Extraction**: Trafilatura, BeautifulSoup, Readability
- **Database**: SQLite (via SQLAlchemy)
- **HTTP Client**: httpx (async)

---

## 📝 Common Issues

### ❌ 401 Unauthorized Error
- Make sure you've added valid API keys in `configs/app.yaml`
- Get your [Brave Search API key](https://brave.com/search/api/) and [OpenRouter API key](https://openrouter.ai/keys)

### ⚠️ Port 8000 Already in Use
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# macOS/Linux
lsof -ti:8000 | xargs kill -9
```

### 🐌 Slow First Query
- First query loads embedding/reranker models (~30-40s)
- Subsequent queries are much faster (~10-15s)
- Models are cached in memory

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Built with inspiration from Perplexity AI's citation-backed search
- ACE architecture inspired by autonomous agent research
- Uses state-of-the-art open models for embeddings and reranking

---

**Made with ❤️ for the AI/ML research community**
