"""
Chunking Module — Strategies cho việc tách document thành chunks.

Protocol:
    BaseChunker: Interface chung cho tất cả chunking strategies.

Implementations:
    - ClauseChunker: Mỗi điều khoản là 1 chunk (mặc định, giữ nguyên logic cũ)
    - (Future) RecursiveChunker: Dùng RecursiveCharacterTextSplitter
"""
from app.services.chunking.base import BaseChunker
from app.services.chunking.clause_chunker import ClauseChunker

__all__ = ["BaseChunker", "ClauseChunker"]
