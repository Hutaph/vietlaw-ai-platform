import json
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.storage import is_database_backend_enabled, _ensure_schema, _connect_postgres
from app.config import CHAT_STORAGE_MODE
from app.utils.logging import setup_logger

logger = setup_logger("vietlaw.api.feedback")

router = APIRouter()

class FeedbackRequest(BaseModel):
    message_id: str
    session_id: str
    user_query: Optional[str] = None
    ai_response: Optional[str] = None
    context_used: Optional[Any] = None
    feedback_type: int  # 1 for up, -1 for down
    reason: Optional[str] = None
    comment: Optional[str] = None
    model_used: Optional[str] = None

@router.post("")
async def submit_feedback(request: FeedbackRequest):
    if CHAT_STORAGE_MODE == "browser":
        return {
            "status": "skipped",
            "storageMode": "browser",
            "message": "Feedback is kept in browser-local state and is not persisted server-side.",
        }
    if not is_database_backend_enabled():
        # Fallback or soft-fail if database is not configured.
        # We don't want to crash the UI just because Postgres isn't running.
        logger.info(f"Feedback received but database backend is disabled. Payload: {request.model_dump()}")
        return {"status": "skipped", "message": "Database backend not enabled."}

    try:
        import psycopg
    except ImportError:
        logger.error("psycopg is not installed.")
        raise HTTPException(status_code=500, detail="Database driver not available.")

    try:
        # Ensure schema exists (in case it wasn't initialized)
        _ensure_schema()
        
        with _connect_postgres(autocommit=True) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO chat_feedbacks (
                        message_id, session_id, user_query, ai_response, 
                        context_used, feedback_type, reason, comment, model_used
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (message_id) DO UPDATE SET
                        feedback_type = EXCLUDED.feedback_type,
                        reason = EXCLUDED.reason,
                        comment = EXCLUDED.comment
                    """,
                    (
                        request.message_id,
                        request.session_id,
                        request.user_query or "",
                        request.ai_response or "",
                        json.dumps(request.context_used) if request.context_used else None,
                        request.feedback_type,
                        request.reason,
                        request.comment,
                        request.model_used,
                    )
                )
        return {"status": "success"}
    except Exception as exc:
        logger.error(f"Error saving feedback: {exc}")
        # Return 200 OK with error state to prevent UI from showing a huge red toast for feedback failure
        return {"status": "error", "message": str(exc)}
