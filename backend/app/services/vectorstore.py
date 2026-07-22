"""
Legacy FAISS vector store helpers.
Kept for local fallback paths and compatibility with older scripts.
"""
import os
import json
import glob
import time
from typing import List, Dict, Any, Optional

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_community.vectorstores.utils import DistanceStrategy
from app.config import (
    FAISS_INDEX_PATH, JSON_DATA_PATH, TRACKING_FILE,
    EMBEDDING_BATCH_SIZE, EMBEDDING_MAX_RETRIES,
    EMBEDDING_SLEEP_BETWEEN_BATCHES, EMBEDDING_RETRY_BASE_WAIT,
)
from app.services.embedding.hf_endpoint import HuggingFaceEndpointEmbedding
from app.services.knowledge_base import (
    KNOWLEDGE_BASE as CANONICAL_KNOWLEDGE_BASE,
    LAW_METADATA as CANONICAL_LAW_METADATA,
    determine_category,
    load_knowledge_base,
)
from app.utils.logging import setup_logger

logger = setup_logger("vietlaw.vectorstore")

# --- Module-level state ---
vectorstore: Optional[FAISS] = None
embeddings = None
KNOWLEDGE_BASE: Dict[str, Any] = {}
LAW_METADATA: Dict[str, Any] = {}


def _get_embeddings():
    global embeddings
    if embeddings is None:
        embeddings = HuggingFaceEndpointEmbedding().langchain_embeddings
    return embeddings


def load_knowledge_base_to_ram() -> None:
    """Load the corpus into RAM through the canonical backend loader."""
    global KNOWLEDGE_BASE, LAW_METADATA
    load_knowledge_base()
    KNOWLEDGE_BASE = CANONICAL_KNOWLEDGE_BASE
    LAW_METADATA = CANONICAL_LAW_METADATA
    logger.info("Nạp dữ liệu vào RAM hoàn tất! (%d chunks)", len(KNOWLEDGE_BASE))


def get_processed_files() -> List[str]:
    """Read the list of files that have already been embedded."""
    if os.path.exists(TRACKING_FILE):
        with open(TRACKING_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def mark_file_as_processed(filename: str) -> None:
    """Mark a file as processed so future runs can skip it."""
    processed = get_processed_files()
    if filename not in processed:
        processed.append(filename)
        with open(TRACKING_FILE, 'w', encoding='utf-8') as f:
            json.dump(processed, f, ensure_ascii=False, indent=4)


def _embed_single_file(file_path: str) -> None:
    """Embed one JSON file into the FAISS index."""
    global vectorstore

    filename = os.path.basename(file_path)
    logger.info("=" * 50)
    logger.info("BẮT ĐẦU EMBEDDING: %s", filename)
    logger.info("=" * 50)

    splits = []
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        law_id = data.get("law_info", {}).get("law_id")
        category = determine_category(data.get("law_info", {}).get("law_name", ""))

        # Wrap each clause as a LangChain document.
        for clause in data.get("clauses", []):
            metadata = {
                "id": clause["id"],
                "law_id": law_id,
                "category": category,
            }
            doc = Document(page_content=clause.get("content", ""), metadata=metadata)
            splits.append(doc)

    logger.info("Số lượng chunk cần nhúng: %d", len(splits))

    for i in range(0, len(splits), EMBEDDING_BATCH_SIZE):
        batch = splits[i:i + EMBEDDING_BATCH_SIZE]
        logger.info("  + Đang đẩy batch %d → %d...", i, i + len(batch))

        for attempt in range(EMBEDDING_MAX_RETRIES):
            try:
                # Create the vector store on the first batch, then append later batches.
                if vectorstore is None:
                    vectorstore = FAISS.from_documents(
                        batch, _get_embeddings(),
                        distance_strategy=DistanceStrategy.COSINE
                    )
                else:
                    vectorstore.add_documents(batch)

                time.sleep(EMBEDDING_SLEEP_BETWEEN_BATCHES)
                break  # Success: leave the retry loop.

            except Exception as e:
                logger.warning(
                    "  -> Lỗi batch %d lần %d/%d: %s",
                    i, attempt + 1, EMBEDDING_MAX_RETRIES, str(e)[:100]
                )
                if attempt < EMBEDDING_MAX_RETRIES - 1:
                    wait_time = EMBEDDING_RETRY_BASE_WAIT * (attempt + 1)
                    logger.info("  -> Tạm nghỉ %ds...", wait_time)
                    time.sleep(wait_time)
                else:
                    logger.error("THẤT BẠI TẠI BATCH %d SAU %d LẦN THỬ.", i, EMBEDDING_MAX_RETRIES)
                    raise e

    vectorstore.save_local(FAISS_INDEX_PATH)
    mark_file_as_processed(filename)
    logger.info("Finished embedding and saved file: %s", filename)


def init_vector_db() -> None:
    """Initialize the FAISS vector database."""
    global vectorstore

    # 1. Load data into RAM before serving.
    load_knowledge_base_to_ram()

    # Load an existing index when available.
    if os.path.exists(FAISS_INDEX_PATH):
        logger.info("Đang tải FAISS Index từ ổ cứng...")
        vectorstore = FAISS.load_local(
            FAISS_INDEX_PATH,
            _get_embeddings(),
            allow_dangerous_deserialization=True
        )
    else:
        logger.warning(
            "Không tìm thấy FAISS Index tại %s. "
            "Nếu bạn dùng FAISS làm bộ nhớ chính, vui lòng chạy script ingest (nhúng tài liệu) riêng rẽ để tạo index.",
            FAISS_INDEX_PATH
        )


def get_vectorstore() -> Optional[FAISS]:
    """Return the current vector store, initializing it if needed."""
    global vectorstore
    if vectorstore is None:
        init_vector_db()
    return vectorstore
