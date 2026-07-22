"""
Centralized backend configuration.
Paths, runtime constants, and environment variables are declared here.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# --- ENVIRONMENT LOADING ---
# Locate the project-root .env file two levels above app/.
_current_dir = Path(__file__).resolve().parent
_backend_dir = _current_dir.parent
_env_path = _backend_dir.parent / ".env"

if _env_path.exists():
    load_dotenv(dotenv_path=_env_path)

# --- DATA PATHS ---
# Resolve paths from the backend directory.
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "huggingface").strip().lower()
_embedding_artifact_suffix = (
    "" if EMBEDDING_PROVIDER == "huggingface" else f"_{EMBEDDING_PROVIDER}"
)

FAISS_INDEX_PATH = os.getenv(
    "FAISS_INDEX_PATH",
    str(_backend_dir / f"vietlaw_faiss_index{_embedding_artifact_suffix}"),
)
JSON_DATA_PATH = str(_backend_dir / "data" / "processed")
_corpus_jsonl_env = os.getenv("CORPUS_JSONL_PATH")
if _corpus_jsonl_env:
    _corpus_jsonl_path = Path(_corpus_jsonl_env)
    CORPUS_JSONL_PATH = str(
        _corpus_jsonl_path
        if _corpus_jsonl_path.is_absolute()
        else _backend_dir.parent / _corpus_jsonl_path
    )
else:
    CORPUS_JSONL_PATH = str(_backend_dir.parent / "corpus" / "processed" / "legal-corpus.jsonl")
CORPUS_EMBED_LEVELS = {
    level.strip().lower()
    for level in os.getenv("CORPUS_EMBED_LEVELS", "article,clause,point").split(",")
    if level.strip()
}
TRACKING_FILE = os.getenv(
    "EMBEDDED_FILES_PATH",
    str(_backend_dir / f"embedded_files{_embedding_artifact_suffix}.json"),
)

# --- API KEYS ---
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

# Native/Docker runs keep local models by default; Vercel can opt into the
# deployment-safe profile through its built-in environment marker.
_runtime_profile_env = os.getenv("RUNTIME_PROFILE", "").strip().lower()
RUNTIME_PROFILE = _runtime_profile_env or (
    "serverless" if os.getenv("VERCEL") or os.getenv("VERCEL_ENV") else "local"
)
SUPPORTED_RUNTIME_PROFILES = frozenset({"local", "serverless"})

# Conversation storage is intentionally separate from STORAGE_BACKEND:
# PostgreSQL/Qdrant may remain shared for the legal corpus while chat data is
# kept in the user's browser.
CHAT_STORAGE_MODE = os.getenv("CHAT_STORAGE_MODE", "postgres").strip().lower()
FRONTEND_CHAT_STORAGE_MODE = os.getenv("NEXT_PUBLIC_CHAT_STORAGE_MODE", "").strip().lower()
SUPPORTED_CHAT_STORAGE_MODES = frozenset({"postgres", "browser"})

# --- STORAGE BACKEND ---
STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "faiss").strip().lower()
POSTGRES_DSN = os.getenv("POSTGRES_DSN", "postgresql://postgres:postgres@localhost:5432/vietlaw")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "vietlaw_clauses")
QDRANT_TIMEOUT = float(os.getenv("QDRANT_TIMEOUT", "120"))
QDRANT_MAX_RETRIES = int(os.getenv("QDRANT_MAX_RETRIES", "5"))
QDRANT_UPSERT_BATCH_SIZE = int(os.getenv("QDRANT_UPSERT_BATCH_SIZE", "64"))
DISABLE_AUTO_INGEST = os.getenv("DISABLE_AUTO_INGEST", "false").strip().lower() == "true"
ENABLE_FAISS_FALLBACK = os.getenv("ENABLE_FAISS_FALLBACK", "false").strip().lower() == "true"
PIPELINE_TIMING_ENABLED = os.getenv("PIPELINE_TIMING_ENABLED", "false").strip().lower() == "true"

# --- THÔNG SỐ EMBEDDING ---
DEFAULT_LOCAL_EMBEDDING_MODEL = "../models/embedding/vietlaw-bge-m3-finetuned/best"
DEFAULT_LOCAL_RERANKER_MODEL = "../models/reranking/vietlaw-bge-reranker-v2-m3-finetuned/selected"

DEFAULT_REMOTE_EMBEDDING_MODEL = "BAAI/bge-m3"

_default_embedding_mode = "api" if RUNTIME_PROFILE == "serverless" else "local"
HUGGINGFACE_EMBEDDING_MODE = os.getenv(
    "HUGGINGFACE_EMBEDDING_MODE",
    _default_embedding_mode,
).strip().lower()
_default_embedding_model = (
    DEFAULT_REMOTE_EMBEDDING_MODEL
    if HUGGINGFACE_EMBEDDING_MODE == "api"
    else DEFAULT_LOCAL_EMBEDDING_MODEL
)
EMBEDDING_MODEL = os.getenv("HUGGINGFACE_EMBEDDING_MODEL", _default_embedding_model)
# Supported values: "api" or "local".
EMBEDDING_DEVICE = os.getenv("EMBEDDING_DEVICE", "cpu").strip()
EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "1024"))
EMBEDDING_NORMALIZE = os.getenv("EMBEDDING_NORMALIZE", "true").strip().lower() == "true"
LOCAL_MODELS_OFFLINE = os.getenv("LOCAL_MODELS_OFFLINE", "true").strip().lower() == "true"
_local_preload_requested = os.getenv("LOCAL_MODELS_PRELOAD_ENABLED", "true").strip().lower() == "true"
_local_warmup_requested = os.getenv("LOCAL_MODELS_WARMUP_ENABLED", "true").strip().lower() == "true"
LOCAL_MODELS_PRELOAD_ENABLED = _local_preload_requested and RUNTIME_PROFILE == "local"
LOCAL_MODELS_WARMUP_ENABLED = _local_warmup_requested and RUNTIME_PROFILE == "local"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "bge-m3")
OLLAMA_EMBEDDING_TIMEOUT = float(os.getenv("OLLAMA_EMBEDDING_TIMEOUT", "300"))
EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "32"))
EMBEDDING_MAX_RETRIES = int(os.getenv("EMBEDDING_MAX_RETRIES", "3"))
EMBEDDING_SLEEP_BETWEEN_BATCHES = float(os.getenv(
    "EMBEDDING_SLEEP_BETWEEN_BATCHES",
    "0" if EMBEDDING_PROVIDER == "ollama" else "5",
))
EMBEDDING_RETRY_BASE_WAIT = float(os.getenv(
    "EMBEDDING_RETRY_BASE_WAIT",
    "2" if EMBEDDING_PROVIDER == "ollama" else "15",
))

# --- THÔNG SỐ RETRIEVAL ---
RETRIEVER_K = 5
RETRIEVER_CANDIDATE_K = int(os.getenv("RETRIEVER_CANDIDATE_K", "10"))
RETRIEVER_FETCH_K = 20
RETRIEVER_LAMBDA_MULT = 0.8

# --- THÔNG SỐ LLM ---
LLM_MAX_NEW_TOKENS = 1500
LLM_TEMPERATURE = 0.1
LLM_REPETITION_PENALTY = 1.0
LLM_TIMEOUT = 300
ENABLE_GOOGLE_FALLBACK = os.getenv("ENABLE_GOOGLE_FALLBACK", "false").strip().lower() == "true"
GOOGLE_FALLBACK_MODEL = os.getenv("GOOGLE_FALLBACK_MODEL", "gemini-3.1-flash-lite").strip()
GOOGLE_OPENAI_BASE_URL = os.getenv(
    "GOOGLE_OPENAI_BASE_URL",
    "https://generativelanguage.googleapis.com/v1beta/openai/",
).strip()

# --- CORS ---
CORS_ORIGINS = ["*"]

# ---------------------------------------------------------------------------
# PIPELINE CONFIG
# ---------------------------------------------------------------------------
# Each key selects the corresponding strategy. See each module for the
# supported strategy list.
#
# Example ablation experiments:
#   Baseline:  search="faiss",  reranking="none"
#   +Reranker: search="faiss",  reranking="cross_encoder"
#   Hybrid:    search="hybrid", reranking="none"
#   Full:      search="hybrid", reranking="cross_encoder"
# ---------------------------------------------------------------------------
PIPELINE_CONFIG = {
    # Chunking: "clause" (one legal clause per chunk).
    "chunking": os.getenv("PIPELINE_CHUNKING", "clause"),

    # Search: "faiss" | "bm25" | "hybrid"
    "search": os.getenv("PIPELINE_SEARCH", "faiss"),

    # Reranking: "none" | "cross_encoder" | "embedding_similarity"
    "reranking": os.getenv(
        "PIPELINE_RERANKING",
        "embedding_similarity" if RUNTIME_PROFILE == "serverless" else "none",
    ).strip().lower(),

    # Context builder: "nested"
    "context_builder": os.getenv("PIPELINE_CONTEXT_BUILDER", "nested"),

    # --- Hybrid search weights, used only when search="hybrid". ---
    "hybrid_vector_weight": float(os.getenv("HYBRID_VECTOR_WEIGHT", "0.5")),
    "hybrid_bm25_weight": float(os.getenv("HYBRID_BM25_WEIGHT", "0.5")),

    # --- Reranker model, used only when reranking="cross_encoder". ---
    "reranker_model": os.getenv("RERANKER_MODEL", DEFAULT_LOCAL_RERANKER_MODEL),
    "reranker_max_candidates": int(os.getenv("RERANKER_MAX_CANDIDATES", "10")),
    "reranker_device": os.getenv("RERANKER_DEVICE", "cpu").strip(),
    "reranker_batch_size": int(os.getenv("RERANKER_BATCH_SIZE", "8")),
    "reranker_max_length": int(os.getenv("RERANKER_MAX_LENGTH", "512")),
    "reranker_fail_open": os.getenv("RERANKER_FAIL_OPEN", "false").strip().lower() == "true",

    # --- Query Rewriter ---
    "rewriter": os.getenv("PIPELINE_REWRITER", "none"),
    "rewriter_model_provider": os.getenv("REWRITER_MODEL_PROVIDER", "ollama"),
    "rewriter_model_name": os.getenv("REWRITER_MODEL_NAME", "qwen2.5:1.5b"),
}

# --- SEMANTIC CACHE ---
ENABLE_SEMANTIC_CACHE = os.getenv("ENABLE_SEMANTIC_CACHE", "true").strip().lower() == "true"
SEMANTIC_CACHE_THRESHOLD = float(os.getenv("SEMANTIC_CACHE_THRESHOLD", "0.95"))
SEMANTIC_CACHE_COLLECTION = os.getenv("SEMANTIC_CACHE_COLLECTION", "semantic_cache")

# --- FALLBACK STRATEGY ---
INFERENCE_STRATEGY = os.getenv("INFERENCE_STRATEGY", "remote_first").strip().lower()


def validate_runtime_configuration() -> None:
    """Validate profile/provider combinations without loading model weights."""
    if CHAT_STORAGE_MODE not in SUPPORTED_CHAT_STORAGE_MODES:
        raise ValueError(
            f"CHAT_STORAGE_MODE must be one of {sorted(SUPPORTED_CHAT_STORAGE_MODES)}; "
            f"got {CHAT_STORAGE_MODE!r}."
        )
    if FRONTEND_CHAT_STORAGE_MODE and FRONTEND_CHAT_STORAGE_MODE not in SUPPORTED_CHAT_STORAGE_MODES:
        raise ValueError(
            "NEXT_PUBLIC_CHAT_STORAGE_MODE must be one of "
            f"{sorted(SUPPORTED_CHAT_STORAGE_MODES)}; got {FRONTEND_CHAT_STORAGE_MODE!r}."
        )
    if FRONTEND_CHAT_STORAGE_MODE and FRONTEND_CHAT_STORAGE_MODE != CHAT_STORAGE_MODE:
        raise ValueError(
            "CHAT_STORAGE_MODE and NEXT_PUBLIC_CHAT_STORAGE_MODE must match."
        )
    if RUNTIME_PROFILE not in SUPPORTED_RUNTIME_PROFILES:
        raise ValueError(
            f"RUNTIME_PROFILE must be one of {sorted(SUPPORTED_RUNTIME_PROFILES)}; "
            f"got {RUNTIME_PROFILE!r}."
        )
    if HUGGINGFACE_EMBEDDING_MODE not in {"api", "local"}:
        raise ValueError("HUGGINGFACE_EMBEDDING_MODE must be either 'api' or 'local'.")
    if RUNTIME_PROFILE == "serverless" and HUGGINGFACE_EMBEDDING_MODE != "api":
        raise ValueError("RUNTIME_PROFILE=serverless requires HUGGINGFACE_EMBEDDING_MODE=api.")
    if RUNTIME_PROFILE == "local" and HUGGINGFACE_EMBEDDING_MODE != "local":
        raise ValueError("RUNTIME_PROFILE=local requires HUGGINGFACE_EMBEDDING_MODE=local.")
    if RUNTIME_PROFILE == "local" and (
        not Path(EMBEDDING_MODEL).is_absolute()
        and not EMBEDDING_MODEL.startswith((".", "~"))
    ):
        raise ValueError(
            "Local embedding mode requires HUGGINGFACE_EMBEDDING_MODEL to be a filesystem path."
        )
    if RUNTIME_PROFILE == "serverless" and (
        Path(EMBEDDING_MODEL).is_absolute()
        or EMBEDDING_MODEL.startswith((".", "~"))
    ):
        raise ValueError(
            "Serverless embedding mode requires HUGGINGFACE_EMBEDDING_MODEL to be a Hub model id."
        )
    if RUNTIME_PROFILE == "local" and PIPELINE_CONFIG["reranking"] in {
        "embedding_similarity",
        "remote_embedding_similarity",
    }:
        raise ValueError(
            "Local runtime must use cross_encoder or none for reranking."
        )


def runtime_profile_summary() -> dict:
    """Return safe profile diagnostics for readiness and startup logs."""
    return {
        "profile": RUNTIME_PROFILE,
        "chatStorageMode": CHAT_STORAGE_MODE,
        "frontendChatStorageMode": FRONTEND_CHAT_STORAGE_MODE or None,
        "embeddingMode": HUGGINGFACE_EMBEDDING_MODE,
        "embeddingModel": EMBEDDING_MODEL,
        "reranking": PIPELINE_CONFIG["reranking"],
        "localModelsPreload": LOCAL_MODELS_PRELOAD_ENABLED,
    }


def _validate_positive_int(name: str, value: int) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be greater than 0; got {value}.")


def _validate_non_empty(name: str, value: str) -> None:
    if not value.strip():
        raise ValueError(f"{name} must not be empty.")


_validate_positive_int("EMBEDDING_BATCH_SIZE", EMBEDDING_BATCH_SIZE)
_validate_positive_int("EMBEDDING_DIMENSION", EMBEDDING_DIMENSION)
_validate_positive_int("QDRANT_MAX_RETRIES", QDRANT_MAX_RETRIES)
_validate_positive_int("QDRANT_UPSERT_BATCH_SIZE", QDRANT_UPSERT_BATCH_SIZE)
_validate_positive_int("RERANKER_BATCH_SIZE", PIPELINE_CONFIG["reranker_batch_size"])
_validate_positive_int("RERANKER_MAX_LENGTH", PIPELINE_CONFIG["reranker_max_length"])
_validate_non_empty("QDRANT_COLLECTION", QDRANT_COLLECTION)
_validate_non_empty("SEMANTIC_CACHE_COLLECTION", SEMANTIC_CACHE_COLLECTION)
