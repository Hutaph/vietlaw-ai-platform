from types import SimpleNamespace

import asyncio

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.api.chat import chat_endpoint
import app.main as main_module
from app.models import ChatRequest


class DummyRewriter:
    def rewrite(self, query, history_str):
        return "all", [query]

class DummyPipeline:
    def __init__(self):
        self.rewriter = DummyRewriter()

    async def aretrieve(self, query, category=None, **kwargs):
        return [SimpleNamespace(page_content="Nội dung mẫu", metadata={"id": "1"})], "Tài liệu tham khảo"

    def format_for_frontend(self, docs):
        return [
            {
                "content": doc.page_content,
                "metadata": {"id": doc.metadata["id"], "source": "Luật thử nghiệm", "dieu": 1},
            }
            for doc in docs
        ]


class _FakePrompt:
    def __init__(self, text):
        self.text = text

    def __or__(self, other):
        return self

    async def ainvoke(self, payload):
        return self.text


def test_chat_returns_http_error_when_llm_is_unavailable(monkeypatch):
    async def immediate_to_thread(func, /, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(main_module, "LOCAL_MODELS_PRELOAD_ENABLED", False)
    monkeypatch.setattr(main_module, "LOCAL_MODELS_WARMUP_ENABLED", False)
    monkeypatch.setattr(main_module, "load_knowledge_base", lambda: None)
    monkeypatch.setattr(main_module, "initialize_storage", lambda: None)
    monkeypatch.setattr(main_module, "init_pipeline", lambda: None)
    monkeypatch.setattr("app.api.chat.asyncio.to_thread", immediate_to_thread)
    monkeypatch.setattr("app.api.chat.get_pipeline", lambda: DummyPipeline())
    monkeypatch.setattr("app.api.chat.get_llm", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("LLM unavailable")))
    monkeypatch.setattr("app.services.pipeline._get_embedding", lambda *args, **kwargs: None)

    request = ChatRequest.model_validate({
        "messages": [{"role": "user", "content": "Câu hỏi mẫu"}],
        "model": "default",
        "category": "all",
        "enableMemory": False,
        "enableSemanticCache": False,
    })
    http_request = Request({"type": "http", "method": "POST", "path": "/chat", "headers": []})

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(chat_endpoint(request, http_request))

    assert exc_info.value.status_code == 503
    assert "dịch vụ suy luận" in exc_info.value.detail.lower()


def _run_chat_with_answer(monkeypatch, answer_text):
    persisted = {}

    async def fake_persist(request, session_id, user_content, ai_content, ai_context):
        persisted["text"] = ai_content
        persisted["context"] = ai_context

    monkeypatch.setattr("app.api.chat.get_pipeline", lambda: DummyPipeline())
    monkeypatch.setattr("app.api.chat.get_llm", lambda **kwargs: object())
    monkeypatch.setattr("app.api.chat.CHAT_PROMPT", _FakePrompt(answer_text))
    monkeypatch.setattr("app.api.chat.get_output_parser", lambda: object())
    monkeypatch.setattr("app.api.chat._persist_completed_turn", fake_persist)
    monkeypatch.setattr("app.services.pipeline._get_embedding", lambda *args, **kwargs: None)

    request = ChatRequest.model_validate({
        "messages": [{"role": "user", "content": "Câu hỏi mẫu"}],
        "model": "default",
        "category": "all",
        "enableMemory": False,
        "enableSemanticCache": False,
    })
    http_request = Request({"type": "http", "method": "POST", "path": "/chat", "headers": []})

    response = asyncio.run(chat_endpoint(request, http_request))
    return response, persisted


def test_chat_response_and_persistence_keep_valid_citation(monkeypatch):
    response, persisted = _run_chat_with_answer(
        monkeypatch,
        'Theo <cite id="1">Điều 1</cite>, nội dung mẫu.',
    )

    assert '<cite id="1">Điều 1</cite>' in response["text"]
    assert response["text"] == persisted["text"]
    assert [item["metadata"]["id"] for item in response["contextUsed"]] == ["1"]


def test_chat_response_and_persistence_sanitize_invalid_citation(monkeypatch):
    response, persisted = _run_chat_with_answer(
        monkeypatch,
        'Theo <cite id="FAKE_2024_D999">Điều 999</cite>, có nghĩa vụ.',
    )

    assert "FAKE_2024_D999" not in response["text"]
    assert response["text"] == persisted["text"]
    assert "chưa cung cấp đủ căn cứ pháp lý" in response["text"]


def test_chat_response_and_persistence_keep_valid_from_mixed_citations(monkeypatch):
    response, persisted = _run_chat_with_answer(
        monkeypatch,
        'Theo <cite id="1">Điều 1</cite> và <cite id="FAKE_2024_D999">Điều 999</cite>.',
    )

    assert '<cite id="1">Điều 1</cite>' in response["text"]
    assert "FAKE_2024_D999" not in response["text"]
    assert response["text"] == persisted["text"]
