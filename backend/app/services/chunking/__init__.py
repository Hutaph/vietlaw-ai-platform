"""
Chunking module for splitting documents into retrievable chunks.

Protocol:
    BaseChunker: shared interface for chunking strategies.

Implementations:
    - ClauseChunker: one legal clause per chunk.
    - Future RecursiveChunker: RecursiveCharacterTextSplitter-based chunking.
"""
from app.services.chunking.base import BaseChunker
from app.services.chunking.clause_chunker import ClauseChunker

__all__ = ["BaseChunker", "ClauseChunker"]
