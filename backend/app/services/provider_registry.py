from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


GOOGLE_PROVIDER = "google"
HUGGINGFACE_PROVIDER = "huggingface"
OLLAMA_PROVIDER = "ollama"

ANSWER_ROLE = "answer"
REWRITER_ROLE = "rewriter"
SUMMARIZER_ROLE = "summarizer"

INFERENCE_ROLES = frozenset({ANSWER_ROLE, REWRITER_ROLE, SUMMARIZER_ROLE})


@dataclass(frozen=True)
class ProviderDefinition:
    id: str
    label: str
    base_url: str
    models: frozenset[str]
    requires_api_key: bool
    deployment_supported: bool = True


GOOGLE_CHAT_MODELS = frozenset({
    "gemini-3.1-flash-lite",
})

HUGGINGFACE_CHAT_MODELS = frozenset({
    "Qwen/Qwen2.5-7B-Instruct",
    "meta-llama/Llama-3.1-8B-Instruct",
    "deepseek-ai/DeepSeek-R1-Distill-Llama-8B",
    "google/gemma-4-31B-it:novita",
})

OLLAMA_CHAT_MODELS = frozenset({
    "qwen2.5:7b-instruct",
    "qwen2.5:1.5b",
    "llama3.1:8b",
    "deepseek-r1:8b",
    "gemma2:9b",
})

PROVIDER_REGISTRY: dict[str, ProviderDefinition] = {
    GOOGLE_PROVIDER: ProviderDefinition(
        id=GOOGLE_PROVIDER,
        label="Google AI Studio",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        models=GOOGLE_CHAT_MODELS,
        requires_api_key=True,
    ),
    HUGGINGFACE_PROVIDER: ProviderDefinition(
        id=HUGGINGFACE_PROVIDER,
        label="HuggingFace Router",
        base_url="https://router.huggingface.co/v1",
        models=HUGGINGFACE_CHAT_MODELS,
        requires_api_key=True,
    ),
    OLLAMA_PROVIDER: ProviderDefinition(
        id=OLLAMA_PROVIDER,
        label="Ollama",
        base_url="",
        models=OLLAMA_CHAT_MODELS,
        requires_api_key=False,
        deployment_supported=False,
    ),
}


def normalize_provider_id(provider: str | None) -> str:
    return (provider or "").strip().lower()


def is_supported_provider(provider: str | None) -> bool:
    return normalize_provider_id(provider) in PROVIDER_REGISTRY


def is_supported_model(provider: str | None, model: str | None) -> bool:
    provider_id = normalize_provider_id(provider)
    model_name = (model or "").strip()
    definition = PROVIDER_REGISTRY.get(provider_id)
    return bool(definition and model_name in definition.models)


def infer_provider_for_model(model_name: str) -> str:
    model = (model_name or "").strip()
    for provider_id, definition in PROVIDER_REGISTRY.items():
        if model in definition.models:
            return provider_id
    if model.startswith("gemini-"):
        return GOOGLE_PROVIDER
    return HUGGINGFACE_PROVIDER


def redact_secret(value: str | None) -> str:
    if not value:
        return ""
    return "<redacted>"


def redact_runtime_inference_config(config: Any) -> Any:
    """Return a plain redacted representation of runtime inference config."""
    if config is None:
        return None
    if hasattr(config, "model_dump"):
        config = config.model_dump(by_alias=True)
    if isinstance(config, Mapping):
        redacted: dict[str, Any] = {}
        for key, value in config.items():
            if key.lower() in {"apikey", "api_key", "token"}:
                redacted[key] = redact_secret(value)
            else:
                redacted[key] = redact_runtime_inference_config(value)
        return redacted
    if isinstance(config, list):
        return [redact_runtime_inference_config(item) for item in config]
    return config
