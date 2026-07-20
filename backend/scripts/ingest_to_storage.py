import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.storage import ingest_json_documents, initialize_storage


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest processed legal JSON into the configured storage backend")
    args = parser.parse_args()

    try:
        print("Khởi tạo schema và các collection...")
        initialize_storage()
        
        print("Bắt đầu nhúng và nạp dữ liệu (có thể tốn vài giờ)...")
        count = ingest_json_documents()
        
        if count > 0:
            print("Đang dọn dẹp semantic cache cho các document bị thay đổi...")
            try:
                from app.services.knowledge_base import KNOWLEDGE_BASE
                from app.services.semantic_cache import invalidate_cache_by_doc_ids
                affected_ids = list(KNOWLEDGE_BASE.keys())
                
                # Chunking to avoid massive Qdrant payload limits
                chunk_size = 1000
                for i in range(0, len(affected_ids), chunk_size):
                    invalidate_cache_by_doc_ids(affected_ids[i:i+chunk_size])
                print(f"Đã gửi yêu cầu xóa cache cho {len(affected_ids)} document IDs.")
            except Exception as e:
                print(f"Lỗi khi dọn dẹp semantic cache: {e}", file=sys.stderr)
                
        print(f"Đã nạp thành công {count} văn bản.")
        return 0
    except Exception as exc:
        print(f"Storage ingestion failed: {exc}", file=sys.stderr)
        print("Verify that PostgreSQL and Qdrant are running and that your storage configuration is correct.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
