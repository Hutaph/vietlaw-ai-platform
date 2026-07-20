"""
Quản lý Vector Store (FAISS), Knowledge Base, và quy trình Embedding.
Tách từ rag_service.py gốc — chỉ chứa logic liên quan đến dữ liệu và vector.
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
from app.services.knowledge_base import determine_category
from app.utils.logging import setup_logger

logger = setup_logger("vietlaw.vectorstore")

# --- BIẾN TOÀN CỤC ---
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
    """Nạp toàn bộ dữ liệu JSON vào RAM để Chatbot truy xuất siêu tốc mà không cần gọi API."""
    global KNOWLEDGE_BASE, LAW_METADATA
    json_files = glob.glob(os.path.join(JSON_DATA_PATH, "*.json"))

    logger.info("Đang nạp %d file JSON vào bộ nhớ...", len(json_files))

    for file_path in json_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            law_info = data.get("law_info", {})
            clauses = data.get("clauses", [])

            law_id = law_info.get("law_id")
            law_name = law_info.get("law_name", "")

            # Lưu trữ thông tin chung của văn bản luật
            LAW_METADATA[law_id] = {
                "law_name": law_name,
                "summary": law_info.get("executive_summary", ""),
                "category": determine_category(law_name)
            }

            # Lưu trữ chi tiết từng điều khoản
            for clause in clauses:
                KNOWLEDGE_BASE[clause["id"]] = {
                    "law_id": law_id,
                    "position": clause.get("position", {}),
                    "content": clause.get("content", ""),
                    "cross_references": clause.get("cross_references", [])
                }

    logger.info("Nạp dữ liệu vào RAM hoàn tất!")


def get_processed_files() -> List[str]:
    """Đọc danh sách các file đã được embedding thành công trước đó."""
    if os.path.exists(TRACKING_FILE):
        with open(TRACKING_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def mark_file_as_processed(filename: str) -> None:
    """Đánh dấu file đã xử lý xong để những lần chạy sau hệ thống sẽ bỏ qua."""
    processed = get_processed_files()
    if filename not in processed:
        processed.append(filename)
        with open(TRACKING_FILE, 'w', encoding='utf-8') as f:
            json.dump(processed, f, ensure_ascii=False, indent=4)


def _embed_single_file(file_path: str) -> None:
    """Nhúng (embedding) một file JSON vào FAISS index."""
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

        # Đóng gói từng điều khoản thành Document
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
                # Nếu vectorstore chưa có, tạo mới. Nếu có rồi thì thêm vào.
                if vectorstore is None:
                    vectorstore = FAISS.from_documents(
                        batch, _get_embeddings(),
                        distance_strategy=DistanceStrategy.COSINE
                    )
                else:
                    vectorstore.add_documents(batch)

                time.sleep(EMBEDDING_SLEEP_BETWEEN_BATCHES)
                break  # Thành công thì thoát retry

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
    logger.info("ĐÃ HOÀN THÀNH VÀ LƯU FILE: %s", filename)


def init_vector_db() -> None:
    """Hàm khởi tạo và cập nhật cơ sở dữ liệu vector (FAISS)."""
    global vectorstore

    # 1. Nạp dữ liệu vào RAM trước để sẵn sàng phục vụ
    load_knowledge_base_to_ram()

    # Tải index cũ nếu đã có
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
    """Trả về vectorstore hiện tại. Khởi tạo nếu chưa có."""
    global vectorstore
    if vectorstore is None:
        init_vector_db()
    return vectorstore
