import asyncio

from fastapi import HTTPException

import app.main as main_module


def _app_without_startup_side_effects(monkeypatch, *, preload_enabled=False, warmup_enabled=False):
    async def immediate_to_thread(func, /, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(main_module, "LOCAL_MODELS_PRELOAD_ENABLED", preload_enabled)
    monkeypatch.setattr(main_module, "LOCAL_MODELS_WARMUP_ENABLED", warmup_enabled)
    monkeypatch.setattr(main_module.asyncio, "to_thread", immediate_to_thread)
    monkeypatch.setattr(main_module, "load_knowledge_base", lambda: None)
    monkeypatch.setattr(main_module, "initialize_storage", lambda: None)
    monkeypatch.setattr(main_module, "init_pipeline", lambda: None)
    monkeypatch.setattr(main_module, "preload_local_models", lambda warmup=False: {})
    app = main_module.create_app()
    app.router.on_startup.clear()
    return app


def _route_endpoint(app, path):
    for route in app.routes:
        if getattr(route, "path", None) == path:
            return route.endpoint
    raise AssertionError(f"route {path} not found")


def _call_route(app, path):
    return asyncio.run(_route_endpoint(app, path)())


def test_health_is_fast_and_does_not_call_dependencies(monkeypatch):
    app = _app_without_startup_side_effects(monkeypatch)

    def fail_if_called():
        raise AssertionError("readiness dependency should not be called by /health")

    monkeypatch.setattr(main_module, "_check_artifacts", fail_if_called)
    monkeypatch.setattr(main_module, "_check_postgres", fail_if_called)
    monkeypatch.setattr(main_module, "_check_qdrant", fail_if_called)

    response = _call_route(app, "/health")

    assert response == {"status": "ok"}


def test_readiness_success_with_mocked_dependencies(monkeypatch):
    app = _app_without_startup_side_effects(monkeypatch)
    monkeypatch.setattr(
        main_module,
        "_check_artifacts",
        lambda: {
            "embedding": {"status": "ok", "configured": True, "weights": True},
            "reranker": {"status": "ok", "enabled": True, "weights": True},
        },
    )
    monkeypatch.setattr(
        main_module,
        "_check_postgres",
        lambda: {"status": "ok", "host": "localhost", "port": 15432, "database": "vietlaw"},
    )
    monkeypatch.setattr(
        main_module,
        "_check_qdrant",
        lambda: {
            "status": "ok",
            "host": "qdrant.example",
            "collection": "vietlaw_clauses",
            "points": 5756,
            "denseVector": {"name": "text-dense", "dimension": 1024, "distance": "Cosine"},
        },
    )

    body = _call_route(app, "/readiness")

    assert body["status"] == "ready"
    assert body["components"]["embedding"]["status"] == "ok"
    assert body["components"]["qdrant"]["denseVector"]["dimension"] == 1024


def test_readiness_returns_503_when_required_dependency_fails(monkeypatch):
    app = _app_without_startup_side_effects(monkeypatch)
    monkeypatch.setattr(
        main_module,
        "_check_artifacts",
        lambda: {
            "embedding": {"status": "ok", "configured": True, "weights": True},
            "reranker": {"status": "ok", "enabled": True, "weights": True},
        },
    )
    monkeypatch.setattr(main_module, "_check_postgres", lambda: {"status": "ok"})

    def qdrant_down():
        raise RuntimeError("missing collection")

    monkeypatch.setattr(main_module, "_check_qdrant", qdrant_down)

    try:
        _call_route(app, "/readiness")
    except HTTPException as exc:
        assert exc.status_code == 503
        detail = exc.detail
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("readiness should raise HTTPException")
    assert detail["status"] == "not_ready"
    assert detail["components"]["qdrant"]["status"] == "error"


def test_readiness_waits_for_local_model_preload(monkeypatch):
    app = _app_without_startup_side_effects(monkeypatch, preload_enabled=True, warmup_enabled=True)
    monkeypatch.setattr(main_module, "_check_artifacts", lambda: {"embedding": {"status": "ok"}, "reranker": {"status": "ok"}})
    monkeypatch.setattr(main_module, "_check_postgres", lambda: {"status": "ok"})
    monkeypatch.setattr(main_module, "_check_qdrant", lambda: {"status": "ok", "denseVector": {"dimension": 1024}})

    app.state.local_models_ready = False
    try:
        _call_route(app, "/readiness")
    except HTTPException as exc:
        assert exc.status_code == 503
        detail = exc.detail
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("readiness should raise HTTPException")
    assert detail["components"]["localModels"]["status"] == "error"
    assert detail["components"]["localModels"]["preload"] is True


def test_readiness_allows_ready_local_model_preload(monkeypatch):
    app = _app_without_startup_side_effects(monkeypatch, preload_enabled=True, warmup_enabled=True)
    monkeypatch.setattr(main_module, "_check_artifacts", lambda: {"embedding": {"status": "ok"}, "reranker": {"status": "ok"}})
    monkeypatch.setattr(main_module, "_check_postgres", lambda: {"status": "ok"})
    monkeypatch.setattr(main_module, "_check_qdrant", lambda: {"status": "ok", "denseVector": {"dimension": 1024}})

    app.state.local_models_ready = True
    body = _call_route(app, "/readiness")

    assert body["components"]["localModels"]["status"] == "ok"
