import app.services.llm as llm_module


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
    monkeypatch.setattr(llm_module, "HUGGINGFACE_API_KEY", "hf-token")
    monkeypatch.setattr(llm_module, "GOOGLE_API_KEY", "google-token")
    monkeypatch.setattr(llm_module, "GOOGLE_FALLBACK_MODEL", "gemini-3.1-flash-lite")
    monkeypatch.setattr(
        llm_module,
        "GOOGLE_OPENAI_BASE_URL",
        "https://generativelanguage.googleapis.com/v1beta/openai/",
    )
    monkeypatch.setattr(llm_module, "ENABLE_GOOGLE_FALLBACK", True)


def test_google_model_detection():
    assert llm_module.is_google_chat_model("gemini-3.1-flash-lite")
    assert not llm_module.is_google_chat_model("gemini-2.5-flash-lite")
    assert not llm_module.is_google_chat_model("google/gemma-4-31B-it")


def test_selected_google_model_uses_google_endpoint(monkeypatch):
    _patch_chat_factory(monkeypatch)
    monkeypatch.setattr(llm_module, "INFERENCE_STRATEGY", "remote_first")

    llm = llm_module.get_llm("gemini-3.1-flash-lite")

    assert llm.model == "gemini-3.1-flash-lite"
    assert llm.api_key == "google-token"
    assert llm.base_url == "https://generativelanguage.googleapis.com/v1beta/openai/"


def test_remote_first_does_not_add_local_fallback(monkeypatch):
    _patch_chat_factory(monkeypatch)
    monkeypatch.setattr(llm_module, "INFERENCE_STRATEGY", "remote_first")

    llm = llm_module.get_llm("Qwen/Qwen2.5-7B-Instruct")

    assert llm.model == "Qwen/Qwen2.5-7B-Instruct"
    assert [fallback.model for fallback in llm.fallbacks] == [
        "gemini-3.1-flash-lite",
    ]


def test_local_first_adds_google_as_final_fallback(monkeypatch):
    _patch_chat_factory(monkeypatch)
    monkeypatch.setattr(llm_module, "INFERENCE_STRATEGY", "local_first")

    llm = llm_module.get_llm("Qwen/Qwen2.5-7B-Instruct")

    assert llm.model == "qwen2.5:7b-instruct"
    assert [fallback.model for fallback in llm.fallbacks] == [
        "Qwen/Qwen2.5-7B-Instruct",
        "gemini-3.1-flash-lite",
    ]


def test_missing_google_key_without_local_fallback_raises(monkeypatch):
    _patch_chat_factory(monkeypatch)
    monkeypatch.setattr(llm_module, "INFERENCE_STRATEGY", "remote_first")
    monkeypatch.setattr(llm_module, "GOOGLE_API_KEY", "")

    import pytest

    with pytest.raises(RuntimeError):
        llm_module.get_llm("gemini-3.1-flash-lite")


def test_unsupported_google_model_raises_clear_error(monkeypatch):
    _patch_chat_factory(monkeypatch)

    import pytest

    with pytest.raises(ValueError, match="Unsupported Google model"):
        llm_module.get_llm("gemini-2.5-flash-lite")


def test_duplicate_google_fallback_model_is_not_retried(monkeypatch):
    _patch_chat_factory(monkeypatch)
    monkeypatch.setattr(llm_module, "INFERENCE_STRATEGY", "remote_first")
    monkeypatch.setattr(llm_module, "GOOGLE_FALLBACK_MODEL", "gemini-3.1-flash-lite")

    llm = llm_module.get_llm("gemini-3.1-flash-lite")

    assert llm.fallbacks == []
