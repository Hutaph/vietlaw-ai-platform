"""
Semantic Caching Service
"""
import uuid
import time
from typing import Optional, Dict, Any, List

from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

from app.config import (
    EMBEDDING_DIMENSION,
    QDRANT_URL,
    QDRANT_API_KEY,
    ENABLE_SEMANTIC_CACHE,
    SEMANTIC_CACHE_COLLECTION,
    SEMANTIC_CACHE_THRESHOLD
)
from app.utils.logging import setup_logger

logger = setup_logger("vietlaw.semantic_cache")

_qdrant_client = None


def _validate_query_vector(query_vector: List[float]) -> None:
    if len(query_vector) != EMBEDDING_DIMENSION:
        raise ValueError(
            f"Semantic cache vector dimension mismatch: expected {EMBEDDING_DIMENSION}, got {len(query_vector)}."
        )

def _get_client() -> Optional[QdrantClient]:
    global _qdrant_client
    if _qdrant_client is None:
        try:
            _qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY or None)
        except Exception as e:
            logger.warning("Failed to initialize QdrantClient for semantic cache: %s", e)
    return _qdrant_client

def check_cache(
    query_vector: List[float],
    score_threshold: Optional[float] = None,
) -> Optional[Dict[str, Any]]:
    """
    Check if a similar query exists in the semantic cache.
    Returns the cached payload (including text and contextUsed) if found, else None.
    """
    if not ENABLE_SEMANTIC_CACHE:
        return None
    _validate_query_vector(query_vector)

    threshold = SEMANTIC_CACHE_THRESHOLD if score_threshold is None else score_threshold
    client = _get_client()
    if not client:
        return None

    try:
        try:
            # Try query_points (newer versions)
            search_result = client.query_points(
                collection_name=SEMANTIC_CACHE_COLLECTION,
                query=query_vector,
                limit=1,
                score_threshold=threshold
            ).points
        except AttributeError:
            # Fallback for older versions
            search_result = client.search(
                collection_name=SEMANTIC_CACHE_COLLECTION,
                query_vector=query_vector,
                limit=1,
                score_threshold=threshold
            )
        
        if search_result and len(search_result) > 0:
            hit = search_result[0]
            logger.info("Semantic cache HIT! Score: %.4f", hit.score)
            return hit.payload
        
        logger.info("Semantic cache MISS.")
        return None
        
    except Exception as e:
        logger.warning("Error checking semantic cache: %s", e)
        return None

def update_cache(query_vector: List[float], original_query: str, response_text: str, context_used: List[Dict[str, Any]], retrieved_doc_ids: List[str] = None) -> None:
    """
    Update the semantic cache with a new query and its generated response.
    """
    if not ENABLE_SEMANTIC_CACHE:
        return
    _validate_query_vector(query_vector)

    client = _get_client()
    if not client:
        return

    try:
        point_id = str(uuid.uuid4())
        
        payload = {
            "original_query": original_query,
            "response_text": response_text,
            "context_used": context_used,
            "timestamp": time.time(),
            "retrieved_doc_ids": retrieved_doc_ids or []
        }
        
        client.upsert(
            collection_name=SEMANTIC_CACHE_COLLECTION,
            points=[
                qdrant_models.PointStruct(
                    id=point_id,
                    vector=query_vector,
                    payload=payload
                )
            ]
        )
        logger.info("Saved response to semantic cache (id: %s)", point_id)
        
    except Exception as e:
        logger.warning("Error updating semantic cache: %s", e)

def invalidate_cache_by_doc_ids(doc_ids: List[str]) -> bool:
    """
    Invalidate cache entries that relied on any of the provided doc_ids.
    """
    if not ENABLE_SEMANTIC_CACHE or not doc_ids:
        return False
        
    client = _get_client()
    if not client:
        return False
        
    try:
        client.delete(
            collection_name=SEMANTIC_CACHE_COLLECTION,
            points_selector=qdrant_models.FilterSelector(
                filter=qdrant_models.Filter(
                    must=[
                        qdrant_models.FieldCondition(
                            key="retrieved_doc_ids",
                            match=qdrant_models.MatchAny(any=doc_ids)
                        )
                    ]
                )
            )
        )
        logger.info("Invalidated semantic cache points for %d doc_ids.", len(doc_ids))
        return True
    except Exception as e:
        logger.warning("Error invalidating semantic cache: %s", e)
        return False
