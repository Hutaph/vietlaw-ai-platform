#!/usr/bin/env python
"""
Flush the semantic cache after the knowledge base changes.
Run with: python -m scripts.clear_semantic_cache
"""

import sys
import os
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
from app.config import (
    QDRANT_URL,
    QDRANT_API_KEY,
    ENABLE_SEMANTIC_CACHE,
    EMBEDDING_DIMENSION,
    SEMANTIC_CACHE_COLLECTION,
)

def main():
    if not ENABLE_SEMANTIC_CACHE:
        print("Semantic Caching is currently disabled in .env (ENABLE_SEMANTIC_CACHE=false).")
        return

    print("Connecting to Qdrant...")
    try:
        client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY or None)
        collection_name = SEMANTIC_CACHE_COLLECTION

        print(f"Checking for collection '{collection_name}'...")
        try:
            client.get_collection(collection_name)
        except Exception:
            print(f"Collection '{collection_name}' does not exist. Nothing to clear.")
            return

        print(f"Recreating collection '{collection_name}' to flush all cached responses...")
        client.recreate_collection(
            collection_name=collection_name,
            vectors_config=qdrant_models.VectorParams(size=EMBEDDING_DIMENSION, distance=qdrant_models.Distance.COSINE),
        )
        print("Semantic Cache cleared successfully!")

    except Exception as e:
        print(f"An error occurred while clearing semantic cache: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
