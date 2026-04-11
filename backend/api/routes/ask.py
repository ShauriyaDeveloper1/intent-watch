from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from api import rag


router = APIRouter()


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=5000)
    k: int | None = Field(default=5, ge=1, le=12)
    max_alerts: int | None = Field(default=1000, ge=50, le=2000)


@router.post("/ask")
def ask(req: AskRequest):
    # Pull alerts from the in-memory store.
    try:
        from api.routes.alerts import alerts, alerts_lock
    except Exception:
        alerts = []
        alerts_lock = None

    max_alerts = int(req.max_alerts or 1000)
    if alerts_lock is None:
        snapshot = []
    else:
        with alerts_lock:
            snapshot = list(alerts[-max_alerts:]) if alerts else []

    answer, sources = rag.answer_question(snapshot, req.question, k=int(req.k or 5))

    return {
        "answer": answer,
        "sources": [
            {
                "id": s.id,
                "type": s.type,
                "message": s.message,
                "timestamp": s.timestamp,
                "severity": s.severity,
                "camera": s.camera,
                "snapshot_url": s.snapshot_url,
            }
            for s in sources
        ],
    }
