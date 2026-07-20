import pytest
from pydantic import ValidationError

import app.services.llm as llm_module
from app.models import ChatRequest, RuntimeInferenceConfig
from app.services.provider_registry import redact_runtime_inference_config


class FakeChatOpenAI:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.model = kwargs["model"]
        self.base_url = kwargs["base_url"]
        self.api_key = kwargs["api_key"]
        self.fallbacks = []

    def with_fallbacks(self, fallbacks):
        self.fallbacks = fallbacks
        return self


def _patch_chat_factory(monkeypatch):
    monkeypatch.setattr(llm_module, "ChatOpenAI", FakeChatOpenAI)
    monkeypatch.setattr(llm_module, "HUGGINGFACE_API_KEY", "env-hf-token")
    monkeypatch.setattr(llm_module, "GOOGLE_API_KEY", "env-google-token")
    monkeypatch.setattr(llm_module, "ENABLE_GOOGLE_FALLBACK", False)
    monkeypatch.setattr(llm_module, "INFERENCE_STRATEGY", "remote_first")


def _runtime_config(provider="google", model="gemini-3.1-flash-lite", key="runtime-google-token", role="answer"):
    return RuntimeInferenceConfig.model_validate({
        "credentials": {
            provider: {"apiKey": key}
        },
        "roles": {
            role: {"provider": provider, "model": model}
        },
        "useServerFallbacks": False,
    })


def test_runtime_inference_config_rejects_unsupported_provider():
    with pytest.raises(ValidationError):
        RuntimeInferenceConfig.model_validate({
            "roles": {
                "answer": {"provider": "custom", "model": "anything"}
            }
        })


def test_runtime_inference_config_rejects_arbitrary_base_url():
    with pytest.raises(ValidationError):
        RuntimeInferenceConfig.model_validate({
            "roles": {
                "answer": {
                    "provider": "google",
                    "model": "gemini-3.1-flash-lite",
                    "baseUrl": "http://169.254.169.254",
                }
            }
        })


def test_chat_request_rejects_embedding_override():
    with pytest.raises(ValidationError):
        ChatRequest.model_validate({
            "messages": [{"role": "user", "content": "test"}],
            "model": "gemini-2.5-flash-lite",
            "inferenceConfig": {
                "roles": {
                    "answer": {"provider": "google", "model": "gemini-3.1-flash-lite"}
                },
                "embedding": {"provider": "google", "model": "anything"},
            },
        })


def test_chat_request_defaults_candidate_k_to_reduced_workload():
    request = ChatRequest.model_validate({
        "messages": [{"role": "user", "content": "test"}],
        "model": "gemini-3.1-flash-lite",
    })

    assert request.candidateK == 10
    assert request.topK == 5


def test_chat_request_rejects_candidate_k_below_top_k():
    with pytest.raises(ValidationError):
        ChatRequest.model_validate({
            "messages": [{"role": "user", "content": "test"}],
            "model": "gemini-3.1-flash-lite",
            "candidateK": 10,
            "topK": 12,
        })


def test_runtime_google_key_overrides_environment_key(monkeypatch):
    _patch_chat_factory(monkeypatch)
    config = _runtime_config()

    llm = llm_module.get_llm(
        "deepseek-ai/DeepSeek-R1-Distill-Llama-8B",
        runtime_config=config,
        role="answer",
    )

    assert llm.model == "gemini-3.1-flash-lite"
    assert llm.api_key == "runtime-google-token"
    assert llm.fallbacks == []


def test_runtime_role_routing(monkeypatch):
    _patch_chat_factory(monkeypatch)
    config = RuntimeInferenceConfig.model_validate({
        "credentials": {
            "google": {"apiKey": "runtime-google-token"},
            "huggingface": {"apiKey": "runtime-hf-token"},
        },
        "roles": {
            "answer": {"provider": "google", "model": "gemini-3.1-flash-lite"},
            "rewriter": {"provider": "huggingface", "model": "Qwen/Qwen2.5-7B-Instruct"},
            "summarizer": {"provider": "google", "model": "gemini-3.1-flash-lite"},
        },
        "useServerFallbacks": False,
    })

    answer = llm_module.get_llm("unused", runtime_config=config, role="answer")
    rewriter = llm_module.get_llm("unused", runtime_config=config, role="rewriter")
    summarizer = llm_module.get_llm("unused", runtime_config=config, role="summarizer")

    assert answer.model == "gemini-3.1-flash-lite"
    assert answer.api_key == "runtime-google-token"
    assert rewriter.model == "Qwen/Qwen2.5-7B-Instruct"
    assert rewriter.api_key == "runtime-hf-token"
    assert summarizer.model == "gemini-3.1-flash-lite"


def test_missing_runtime_key_without_server_fallback_raises(monkeypatch):
    _patch_chat_factory(monkeypatch)
    monkeypatch.setattr(llm_module, "GOOGLE_API_KEY", "")
    config = RuntimeInferenceConfig.model_validate({
        "roles": {
            "answer": {"provider": "google", "model": "gemini-3.1-flash-lite"}
        },
        "useServerFallbacks": False,
    })

    with pytest.raises(RuntimeError):
        llm_module.get_llm("deepseek-ai/DeepSeek-R1-Distill-Llama-8B", runtime_config=config)


def test_redacts_runtime_api_keys():
    config = _runtime_config()

    redacted = redact_runtime_inference_config(config)

    assert redacted["credentials"]["google"]["apiKey"] == "<redacted>"
    assert "runtime-google-token" not in str(redacted)
