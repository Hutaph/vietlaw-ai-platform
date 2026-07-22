import os
import time
import json
from typing import List, Dict, Any
from fastapi import APIRouter, UploadFile, File, HTTPException

from app.config import JSON_DATA_PATH, STORAGE_BACKEND
from app.services.knowledge_base import LAW_METADATA, KNOWLEDGE_BASE
from app.utils.logging import setup_logger

logger = setup_logger("vietlaw.api.documents")
router = APIRouter()

@router.get("")
@router.get("/")
async def list_documents():
    """Return all loaded legal documents."""
    docs = []
    for law_id, meta in LAW_METADATA.items():
        docs.append({
            "id": law_id,
            "name": meta.get("law_name", ""),
            "summary": meta.get("summary", ""),
            "category": meta.get("category", "")
        })
    if docs:
        return {"documents": docs}

    if STORAGE_BACKEND.lower() in {"qdrant_postgres", "postgres", "postgresql", "qdrant"}:
        try:
            from app.services.storage import list_legal_documents
            return {"documents": list_legal_documents()}
        except Exception as exc:
            logger.error("Failed to list documents from database storage: %s", exc)
            raise HTTPException(status_code=503, detail="Không thể tải danh sách tài liệu từ cơ sở dữ liệu.")

    return {"documents": docs}


@router.get("/{law_id}/chunks")
async def get_document_chunks(law_id: str):
    """Return chunks for one legal document."""
    chunks = []
    for chunk_id, chunk_data in KNOWLEDGE_BASE.items():
        if chunk_data.get("law_id") == law_id:
            chunks.append({
                "id": chunk_id,
                "content": chunk_data.get("content", ""),
                "position": chunk_data.get("position", {})
            })
    if chunks:
        return {"chunks": chunks}

    if STORAGE_BACKEND.lower() in {"qdrant_postgres", "postgres", "postgresql", "qdrant"}:
        try:
            from app.services.storage import list_document_chunks
            return {"chunks": list_document_chunks(law_id)}
        except Exception as exc:
            logger.error("Failed to list chunks for %s from database storage: %s", law_id, exc)
            raise HTTPException(status_code=503, detail="Không thể tải các đoạn dữ liệu từ cơ sở dữ liệu.")

    return {"chunks": chunks}


@router.post("/upload")
async def upload_document(files: List[UploadFile] = File(...)):
    """Upload text documents, chunk them, and store them in the active backend."""
    for file in files:
        if not file.filename.endswith(".txt"):
            raise HTTPException(status_code=400, detail=f"File {file.filename} không đúng định dạng .txt")
    
    total_chunks = 0
    doc_ids = []
    
    for file_idx, file in enumerate(files):
        content_bytes = await file.read()
        content_str = content_bytes.decode("utf-8", errors="ignore")
        
        doc_id = f"DOC_{int(time.time())}_{file_idx}"
        
        # 1. Simple chunking (RecursiveCharacterTextSplitter equivalent via langchain)
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
            separators=["\n\n", "\n", ".", " ", ""]
        )
        chunks = splitter.split_text(content_str)
        
        # 2. Prepare JSON data structure
        json_data = {
            "law_info": {
                "law_id": doc_id,
                "law_name": file.filename,
                "executive_summary": "Tài liệu tải lên từ người dùng",
                "category": "uploaded"
            },
            "clauses": []
        }
        
        records = [{
            "law_id": doc_id,
            "law_name": file.filename,
            "summary": "Tài liệu tải lên từ người dùng",
            "category": "uploaded",
            "metadata": {"source": file.filename},
            "clauses": []
        }]
        
        for i, text in enumerate(chunks):
            chunk_id = f"{doc_id}_{i}"
            clause_data = {
                "id": chunk_id,
                "content": text,
                "position": {"chapter": "", "section": "", "clause": str(i)},
                "cross_references": []
            }
            json_data["clauses"].append(clause_data)
            
            # Prepare for ingest
            records[0]["clauses"].append(clause_data.copy())
            
            # Update RAM instantly
            KNOWLEDGE_BASE[chunk_id] = {
                "law_id": doc_id,
                "position": clause_data["position"],
                "content": text,
                "cross_references": []
            }
            
        LAW_METADATA[doc_id] = {
            "law_name": file.filename,
            "summary": "Tài liệu tải lên từ người dùng",
            "category": "uploaded"
        }
        
        # 3. Save JSON file for persistence
        os.makedirs(JSON_DATA_PATH, exist_ok=True)
        file_path = os.path.join(JSON_DATA_PATH, f"{doc_id}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
            
        # 4. Embed and store to Vector Database
        try:
            if STORAGE_BACKEND.lower() in {"qdrant_postgres", "postgres", "postgresql", "qdrant"}:
                from app.services.storage import ingest_documents
                from app.config import EMBEDDING_PROVIDER
                if EMBEDDING_PROVIDER == "ollama":
                    from app.services.embedding.ollama import OllamaEmbedding
                    embedding_backend = OllamaEmbedding()
                else:
                    from app.services.embedding.hf_endpoint import HuggingFaceEndpointEmbedding
                    embedding_backend = HuggingFaceEndpointEmbedding()
                
                try:
                    from app.services.sparse_vector import SparseVectorGenerator
                    sparse_generator = SparseVectorGenerator()
                except:
                    sparse_generator = None
                    
                for clause in records[0]["clauses"]:
                    clause["embedding"] = embedding_backend.embed_query(clause["content"])
                    if sparse_generator:
                        clause["sparse_embedding"] = sparse_generator.generate_sparse_vector(clause["content"])
                        
                ingest_documents(records)
                logger.info(f"Ingested document {doc_id} to Qdrant/Postgres")
            else:
                from app.services.vectorstore import _embed_single_file, get_vectorstore
                get_vectorstore() # Ensure initialized
                _embed_single_file(file_path)
                logger.info(f"Ingested document {doc_id} to FAISS")
        except Exception as e:
            logger.error(f"Error embedding uploaded document {doc_id}: {e}")
            # Even if embedding fails, the document has been saved in JSON and RAM.
            
        total_chunks += len(chunks)
        doc_ids.append(doc_id)
        
    return {"message": f"Upload thành công {len(files)} file", "document_ids": doc_ids, "chunks_count": total_chunks}


@router.delete("/{law_id}")
async def delete_document(law_id: str):
    """Delete a document from memory, disk, and the configured storage backend."""
    # 1. Remove from RAM
    if law_id in LAW_METADATA:
        del LAW_METADATA[law_id]
        
    chunks_to_delete = [k for k, v in KNOWLEDGE_BASE.items() if v.get("law_id") == law_id]
    for k in chunks_to_delete:
        del KNOWLEDGE_BASE[k]
        
    # 2. Remove JSON file
    file_path = os.path.join(JSON_DATA_PATH, f"{law_id}.json")
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            logger.info(f"Deleted file {file_path}")
        except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {e}")
            
    # 3. Remove from DB/Vector Store
    try:
        if STORAGE_BACKEND.lower() in {"qdrant_postgres", "postgres", "postgresql", "qdrant"}:
            import psycopg
            from app.config import QDRANT_URL, QDRANT_API_KEY, QDRANT_COLLECTION
            from app.services.storage import _connect_postgres
            from qdrant_client import QdrantClient
            from qdrant_client.http import models
            
            # Delete from Postgres
            with _connect_postgres(autocommit=True) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM laws WHERE law_id = %s", (law_id,))
                    
            # Delete from Qdrant
            qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY or None)
            qdrant_client.delete(
                collection_name=QDRANT_COLLECTION,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="law_id",
                                match=models.MatchValue(value=law_id),
                            )
                        ]
                    )
                )
            )
            logger.info(f"Deleted document {law_id} from DB/Vector Store")
        else:
            # For FAISS, we can't easily delete vectors. We'll skip FAISS deletion for now.
            # Realistically requires a full re-index.
            logger.warning(f"Deletion from FAISS is not supported. Restart ingestion if needed.")
            
    except Exception as e:
        logger.error(f"Failed to delete document {law_id} from storage: {e}")

    return {"message": "Xóa thành công", "document_id": law_id}
