"""
Pydantic models cho API request/response.
Tách riêng để dễ tái sử dụng và test.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.services.provider_registry import (
    INFERENCE_ROLES,
    PROVIDER_REGISTRY,
    is_supported_model,
    is_supported_provider,
    normalize_provider_id,
)


class Message(BaseModel):
    """Một tin nhắn trong lịch sử chat."""
    role: str
    content: str


class RuntimeProviderCredential(BaseModel):
    """Browser-provided provider credential for the current request."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    api_key: Optional[str] = Field(default=None, alias="apiKey")


class RuntimeProviderCredentials(BaseModel):
    """Provider credentials sent from browser storage per request."""

    model_config = ConfigDict(extra="forbid")

    google: Optional[RuntimeProviderCredential] = None
    huggingface: Optional[RuntimeProviderCredential] = None

    def get_api_key(self, provider: str) -> str:
        provider_id = normalize_provider_id(provider)
        credential = getattr(self, provider_id, None)
        return (credential.api_key or "").strip() if credential else ""


class RuntimeInferenceRole(BaseModel):
    """Provider/model assignment for one inference role."""

    model_config = ConfigDict(extra="forbid")

    provider: str
    model: str

    @model_validator(mode="after")
    def validate_provider_and_model(self):
        provider_id = normalize_provider_id(self.provider)
        self.provider = provider_id
        self.model = self.model.strip()

        if not is_supported_provider(provider_id):
            supported = ", ".join(sorted(PROVIDER_REGISTRY))
            raise ValueError(f"Unsupported inference provider '{provider_id}'. Supported providers: {supported}")

        if not is_supported_model(provider_id, self.model):
            raise ValueError(f"Unsupported model '{self.model}' for provider '{provider_id}'")

        return self


class RuntimeInferenceRoles(BaseModel):
    """Runtime model assignments for supported inference roles."""

    model_config = ConfigDict(extra="forbid")

    answer: Optional[RuntimeInferenceRole] = None
    rewriter: Optional[RuntimeInferenceRole] = None
    summarizer: Optional[RuntimeInferenceRole] = None

    def get(self, role: str) -> Optional[RuntimeInferenceRole]:
        role_id = role.strip().lower()
        if role_id not in INFERENCE_ROLES:
            return None
        return getattr(self, role_id)


class RuntimeInferenceConfig(BaseModel):
    """Browser-local BYOK inference config sent with each chat request."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    credentials: RuntimeProviderCredentials = Field(default_factory=RuntimeProviderCredentials)
    roles: RuntimeInferenceRoles = Field(default_factory=RuntimeInferenceRoles)
    use_server_fallbacks: bool = Field(default=True, alias="useServerFallbacks")

    def api_key_for(self, provider: str) -> str:
        return self.credentials.get_api_key(provider)


class ChatRequest(BaseModel):
    """Dữ liệu gửi lên từ Frontend khi user đặt câu hỏi."""
    model_config = ConfigDict(populate_by_name=True)

    messages: List[Message]
    model: str
    sessionId: Optional[str] = "unknown"
    sessionTitle: Optional[str] = "Cuộc trò chuyện mới"
    messageId: Optional[str] = None
    category: str = "all"  # Lĩnh vực pháp luật để lọc tài liệu
    temperature: Optional[float] = None
    maxTokens: Optional[int] = None
    topK: Optional[int] = Field(default=5, ge=1, le=20)
    candidateK: int = Field(default=10, ge=10, le=100)
    cacheThreshold: float = Field(default=0.95, ge=0.8, le=0.99)
    maxSubqueries: int = Field(default=3, ge=1, le=5)
    historyMessages: int = Field(default=4, ge=0, le=10)
    contextTokenBudget: int = Field(default=6000, ge=1000, le=16000)
    maxCitations: int = Field(default=5, ge=1, le=10)
    llmTimeout: int = Field(default=300, ge=30, le=300)
    streaming: bool = True
    useHistoryForRewriter: bool = True
    enableQueryRewriter: bool = True
    enableReranker: bool = True
    enableSemanticCache: bool = True
    enableMemory: bool = True
    inference_config: Optional[RuntimeInferenceConfig] = Field(default=None, alias="inferenceConfig")

    @model_validator(mode="after")
    def validate_candidate_window(self):
        final_top_k = self.topK or 5
        if self.candidateK < final_top_k:
            raise ValueError("candidateK must be greater than or equal to topK")
        return self


class ChatResponse(BaseModel):
    """Dữ liệu trả về cho Frontend sau khi LLM trả lời."""
    text: str
    contextUsed: List[Dict[str, Any]]
