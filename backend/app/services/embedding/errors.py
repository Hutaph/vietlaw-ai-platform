class EmbeddingServiceError(RuntimeError):
    """Base error for user-visible embedding provider failures."""


class EmbeddingAuthError(EmbeddingServiceError):
    """Raised when the embedding provider rejects credentials."""


class EmbeddingServerError(EmbeddingServiceError):
    """Raised when the embedding provider is temporarily unavailable."""
