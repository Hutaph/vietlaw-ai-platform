"""
Embedding module with the abstract interface and concrete implementations.

Protocol:
    BaseEmbedding: shared interface for embedding strategies.

Implementations:
    - HuggingFaceEndpointEmbedding: Hugging Face API or local SentenceTransformer.
    - OllamaEmbedding: local embedding through Ollama.
"""
from app.services.embedding.base import BaseEmbedding
from app.services.embedding.hf_endpoint import HuggingFaceEndpointEmbedding
from app.services.embedding.ollama import OllamaEmbedding
from app.services.embedding.fallback import FallbackEmbedding

__all__ = [
    "BaseEmbedding",
    "HuggingFaceEndpointEmbedding",
    "OllamaEmbedding",
    "FallbackEmbedding",
]
