from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .config import settings
from .dashboard import router as dashboard_router
from .db import init_db
from .lead_sources import import_from_csv, import_from_database
from .workflow import (
    next_question_for_lead,
    process_followups,
    process_new_leads,
    register_inbound_response,
    send_email_for_in_qualification,
)


app = FastAPI(title=settings.app_name)
app.include_router(dashboard_router)
scheduler = AsyncIOScheduler()


class InboundPayload(BaseModel):
    lead_id: int
    message: str


class DbImportPayload(BaseModel):
    db_url: str
    query: str


@app.on_event('startup')
async def startup_event() -> None:
    init_db()
    scheduler.add_job(process_new_leads, 'interval', seconds=settings.poll_interval_seconds)
    scheduler.add_job(process_followups, 'interval', seconds=settings.poll_interval_seconds)
    scheduler.add_job(send_email_for_in_qualification, 'interval', seconds=settings.poll_interval_seconds)
    scheduler.start()


@app.on_event('shutdown')
async def shutdown_event() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)


@app.post('/ingest/csv')
def ingest_csv(path: str) -> dict:
    count = import_from_csv(path)
    return {'imported': count}


@app.post('/ingest/database')
def ingest_database(payload: DbImportPayload) -> dict:
    count = import_from_database(payload.query, payload.db_url)
    return {'imported': count}


@app.post('/webhook/inbound')
async def inbound(payload: InboundPayload) -> dict:
    classification = register_inbound_response(payload.lead_id, payload.message)
    if classification is None:
        raise HTTPException(status_code=404, detail='Lead não encontrado')

    question = next_question_for_lead(payload.lead_id)
    return {'classification': classification.value, 'next_question': question}


@app.get('/health')
def health() -> dict:
    return {'status': 'ok'}
