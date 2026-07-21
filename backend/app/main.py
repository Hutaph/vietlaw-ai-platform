"""
Điểm vào chính của backend — FastAPI Application Factory.
File này chỉ chịu trách nhiệm:
  1. Tạo FastAPI app
  2. Đăng ký middleware
  3. Đăng ký routers
  4. Khởi tạo RAG Pipeline khi startup
"""
import asyncio
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import (
    CHAT_STORAGE_MODE,
    CORS_ORIGINS,
    EMBEDDING_DIMENSION,
    EMBEDDING_MODEL,
    HUGGINGFACE_API_KEY,
    LOCAL_MODELS_PRELOAD_ENABLED,
    LOCAL_MODELS_WARMUP_ENABLED,
    PIPELINE_CONFIG,
    POSTGRES_DSN,
    QDRANT_API_KEY,
    QDRANT_COLLECTION,
    QDRANT_URL,
    RUNTIME_PROFILE,
    runtime_profile_summary,
    validate_runtime_configuration,
)
from app.api.chat import router as chat_router
from app.api.documents import router as documents_router
from app.api.admin import router as admin_router
from app.api.feedback import router as feedback_router
from app.services.pipeline import init_pipeline, preload_local_models
from app.services.knowledge_base import load_knowledge_base
from app.services.storage import initialize_storage
from app.utils.logging import setup_logger

logger = setup_logger("vietlaw.main")


def _chat_storage_diagnostics() -> dict:
    if CHAT_STORAGE_MODE == "postgres":
        return {
            "mode": "postgres",
            "scope": "shared",
            "warning": (
                "Chat sessions and feedback are shared across users because "
                "authentication/row ownership is not configured."
            ),
        }
    return {
        "mode": "browser",
        "scope": "browser-local",
        "warning": None,
    }


def _resolve_runtime_path(path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return (Path(__file__).resolve().parents[1] / path).resolve()


def _check_artifacts() -> dict:
    validate_runtime_configuration()
    if RUNTIME_PROFILE == "serverless":
        return {
            "embedding": {
                "status": "ok" if HUGGINGFACE_API_KEY else "configured",
                "configured": bool(EMBEDDING_MODEL),
                "mode": "api",
                "weights": False,
            },
            "reranker": {
                "status": "ok",
                "enabled": PIPELINE_CONFIG.get("reranking") not in {"none", ""},
                "mode": "remote",
                "weights": False,
            },
        }

    embedding_path = _resolve_runtime_path(EMBEDDING_MODEL)
    embedding_ok = embedding_path.exists() and (embedding_path / "model.safetensors").exists()

    reranker_strategy = PIPELINE_CONFIG.get("reranking", "none")
    reranker_required = reranker_strategy == "cross_encoder"
    reranker_model = PIPELINE_CONFIG.get("reranker_model", "")
    reranker_path = _resolve_runtime_path(reranker_model) if reranker_model else Path("")
    reranker_ok = (
        not reranker_required
        or (reranker_path.exists() and (reranker_path / "model.safetensors").exists())
    )

    return {
        "embedding": {
            "status": "ok" if embedding_ok else "error",
            "configured": bool(EMBEDDING_MODEL),
            "mode": "local",
            "weights": embedding_ok,
        },
        "reranker": {
            "status": "ok" if reranker_ok else "error",
            "enabled": reranker_required,
            "weights": reranker_ok,
        },
    }


def _check_postgres() -> dict:
    try:
        import psycopg
    except Exception:  # pragma: no cover - compatibility fallback
        import psycopg2 as psycopg

    parsed = urlparse(POSTGRES_DSN)
    connect_kwargs = {}
    if psycopg.__name__ == "psycopg":
        connect_kwargs["connect_timeout"] = 3
        connect_kwargs["prepare_threshold"] = None

    conn = psycopg.connect(POSTGRES_DSN, **connect_kwargs)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
    finally:
        conn.close()

    return {
        "status": "ok",
        "host": parsed.hostname,
        "port": parsed.port,
        "database": (parsed.path or "").lstrip("/"),
    }


def _check_qdrant() -> dict:
    from qdrant_client import QdrantClient

    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY or None, timeout=5)
    info = client.get_collection(QDRANT_COLLECTION)
    vectors = info.config.params.vectors
    dense = vectors.get("text-dense") if isinstance(vectors, dict) else vectors
    dense_size = getattr(dense, "size", None)
    distance = str(getattr(dense, "distance", "")).split(".")[-1]
    if dense_size != EMBEDDING_DIMENSION:
        raise RuntimeError(
            f"Qdrant collection {QDRANT_COLLECTION} text-dense dimension is {dense_size}, expected {EMBEDDING_DIMENSION}."
        )

    parsed = urlparse(QDRANT_URL)
    return {
        "status": "ok",
        "host": parsed.hostname,
        "collection": QDRANT_COLLECTION,
        "points": getattr(info, "points_count", None),
        "denseVector": {"name": "text-dense", "dimension": dense_size, "distance": distance},
    }


def create_app() -> FastAPI:
    """Application factory — tạo và cấu hình FastAPI app."""
    application = FastAPI(title="VietLaw RAG Backend")

    # --- CORS Middleware ---
    application.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Đăng ký Routers ---
    application.include_router(chat_router)
    application.include_router(documents_router, prefix="/api/documents", tags=["Documents"])
    application.include_router(admin_router, prefix="/api/admin", tags=["Admin"])
    application.include_router(feedback_router, prefix="/api/feedback", tags=["Feedback"])

    @application.get("/health")
    async def health():
        return {"status": "ok"}

    @application.get("/readiness")
    async def readiness():
        components = {
            "config": {
                "status": "ok",
                **runtime_profile_summary(),
                "chatStorage": _chat_storage_diagnostics(),
            }
        }
        ready = True

        try:
            validate_runtime_configuration()
        except Exception as exc:
            ready = False
            components["config"] = {
                "status": "error",
                **runtime_profile_summary(),
                "chatStorage": _chat_storage_diagnostics(),
                "error": str(exc),
            }

        if LOCAL_MODELS_PRELOAD_ENABLED:
            local_models_ready = bool(getattr(application.state, "local_models_ready", False))
            local_models_error = getattr(application.state, "local_models_error", None)
            components["localModels"] = {
                "status": "ok" if local_models_ready else "error",
                "preload": True,
                "warmup": LOCAL_MODELS_WARMUP_ENABLED,
            }
            if local_models_error:
                components["localModels"]["error"] = local_models_error
            if not local_models_ready:
                ready = False

        try:
            components.update(await asyncio.to_thread(_check_artifacts))
        except Exception as exc:
            ready = False
            components["artifacts"] = {"status": "error", "error": type(exc).__name__}

        try:
            components["postgres"] = await asyncio.to_thread(_check_postgres)
        except Exception as exc:
            ready = False
            components["postgres"] = {"status": "error", "error": type(exc).__name__}

        try:
            components["qdrant"] = await asyncio.to_thread(_check_qdrant)
        except Exception as exc:
            ready = False
            components["qdrant"] = {"status": "error", "error": type(exc).__name__}

        response = {"status": "ready" if ready else "not_ready", "components": components}
        if not ready:
            raise HTTPException(status_code=503, detail=response)
        return response

    def _initialize_runtime_components_sync() -> None:
        application.state.local_models_ready = not LOCAL_MODELS_PRELOAD_ENABLED
        application.state.local_models_error = None
        try:
            validate_runtime_configuration()
        except Exception as exc:
            application.state.runtime_config_error = str(exc)
            logger.error("Runtime configuration validation failed: %s", exc)
            return
        application.state.runtime_config_error = None
        logger.info("Khởi tạo storage layer...")
        try:
            initialize_storage()
        except Exception as e:
            logger.warning("Không thể khởi tạo storage layer DB-backed: %s", str(e))

        logger.info("Khởi tạo RAG Pipeline...")
        try:
            init_pipeline()
            logger.info("RAG Pipeline đã sẵn sàng!")
        except Exception as e:
            logger.error("Lỗi khởi tạo RAG Pipeline: %s", str(e))
            logger.warning("Backend sẽ tiếp tục chạy ở chế độ degraded; API có thể dùng fallback retrieval.")
            if LOCAL_MODELS_PRELOAD_ENABLED:
                application.state.local_models_error = type(e).__name__
            return

        if LOCAL_MODELS_PRELOAD_ENABLED:
            import json
            import time

            start = time.perf_counter()
            outcome = "success"
            timings = {}
            try:
                timings = preload_local_models(warmup=LOCAL_MODELS_WARMUP_ENABLED)
                application.state.local_models_ready = True
            except Exception as exc:
                outcome = "error"
                application.state.local_models_ready = False
                application.state.local_models_error = type(exc).__name__
                logger.error("Local model preload failed: %s", type(exc).__name__)
            finally:
                timings["total_elapsed_ms"] = (time.perf_counter() - start) * 1000
                logger.info(json.dumps({
                    "event": "local_models_startup",
                    "preload_enabled": LOCAL_MODELS_PRELOAD_ENABLED,
                    "warmup_enabled": LOCAL_MODELS_WARMUP_ENABLED,
                    "outcome": outcome,
                    "durations_ms": {key: round(value, 3) for key, value in timings.items()},
                }, ensure_ascii=False, sort_keys=True))

    # --- Startup Event ---
    @application.on_event("startup")
    async def startup_event():
        """Load document metadata before serving requests, then initialize heavy services."""
        application.state.local_models_ready = not LOCAL_MODELS_PRELOAD_ENABLED
        application.state.local_models_error = None
        application.state.runtime_config_error = None
        if CHAT_STORAGE_MODE == "postgres":
            logger.warning(
                "CHAT_STORAGE_MODE=postgres uses shared unauthenticated conversation storage."
            )
        await asyncio.to_thread(load_knowledge_base)
        asyncio.create_task(asyncio.to_thread(_initialize_runtime_components_sync))
        logger.info("Document metadata loaded; remaining initialization scheduled in background")

    return application


# Tạo app instance
app = create_app()

# --- KHỞI CHẠY SERVER ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
