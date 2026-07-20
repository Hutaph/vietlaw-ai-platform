"""
Storage bootstrap for Qdrant + PostgreSQL-backed legal corpus persistence.

This module introduces a storage abstraction for the new backend while
preserving backward compatibility with the existing FAISS-based flow.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.config import (
    EMBEDDING_DIMENSION,
    EMBEDDING_PROVIDER,
    POSTGRES_DSN,
    CHAT_STORAGE_MODE,
    QDRANT_API_KEY,
    QDRANT_COLLECTION,
    QDRANT_URL,
    SEMANTIC_CACHE_COLLECTION,
    STORAGE_BACKEND,
)
from app.utils.logging import setup_logger

logger = setup_logger("vietlaw.storage")


def is_chat_persistence_enabled() -> bool:
    """Return whether user conversation data may be persisted server-side."""
    return CHAT_STORAGE_MODE == "postgres"


class StorageInitializationError(RuntimeError):
    """Raised when the database-backed storage layer cannot be initialized."""


def is_database_backend_enabled() -> bool:
    """Return True when the runtime is configured to use the database-backed storage layer."""
    return STORAGE_BACKEND.lower() in {"qdrant_postgres", "postgres", "postgresql", "qdrant"}


def _named_vector_size(collection_info, vector_name: str) -> Optional[int]:
    vectors = collection_info.config.params.vectors
    if isinstance(vectors, dict):
        vector_config = vectors.get(vector_name)
        return getattr(vector_config, "size", None) if vector_config is not None else None
    if vector_name == "":
        return getattr(vectors, "size", None)
    return None


def _ensure_collection_dimension(collection_info, collection_name: str, vector_name: str, expected_size: int) -> None:
    actual_size = _named_vector_size(collection_info, vector_name)
    if actual_size != expected_size:
        raise StorageInitializationError(
            f"Qdrant collection '{collection_name}' vector '{vector_name}' has dimension {actual_size}; "
            f"expected {expected_size}. Re-index the collection with the configured embedding model before use."
        )


def _ensure_schema() -> None:
    """Create the PostgreSQL schema used by the storage backend if it does not already exist."""
    try:
        import psycopg
    except ImportError as exc:  # pragma: no cover - runtime dependency check
        raise StorageInitializationError(
            "psycopg is required for database-backed storage. Install backend requirements first."
        ) from exc

    schema_statements = [
        """
        CREATE TABLE IF NOT EXISTS laws (
            law_id TEXT PRIMARY KEY,
            law_name TEXT NOT NULL,
            summary TEXT,
            category TEXT,
            metadata JSONB DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS clauses (
            id TEXT PRIMARY KEY,
            law_id TEXT NOT NULL REFERENCES laws(law_id) ON DELETE CASCADE,
            content TEXT NOT NULL,
            position JSONB DEFAULT '{}'::jsonb,
            cross_references JSONB DEFAULT '[]'::jsonb,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS indexing_runs (
            id SERIAL PRIMARY KEY,
            source TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            started_at TIMESTAMPTZ DEFAULT NOW(),
            finished_at TIMESTAMPTZ,
            details JSONB DEFAULT '{}'::jsonb
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS chat_feedbacks (
            id SERIAL PRIMARY KEY,
            message_id TEXT UNIQUE NOT NULL,
            session_id TEXT NOT NULL,
            user_query TEXT,
            ai_response TEXT,
            context_used JSONB,
            feedback_type SMALLINT NOT NULL,
            reason TEXT,
            comment TEXT,
            model_used TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS chat_sessions (
            session_id TEXT PRIMARY KEY,
            title TEXT NOT NULL DEFAULT 'Cuộc trò chuyện mới',
            summary TEXT NOT NULL DEFAULT '',
            turn_count INTEGER NOT NULL DEFAULT 0,
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS chat_messages (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            context_used JSONB DEFAULT '[]'::jsonb,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
        """,
        """
        ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS title TEXT NOT NULL DEFAULT 'Cuộc trò chuyện mới'
        """,
    ]

    with psycopg.connect(POSTGRES_DSN, autocommit=True) as conn:
        with conn.cursor() as cursor:
            for statement in schema_statements:
                cursor.execute(statement)


def _start_indexing_run(source: str, details: Optional[Dict[str, Any]] = None) -> Optional[int]:
    """Create a new indexing run record and return its id when PostgreSQL is available."""
    try:
        _ensure_schema()
        import psycopg
    except ImportError:  # pragma: no cover - runtime dependency check
        return None

    try:
        with psycopg.connect(POSTGRES_DSN, autocommit=True) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO indexing_runs (source, status, details)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (source, "running", json.dumps(details or {})),
                )
                row = cursor.fetchone()
                return int(row[0]) if row else None
    except Exception as exc:  # pragma: no cover - runtime dependency path
        logger.warning("Unable to create indexing run record for %s: %s", source, exc)
        return None


def _finish_indexing_run(
    run_id: Optional[int],
    status: str,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Update an existing indexing run record with a final status."""
    if run_id is None:
        return

    try:
        import psycopg
    except ImportError:  # pragma: no cover - runtime dependency check
        return

    try:
        with psycopg.connect(POSTGRES_DSN, autocommit=True) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE indexing_runs
                    SET status = %s,
                        finished_at = NOW(),
                        details = %s
                    WHERE id = %s
                    """,
                    (status, json.dumps(details or {}), run_id),
                )
    except Exception as exc:  # pragma: no cover - runtime dependency path
        logger.warning("Unable to update indexing run record %s: %s", run_id, exc)


def initialize_storage() -> Dict[str, Any]:
    """Initialize PostgreSQL schema and Qdrant collection if the DB backend is enabled.
    
    Skips re-ingestion if data already exists to avoid expensive re-embedding on every startup.
    """
    if not is_database_backend_enabled():
        logger.info("Storage backend %s requested; skipping DB initialization.", STORAGE_BACKEND)
        return {"backend": STORAGE_BACKEND, "postgres": "skipped", "qdrant": "skipped"}

    try:
        import psycopg
    except ImportError as exc:  # pragma: no cover - runtime dependency check
        raise StorageInitializationError(
            "psycopg is required for database-backed storage. Install backend requirements first."
        ) from exc

    try:
        from qdrant_client import QdrantClient
        from qdrant_client.http import models as qdrant_models
    except ImportError as exc:  # pragma: no cover - runtime dependency check
        raise StorageInitializationError(
            "qdrant-client is required for vector storage. Install backend requirements first."
        ) from exc

    _ensure_schema()
    
    try:
        with psycopg.connect(POSTGRES_DSN, autocommit=True) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM clauses")
                existing_clause_count = cursor.fetchone()[0]
                if existing_clause_count > 0:
                    logger.info("Database already contains %d clauses; checking Qdrant schema...", existing_clause_count)
    except Exception as exc:
        logger.warning("Could not check existing clause count: %s", exc)
        # Continue with initialization if check fails

    qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY or None)
    
    # Check if Qdrant collection exists before creating a new one. Existing
    # collections are never recreated here because that would delete index data.
    try:
        collection_info = qdrant_client.get_collection(QDRANT_COLLECTION)
        
        if not collection_info.config.params.sparse_vectors or "text-sparse" not in collection_info.config.params.sparse_vectors:
            raise StorageInitializationError(
                f"Qdrant collection '{QDRANT_COLLECTION}' lacks required sparse vector 'text-sparse'. "
                "Create a migrated collection and re-index before enabling this backend."
            )
        _ensure_collection_dimension(
            collection_info,
            QDRANT_COLLECTION,
            "text-dense",
            EMBEDDING_DIMENSION,
        )
            
        logger.info("Qdrant collection '%s' already exists with %d points and proper schema.", 
                    QDRANT_COLLECTION, collection_info.points_count)
    except StorageInitializationError:
        raise
    except Exception:
        # Collection doesn't exist or schema mismatch - create it
        logger.info("Creating new Qdrant collection '%s' with Named Vectors (text-dense and text-sparse)", QDRANT_COLLECTION)
        qdrant_client.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config={
                "": qdrant_models.VectorParams(size=1, distance=qdrant_models.Distance.COSINE), # Dummy default vector to bypass Qdrant FusionQuery validation bug
                "text-dense": qdrant_models.VectorParams(size=EMBEDDING_DIMENSION, distance=qdrant_models.Distance.COSINE),
            },
            sparse_vectors_config={
                "text-sparse": qdrant_models.SparseVectorParams(),
            }
        )

    from app.config import ENABLE_SEMANTIC_CACHE
    if ENABLE_SEMANTIC_CACHE:
        cache_collection = SEMANTIC_CACHE_COLLECTION
        try:
            cache_info = qdrant_client.get_collection(cache_collection)
            _ensure_collection_dimension(
                cache_info,
                cache_collection,
                "",
                EMBEDDING_DIMENSION,
            )
            logger.info("Qdrant collection '%s' already exists.", cache_collection)
        except StorageInitializationError:
            raise
        except Exception:
            logger.info("Creating new Qdrant collection '%s'", cache_collection)
            qdrant_client.create_collection(
                collection_name=cache_collection,
                vectors_config=qdrant_models.VectorParams(size=EMBEDDING_DIMENSION, distance=qdrant_models.Distance.COSINE),
            )

    run_id = _start_indexing_run("startup", {"backend": STORAGE_BACKEND, "collection": QDRANT_COLLECTION})
    try:
        from app.config import DISABLE_AUTO_INGEST
        if DISABLE_AUTO_INGEST:
            logger.info("Auto ingestion on startup is disabled via DISABLE_AUTO_INGEST.")
            _finish_indexing_run(run_id, "skipped", {"backend": STORAGE_BACKEND, "reason": "auto_ingest_disabled"})
        else:
            ingested = ingest_json_documents()
            if ingested == 0:
                logger.info("No documents were ingested (either data exists or ingestion was skipped)")
                _finish_indexing_run(run_id, "skipped", {"backend": STORAGE_BACKEND, "reason": "data_exists"})
            else:
                _finish_indexing_run(run_id, "completed", {"backend": STORAGE_BACKEND, "collection": QDRANT_COLLECTION, "ingested": ingested})
                logger.info("Ingested %d documents on startup", ingested)
    except Exception as exc:  # pragma: no cover - runtime fallback path
        _finish_indexing_run(run_id, "failed", {"backend": STORAGE_BACKEND, "error": str(exc)})
        logger.warning("Initial document ingestion skipped: %s", exc)

    logger.info("Database-backed storage initialized: postgres=%s qdrant=%s", POSTGRES_DSN, QDRANT_COLLECTION)
    return {
        "backend": STORAGE_BACKEND,
        "postgres": "ready",
        "qdrant_collection": QDRANT_COLLECTION,
    }


def ingest_json_documents() -> int:
    """Ingest processed legal JSON documents into PostgreSQL and Qdrant using the configured embedding backend.
    
    Returns 0 if data already exists to avoid re-ingesting on every startup.
    Returns the number of records ingested (>0) if new data was added.
    """
    from app.services.knowledge_base import KNOWLEDGE_BASE, LAW_METADATA, load_knowledge_base

    load_knowledge_base()

    records: List[Dict[str, Any]] = []
    grouped: Dict[str, Dict[str, Any]] = {}

    for clause_id, clause_data in KNOWLEDGE_BASE.items():
        law_id = clause_data.get("law_id")
        law_meta = LAW_METADATA.get(law_id, {})
        record = grouped.setdefault(
            law_id,
            {
                "law_id": law_id,
                "law_name": law_meta.get("law_name", ""),
                "summary": law_meta.get("summary", ""),
                "category": law_meta.get("category", "all"),
                "metadata": {"law_name": law_meta.get("law_name", "")},
                "clauses": [],
            },
        )
        record["clauses"].append(
            {
                "id": clause_id,
                "content": clause_data.get("content", ""),
                "position": clause_data.get("position", {}),
                "cross_references": clause_data.get("cross_references", []),
            }
        )

    records = list(grouped.values())
    if not records:
        return 0

    # Check if clauses already exist before embedding
    try:
        import psycopg
        with psycopg.connect(POSTGRES_DSN, autocommit=True) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM clauses")
                existing_count = cursor.fetchone()[0]
                total_expected = sum(len(r.get("clauses", [])) for r in records)
                if existing_count >= total_expected:
                    logger.info("All %d clauses already exist in database; skipping re-ingestion", existing_count)
                    return 0
    except Exception as exc:
        logger.warning("Could not check existing clauses: %s; proceeding with ingestion", exc)

    try:
        if EMBEDDING_PROVIDER == "ollama":
            from app.services.embedding.ollama import OllamaEmbedding
            embedding_backend = OllamaEmbedding()
        else:
            from app.services.embedding.hf_endpoint import HuggingFaceEndpointEmbedding
            embedding_backend = HuggingFaceEndpointEmbedding()
    except Exception as exc:  # pragma: no cover - runtime dependency path
        logger.warning("Embedding backend unavailable during ingestion: %s", exc)
        embedding_backend = None

    try:
        from app.services.sparse_vector import SparseVectorGenerator
        sparse_generator = SparseVectorGenerator()
    except Exception as exc:
        logger.warning("SparseVectorGenerator unavailable: %s", exc)
        sparse_generator = None

    all_clauses = [clause for record in records for clause in record.get("clauses", []) if clause.get("content")]

    try:
        from tqdm import tqdm
        iterator = tqdm(all_clauses, desc="Embedding clauses", unit="clause")
    except ImportError:
        iterator = all_clauses

    for clause in iterator:
        content = clause.get("content", "")
        if content:
            if embedding_backend:
                try:
                    clause["embedding"] = embedding_backend.embed_query(content)
                except Exception as exc:  # pragma: no cover - runtime dependency path
                    logger.warning("Embedding failed for clause %s: %s", clause["id"], exc)
                    clause["embedding"] = None
                    
            if sparse_generator:
                try:
                    clause["sparse_embedding"] = sparse_generator.generate_sparse_vector(content)
                except Exception as exc:
                    logger.warning("Sparse embedding failed for clause %s: %s", clause["id"], exc)
                    clause["sparse_embedding"] = None

    return ingest_documents(records)


def ingest_documents(records: List[Dict[str, Any]]) -> int:
    """Persist legal document records into PostgreSQL and upsert vectors into Qdrant."""
    if not records:
        return 0

    if not is_database_backend_enabled():
        logger.info("Skipping ingestion because storage backend %s is not database-backed.", STORAGE_BACKEND)
        return 0

    try:
        import psycopg
    except ImportError as exc:  # pragma: no cover - runtime dependency check
        raise StorageInitializationError(
            "psycopg is required for database-backed storage. Install backend requirements first."
        ) from exc

    try:
        from qdrant_client import QdrantClient
        from qdrant_client.http import models as qdrant_models
    except ImportError as exc:  # pragma: no cover - runtime dependency check
        raise StorageInitializationError(
            "qdrant-client is required for vector storage. Install backend requirements first."
        ) from exc

    qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY or None)
    run_id = _start_indexing_run("ingest_documents", {"record_count": len(records), "backend": STORAGE_BACKEND})

    try:
        with psycopg.connect(POSTGRES_DSN, autocommit=True) as conn:
            with conn.cursor() as cursor:
                for record in records:
                    law_id = record["law_id"]
                    law_name = record.get("law_name", "")
                    summary = record.get("summary", "")
                    category = record.get("category", "all")
                    metadata = record.get("metadata", {})

                    cursor.execute(
                        """
                        INSERT INTO laws (law_id, law_name, summary, category, metadata)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (law_id) DO UPDATE SET
                            law_name = EXCLUDED.law_name,
                            summary = EXCLUDED.summary,
                            category = EXCLUDED.category,
                            metadata = EXCLUDED.metadata
                        """,
                        (law_id, law_name, summary, category, json.dumps(metadata)),
                    )

                    for clause in record.get("clauses", []):
                        clause_id = clause["id"]
                        cursor.execute(
                            """
                            INSERT INTO clauses (id, law_id, content, position, cross_references)
                            VALUES (%s, %s, %s, %s, %s)
                            ON CONFLICT (id) DO UPDATE SET
                                law_id = EXCLUDED.law_id,
                                content = EXCLUDED.content,
                                position = EXCLUDED.position,
                                cross_references = EXCLUDED.cross_references
                            """,
                            (
                                clause_id,
                                law_id,
                                clause.get("content", ""),
                                json.dumps(clause.get("position", {})),
                                json.dumps(clause.get("cross_references", [])),
                            ),
                        )

                        embedding = clause.get("embedding")
                        sparse_embedding = clause.get("sparse_embedding")
                        
                        if embedding:
                            import uuid
                            qdrant_id = str(uuid.uuid5(uuid.NAMESPACE_URL, clause_id))
                            
                            vector_dict = {"text-dense": embedding}
                            if sparse_embedding:
                                vector_dict["text-sparse"] = qdrant_models.SparseVector(
                                    indices=sparse_embedding["indices"],
                                    values=sparse_embedding["values"]
                                )
                                
                            qdrant_client.upsert(
                                collection_name=QDRANT_COLLECTION,
                                points=[
                                    qdrant_models.PointStruct(
                                        id=qdrant_id,
                                        vector=vector_dict,
                                        payload={
                                            "id": clause_id,
                                            "law_id": law_id,
                                            "content": clause.get("content", ""),
                                            "category": category,
                                        },
                                    )
                                ],
                            )

        _finish_indexing_run(run_id, "completed", {"record_count": len(records), "backend": STORAGE_BACKEND})
    except Exception as exc:
        _finish_indexing_run(run_id, "failed", {"record_count": len(records), "backend": STORAGE_BACKEND, "error": str(exc)})
        raise

    logger.info("Ingested %d document record(s) into database-backed storage.", len(records))
    return len(records)


def get_session_summary(session_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve the conversation summary and turn count for a given session."""
    if not is_chat_persistence_enabled():
        return None
    try:
        import psycopg
    except ImportError:
        return None

    try:
        with psycopg.connect(POSTGRES_DSN, autocommit=True) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT summary, turn_count FROM chat_sessions WHERE session_id = %s
                    """,
                    (session_id,)
                )
                row = cursor.fetchone()
                if row:
                    return {"summary": row[0], "turn_count": row[1]}
                return None
    except Exception as exc:
        logger.warning("Error fetching session summary for %s: %s", session_id, exc)
        return None


def upsert_session_summary(session_id: str, summary: str, turn_count: int) -> None:
    """Insert or update the session summary and turn count."""
    if not is_chat_persistence_enabled():
        return
    try:
        import psycopg
    except ImportError:
        return

    try:
        with psycopg.connect(POSTGRES_DSN, autocommit=True) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO chat_sessions (session_id, summary, turn_count, updated_at)
                    VALUES (%s, %s, %s, NOW())
                    ON CONFLICT (session_id) DO UPDATE SET
                        summary = EXCLUDED.summary,
                        turn_count = EXCLUDED.turn_count,
                        updated_at = EXCLUDED.updated_at
                    """,
                    (session_id, summary, turn_count)
                )
    except Exception as exc:
        logger.warning("Error upserting session summary for %s: %s", session_id, exc)


def ensure_session_exists(session_id: str, title: str = "Cuộc trò chuyện mới") -> None:
    """Create a chat_sessions row if it doesn't exist yet."""
    if not is_chat_persistence_enabled():
        return
    try:
        import psycopg
    except ImportError:
        return
    try:
        with psycopg.connect(POSTGRES_DSN, autocommit=True) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO chat_sessions (session_id, title, summary, turn_count, updated_at)
                    VALUES (%s, %s, '', 0, NOW())
                    ON CONFLICT (session_id) DO NOTHING
                    """,
                    (session_id, title)
                )
    except Exception as exc:
        logger.warning("Error ensuring session %s: %s", session_id, exc)


def update_session_title(session_id: str, title: str) -> None:
    """Update the display title for a session."""
    if not is_chat_persistence_enabled():
        return
    try:
        import psycopg
    except ImportError:
        return
    try:
        with psycopg.connect(POSTGRES_DSN, autocommit=True) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE chat_sessions SET title = %s WHERE session_id = %s",
                    (title, session_id)
                )
    except Exception as exc:
        logger.warning("Error updating session title %s: %s", session_id, exc)


def save_chat_message(
    session_id: str,
    message_id: str,
    role: str,
    content: str,
    context_used: Optional[List[Dict[str, Any]]] = None,
    created_at: Optional[datetime] = None,
) -> None:
    """Persist a single chat message (user or assistant) to PostgreSQL."""
    if not is_chat_persistence_enabled():
        return
    try:
        import psycopg
    except ImportError:
        return
    try:
        with psycopg.connect(POSTGRES_DSN, autocommit=True) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO chat_messages (id, session_id, role, content, context_used, created_at)
                    VALUES (%s, %s, %s, %s, %s, COALESCE(%s, NOW()))
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (message_id, session_id, role, content, json.dumps(context_used or [], ensure_ascii=False), created_at)
                )
                # Keep updated_at fresh on the parent session row
                cursor.execute(
                    "UPDATE chat_sessions SET updated_at = NOW() WHERE session_id = %s",
                    (session_id,)
                )
    except Exception as exc:
        logger.warning("Error saving chat message %s: %s", message_id, exc)


def get_session_messages(session_id: str) -> List[Dict[str, Any]]:
    """Return all messages for a session ordered by creation time."""
    if not is_chat_persistence_enabled():
        return []
    try:
        import psycopg
    except ImportError:
        return []
    try:
        with psycopg.connect(POSTGRES_DSN) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, role, content, context_used, created_at
                    FROM chat_messages
                    WHERE session_id = %s
                    ORDER BY created_at ASC
                    """,
                    (session_id,)
                )
                rows = cursor.fetchall()
                return [
                    {
                        "id": r[0],
                        "role": r[1],
                        "content": r[2],
                        "contextUsed": r[3] if r[3] else [],
                        "created_at": r[4].isoformat() if r[4] else None,
                    }
                    for r in rows
                ]
    except Exception as exc:
        logger.warning("Error getting messages for session %s: %s", session_id, exc)
        return []


def list_sessions() -> List[Dict[str, Any]]:
    """Return all sessions ordered by most recent activity."""
    if not is_chat_persistence_enabled():
        return []
    try:
        import psycopg
    except ImportError:
        return []
    try:
        with psycopg.connect(POSTGRES_DSN) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT s.session_id, s.title, s.turn_count, s.updated_at, COUNT(m.id) as message_count
                    FROM chat_sessions s
                    LEFT JOIN chat_messages m ON s.session_id = m.session_id
                    GROUP BY s.session_id
                    ORDER BY s.updated_at DESC
                    """
                )
                rows = cursor.fetchall()
                return [
                    {
                        "session_id": r[0],
                        "title": r[1],
                        "turn_count": r[2],
                        "updated_at": r[3].isoformat() if r[3] else None,
                        "message_count": r[4],
                    }
                    for r in rows
                ]
    except Exception as exc:
        logger.warning("Error listing sessions: %s", exc)
        return []


def delete_session_summary(session_id: str) -> None:
    """Delete a session and ALL associated data (messages, feedbacks) from PostgreSQL."""
    if not is_chat_persistence_enabled():
        return
    try:
        import psycopg
    except ImportError:
        return

    try:
        with psycopg.connect(POSTGRES_DSN, autocommit=True) as conn:
            with conn.cursor() as cursor:
                # chat_messages and chat_feedbacks are cascade-deleted via FK,
                # but chat_feedbacks has no FK so delete explicitly.
                cursor.execute("DELETE FROM chat_feedbacks WHERE session_id = %s", (session_id,))
                # This cascades to chat_messages automatically.
                cursor.execute("DELETE FROM chat_sessions WHERE session_id = %s", (session_id,))
                logger.info("Deleted session %s from PostgreSQL", session_id)
    except Exception as exc:
        logger.warning("Error deleting session data for %s: %s", session_id, exc)

def get_all_chat_messages() -> List[Dict[str, Any]]:
    """Get all chat messages from PostgreSQL for analytics."""
    if not is_chat_persistence_enabled():
        return []
    try:
        import psycopg
    except ImportError:
        return []
    try:
        with psycopg.connect(POSTGRES_DSN) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, session_id, role, content, created_at
                    FROM chat_messages
                    ORDER BY created_at DESC
                    """
                )
                rows = cursor.fetchall()
                return [
                    {
                        "id": r[0],
                        "session_id": r[1],
                        "role": r[2],
                        "content": r[3],
                        "timestamp": r[4].isoformat() if r[4] else None,
                    }
                    for r in rows
                ]
    except Exception as exc:
        logger.warning("Error getting all chat messages: %s", exc)
        return []
