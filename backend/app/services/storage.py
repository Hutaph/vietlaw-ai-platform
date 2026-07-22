"""
Storage bootstrap for Qdrant + PostgreSQL-backed legal corpus persistence.

This module introduces a storage abstraction for the new backend while
preserving backward compatibility with the existing FAISS-based flow.
"""
from __future__ import annotations

import json
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.config import (
    EMBEDDING_BATCH_SIZE,
    EMBEDDING_DIMENSION,
    EMBEDDING_PROVIDER,
    POSTGRES_DSN,
    CHAT_STORAGE_MODE,
    QDRANT_API_KEY,
    QDRANT_COLLECTION,
    QDRANT_MAX_RETRIES,
    QDRANT_TIMEOUT,
    QDRANT_UPSERT_BATCH_SIZE,
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


class IngestionVerificationError(StorageInitializationError):
    """Raised when persisted relational rows and vector index state diverge."""


def is_database_backend_enabled() -> bool:
    """Return True when the runtime is configured to use the database-backed storage layer."""
    return STORAGE_BACKEND.lower() in {"qdrant_postgres", "postgres", "postgresql", "qdrant"}


def _connect_postgres(*, autocommit: bool = False):
    """Open a psycopg connection compatible with Supabase transaction pooler."""
    import psycopg

    return psycopg.connect(
        POSTGRES_DSN,
        autocommit=autocommit,
        prepare_threshold=None,
    )


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

    with _connect_postgres(autocommit=True) as conn:
        with conn.cursor() as cursor:
            for statement in schema_statements:
                cursor.execute(statement)


def list_legal_documents() -> List[Dict[str, Any]]:
    """Return legal document records stored in PostgreSQL."""
    if not is_database_backend_enabled():
        return []

    _ensure_schema()
    with _connect_postgres(autocommit=True) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    l.law_id,
                    l.law_name,
                    COALESCE(l.summary, '') AS summary,
                    COALESCE(l.category, '') AS category,
                    COALESCE(l.metadata, '{}'::jsonb) AS metadata,
                    COUNT(c.id) AS clause_count
                FROM laws l
                LEFT JOIN clauses c ON c.law_id = l.law_id
                GROUP BY l.law_id, l.law_name, l.summary, l.category, l.metadata
                ORDER BY l.law_name ASC, l.law_id ASC
                """
            )
            return [
                {
                    "id": row[0],
                    "name": row[1],
                    "summary": row[2],
                    "category": row[3],
                    "metadata": row[4] or {},
                    "chunkCount": int(row[5] or 0),
                }
                for row in cursor.fetchall()
            ]


def list_document_chunks(law_id: str) -> List[Dict[str, Any]]:
    """Return clause chunks for one legal document from PostgreSQL."""
    if not is_database_backend_enabled():
        return []

    _ensure_schema()
    with _connect_postgres(autocommit=True) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, content, COALESCE(position, '{}'::jsonb)
                FROM clauses
                WHERE law_id = %s
                ORDER BY id ASC
                """,
                (law_id,),
            )
            return [
                {
                    "id": row[0],
                    "content": row[1],
                    "position": row[2] or {},
                }
                for row in cursor.fetchall()
            ]


def _start_indexing_run(source: str, details: Optional[Dict[str, Any]] = None) -> Optional[int]:
    """Create a new indexing run record and return its id when PostgreSQL is available."""
    try:
        _ensure_schema()
        import psycopg
    except ImportError:  # pragma: no cover - runtime dependency check
        return None

    try:
        with _connect_postgres(autocommit=True) as conn:
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
        with _connect_postgres(autocommit=True) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE indexing_runs
                    SET status = %s,
                        finished_at = CASE WHEN %s = 'running' THEN finished_at ELSE NOW() END,
                        details = %s
                    WHERE id = %s
                    """,
                    (status, status, json.dumps(details or {}), run_id),
                )
    except Exception as exc:  # pragma: no cover - runtime dependency path
        logger.warning("Unable to update indexing run record %s: %s", run_id, exc)


def _qdrant_point_id(clause_id: str) -> str:
    """Return the stable Qdrant point id for a legal clause id."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, clause_id))


def _new_qdrant_client():
    from qdrant_client import QdrantClient

    return QdrantClient(
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY or None,
        timeout=QDRANT_TIMEOUT,
    )


def _batched(items: List[Any], batch_size: int) -> List[List[Any]]:
    return [items[index:index + batch_size] for index in range(0, len(items), batch_size)]


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
        with _connect_postgres(autocommit=True) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM clauses")
                existing_clause_count = cursor.fetchone()[0]
                if existing_clause_count > 0:
                    logger.info("Database already contains %d clauses; checking Qdrant schema...", existing_clause_count)
    except Exception as exc:
        logger.warning("Could not check existing clause count: %s", exc)
        # Continue with initialization if check fails

    qdrant_client = _new_qdrant_client()
    
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
        raise StorageInitializationError(f"Initial document ingestion failed: {exc}") from exc

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
                "metadata": clause_data.get("metadata", {}),
            }
        )

    records = list(grouped.values())
    if not records:
        return 0

    return ingest_documents(records)


def _flatten_clauses(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    clauses: List[Dict[str, Any]] = []
    for record in records:
        for clause in record.get("clauses", []):
            if not clause.get("id") or not clause.get("content"):
                continue
            clauses.append(
                {
                    **clause,
                    "law_id": record["law_id"],
                    "category": record.get("category", "all"),
                }
            )
    return clauses


def _qdrant_existing_clause_ids(qdrant_client, clause_ids: List[str]) -> set[str]:
    existing: set[str] = set()
    for batch in _batched(clause_ids, 256):
        point_ids = [_qdrant_point_id(clause_id) for clause_id in batch]
        points = qdrant_client.retrieve(
            collection_name=QDRANT_COLLECTION,
            ids=point_ids,
            with_payload=True,
            with_vectors=False,
        )
        for point in points:
            payload = point.payload or {}
            clause_id = payload.get("id")
            if isinstance(clause_id, str):
                existing.add(clause_id)
    return existing


def _upsert_qdrant_points_with_retry(qdrant_client, points: List[Any]) -> None:
    if not points:
        return

    for attempt in range(1, QDRANT_MAX_RETRIES + 1):
        try:
            qdrant_client.upsert(
                collection_name=QDRANT_COLLECTION,
                points=points,
                wait=True,
            )
            return
        except Exception as exc:
            if attempt >= QDRANT_MAX_RETRIES:
                raise
            sleep_seconds = min(2 ** attempt, 30)
            logger.warning(
                "Qdrant upsert failed for %d point(s), retrying %d/%d in %ss: %s",
                len(points),
                attempt,
                QDRANT_MAX_RETRIES,
                sleep_seconds,
                exc,
            )
            time.sleep(sleep_seconds)


def _upsert_laws_and_clauses(conn, records: List[Dict[str, Any]]) -> None:
    with conn.cursor() as cursor:
        law_rows = [
            (
                record["law_id"],
                record.get("law_name", ""),
                record.get("summary", ""),
                record.get("category", "all"),
                json.dumps(record.get("metadata", {})),
            )
            for record in records
        ]
        logger.info("Upserting %d law record(s) into PostgreSQL.", len(law_rows))
        cursor.executemany(
            """
            INSERT INTO laws (law_id, law_name, summary, category, metadata)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (law_id) DO UPDATE SET
                law_name = EXCLUDED.law_name,
                summary = EXCLUDED.summary,
                category = EXCLUDED.category,
                metadata = EXCLUDED.metadata
            """,
            law_rows,
        )

        clause_rows: List[tuple[str, str, str, str, str]] = []
        for record in records:
            law_id = record["law_id"]
            for clause in record.get("clauses", []):
                clause_rows.append(
                    (
                        clause["id"],
                        law_id,
                        clause.get("content", ""),
                        json.dumps(clause.get("position", {})),
                        json.dumps(clause.get("cross_references", [])),
                    )
                )

        clause_sql = """
            INSERT INTO clauses (id, law_id, content, position, cross_references)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                law_id = EXCLUDED.law_id,
                content = EXCLUDED.content,
                position = EXCLUDED.position,
                cross_references = EXCLUDED.cross_references
        """
        for batch_index, batch in enumerate(_batched(clause_rows, 1000), start=1):
            cursor.executemany(clause_sql, batch)
            logger.info(
                "Upserted PostgreSQL clause batch %d/%d (%d/%d clauses).",
                batch_index,
                (len(clause_rows) + 999) // 1000,
                min(batch_index * 1000, len(clause_rows)),
                len(clause_rows),
            )


def _verify_ingestion(conn, qdrant_client, expected_clause_ids: List[str]) -> Dict[str, Any]:
    with conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM clauses WHERE id = ANY(%s)", (expected_clause_ids,))
        postgres_count = int(cursor.fetchone()[0])

    qdrant_existing = _qdrant_existing_clause_ids(qdrant_client, expected_clause_ids)
    missing_qdrant = sorted(set(expected_clause_ids) - qdrant_existing)
    details = {
        "expected_clauses": len(expected_clause_ids),
        "postgres_clauses": postgres_count,
        "qdrant_points": len(qdrant_existing),
        "missing_qdrant_count": len(missing_qdrant),
        "missing_qdrant_sample": missing_qdrant[:20],
    }
    if postgres_count != len(expected_clause_ids) or missing_qdrant:
        raise IngestionVerificationError(f"Ingestion verification failed: {details}")
    return details


def ingest_documents(
    records: List[Dict[str, Any]],
    embedding_backend=None,
    sparse_generator=None,
) -> int:
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

    qdrant_client = _new_qdrant_client()
    all_clauses = _flatten_clauses(records)
    expected_clause_ids = [clause["id"] for clause in all_clauses]
    run_id = _start_indexing_run(
        "ingest_documents",
        {
            "record_count": len(records),
            "clause_count": len(expected_clause_ids),
            "backend": STORAGE_BACKEND,
            "collection": QDRANT_COLLECTION,
        },
    )

    try:
        with _connect_postgres(autocommit=True) as conn:
            _upsert_laws_and_clauses(conn, records)

            existing_clause_ids = _qdrant_existing_clause_ids(qdrant_client, expected_clause_ids)
            missing_clauses = [
                clause for clause in all_clauses
                if clause["id"] not in existing_clause_ids
            ]
            if not missing_clauses:
                verification = _verify_ingestion(conn, qdrant_client, expected_clause_ids)
                _finish_indexing_run(
                    run_id,
                    "skipped",
                    {
                        **verification,
                        "backend": STORAGE_BACKEND,
                        "collection": QDRANT_COLLECTION,
                        "reason": "all_vectors_exist",
                    },
                )
                logger.info(
                    "All %d Qdrant vectors already exist for collection %s; ingestion resume has nothing to add.",
                    len(expected_clause_ids),
                    QDRANT_COLLECTION,
                )
                return 0

            if embedding_backend is None and any("embedding" not in clause for clause in missing_clauses):
                try:
                    if EMBEDDING_PROVIDER == "ollama":
                        from app.services.embedding.ollama import OllamaEmbedding
                        embedding_backend = OllamaEmbedding()
                    else:
                        from app.services.embedding.hf_endpoint import HuggingFaceEndpointEmbedding
                        embedding_backend = HuggingFaceEndpointEmbedding()
                except Exception as exc:  # pragma: no cover - runtime dependency path
                    raise StorageInitializationError(
                        f"Embedding backend unavailable during ingestion: {exc}"
                    ) from exc

            if sparse_generator is None:
                try:
                    from app.services.sparse_vector import SparseVectorGenerator
                    sparse_generator = SparseVectorGenerator()
                except Exception as exc:
                    logger.warning("SparseVectorGenerator unavailable: %s", exc)
                    sparse_generator = None

            logger.info(
                "Qdrant resume check: %d/%d vectors exist; embedding %d missing clauses.",
                len(existing_clause_ids),
                len(expected_clause_ids),
                len(missing_clauses),
            )

            try:
                from tqdm import tqdm
                batches = tqdm(
                    _batched(missing_clauses, EMBEDDING_BATCH_SIZE),
                    desc="Embedding/upserting clauses",
                    unit="batch",
                )
            except ImportError:
                batches = _batched(missing_clauses, EMBEDDING_BATCH_SIZE)

            embedded_count = 0
            pending_points: List[Any] = []
            for batch in batches:
                texts = [clause.get("content", "") for clause in batch]
                dense_vectors = (
                    [clause.get("embedding") for clause in batch]
                    if embedding_backend is None
                    else embedding_backend.embed_documents(texts)
                )
                if len(dense_vectors) != len(batch):
                    raise StorageInitializationError(
                        "Embedding backend returned "
                        f"{len(dense_vectors)} vector(s) for {len(batch)} clause(s)."
                    )

                points = []
                for clause, embedding in zip(batch, dense_vectors):
                    if hasattr(embedding, "tolist"):
                        embedding = embedding.tolist()
                    if embedding is None or len(embedding) == 0:
                        raise StorageInitializationError(
                            f"Embedding output is empty for clause {clause['id']}."
                        )

                    vector_dict = {"text-dense": embedding}
                    if sparse_generator is not None:
                        sparse_embedding = sparse_generator.generate_sparse_vector(clause.get("content", ""))
                    else:
                        sparse_embedding = clause.get("sparse_embedding")

                    if sparse_embedding and sparse_embedding.get("indices"):
                        vector_dict["text-sparse"] = qdrant_models.SparseVector(
                            indices=sparse_embedding["indices"],
                            values=sparse_embedding["values"],
                        )

                    points.append(
                        qdrant_models.PointStruct(
                            id=_qdrant_point_id(clause["id"]),
                            vector=vector_dict,
                            payload={
                                "id": clause["id"],
                                "law_id": clause["law_id"],
                                "content": clause.get("content", ""),
                                "category": clause.get("category", "all"),
                                "position": clause.get("position", {}),
                                "metadata": clause.get("metadata", {}),
                            },
                        )
                    )

                pending_points.extend(points)
                if len(pending_points) >= QDRANT_UPSERT_BATCH_SIZE:
                    flushed_count = len(pending_points)
                    _upsert_qdrant_points_with_retry(qdrant_client, pending_points)
                    pending_points = []
                    embedded_count += flushed_count
                    _finish_indexing_run(
                        run_id,
                        "running",
                        {
                            "backend": STORAGE_BACKEND,
                            "collection": QDRANT_COLLECTION,
                            "expected_clauses": len(expected_clause_ids),
                            "embedded_this_run": embedded_count,
                            "remaining": len(missing_clauses) - embedded_count,
                        },
                    )

            if pending_points:
                flushed_count = len(pending_points)
                _upsert_qdrant_points_with_retry(qdrant_client, pending_points)
                embedded_count += flushed_count
                _finish_indexing_run(
                    run_id,
                    "running",
                    {
                        "backend": STORAGE_BACKEND,
                        "collection": QDRANT_COLLECTION,
                        "expected_clauses": len(expected_clause_ids),
                        "embedded_this_run": embedded_count,
                        "remaining": len(missing_clauses) - embedded_count,
                    },
                )

            verification = _verify_ingestion(conn, qdrant_client, expected_clause_ids)
            _finish_indexing_run(
                run_id,
                "completed",
                {
                    **verification,
                    "backend": STORAGE_BACKEND,
                    "collection": QDRANT_COLLECTION,
                    "embedded_this_run": embedded_count,
                },
            )
    except Exception as exc:
        _finish_indexing_run(
            run_id,
            "failed",
            {
                "record_count": len(records),
                "clause_count": len(expected_clause_ids),
                "backend": STORAGE_BACKEND,
                "collection": QDRANT_COLLECTION,
                "error": str(exc),
            },
        )
        raise

    logger.info(
        "Ingested %d document record(s), verified %d PostgreSQL clauses and Qdrant vectors.",
        len(records),
        len(expected_clause_ids),
    )
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
        with _connect_postgres(autocommit=True) as conn:
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
        with _connect_postgres(autocommit=True) as conn:
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
        with _connect_postgres(autocommit=True) as conn:
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
        with _connect_postgres(autocommit=True) as conn:
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
        with _connect_postgres(autocommit=True) as conn:
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
        with _connect_postgres() as conn:
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
        with _connect_postgres() as conn:
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
        with _connect_postgres(autocommit=True) as conn:
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
        with _connect_postgres() as conn:
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
