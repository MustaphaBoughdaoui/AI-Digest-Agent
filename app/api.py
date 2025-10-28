from __future__ import annotations

import logging
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from ace.curator import Curator
from ace.generator import Generator
from ace.playbook_store import PlaybookStore
from ace.reflector import Reflector
from ace.schemas import PlaybookItem
from core.logger import setup_logging
from core.types import AnswerResponse, QueryRequest

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="Mini-Perplexity ACE", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

store = PlaybookStore()
generator = Generator(store=store)
reflector = Reflector()
curator = Curator(store=store)

app.mount("/ui", StaticFiles(directory="app/ui"), name="ui")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/answer", response_model=AnswerResponse)
async def answer(request: QueryRequest) -> AnswerResponse:
    try:
        answer, metadata = await generator.answer(request)
    except Exception as exc:
        logger.exception("Pipeline execution failed.")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    deltas = reflector.critique(metadata)
    merged = curator.merge(deltas)
    answer.metadata["ace"] = {
        "deltas_proposed": [delta.item.id for delta in deltas],
        "deltas_merged": [item.id for item in merged],
    }
    return answer


@app.get("/ace/playbook", response_model=List[PlaybookItem])
async def list_playbook(tag: str | None = None) -> List[PlaybookItem]:
    return store.list_items(tag_filter=tag)
