"""Request-scoped timing utilities for the chat retrieval pipeline."""
from __future__ import annotations

import json
import os
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, Optional

from app.config import PIPELINE_CONFIG
from app.utils.logging import setup_logger

logger = setup_logger("vietlaw.pipeline.timing")

_current_timing: ContextVar["PipelineTimingCollector | None"] = ContextVar(
    "pipeline_timing",
    default=None,
)


def sanitize_request_id(value: str | None) -> str:
    if not value:
        return str(uuid.uuid4())
    safe = "".join(ch for ch in value.strip() if ch.isalnum() or ch in "-_:.")
    return safe[:80] or str(uuid.uuid4())


def current_timing() -> "PipelineTimingCollector | None":
    return _current_timing.get()


def set_current_timing(collector: "PipelineTimingCollector | None"):
    return _current_timing.set(collector)


def reset_current_timing(token) -> None:
    _current_timing.reset(token)


@dataclass
class PipelineTimingCollector:
    request_id: str
    endpoint: str
    streaming: bool
    enabled: bool = False
    process_id: int = field(default_factory=os.getpid)
    _started_ns: int = field(default_factory=time.perf_counter_ns)
    _first_token_ns: Optional[int] = None
    _emitted: bool = False
    _durations_ms: Dict[str, float] = field(default_factory=dict)
    _metrics: Dict[str, Any] = field(default_factory=dict)
    _cold_flags: Dict[str, bool] = field(
        default_factory=lambda: {
            "embedding_was_cold": False,
            "reranker_was_cold": False,
        }
    )

    @contextmanager
    def stage(self, name: str) -> Iterator[None]:
        start_ns = time.perf_counter_ns()
        try:
            yield
        finally:
            self.add_duration(name, self._elapsed_ms(start_ns, time.perf_counter_ns()))

    @staticmethod
    def _elapsed_ms(start_ns: int, end_ns: int) -> float:
        return max(0.0, (end_ns - start_ns) / 1_000_000)

    def add_duration(self, name: str, duration_ms: float) -> None:
        if duration_ms < 0:
            duration_ms = 0.0
        self._durations_ms[name] = self._durations_ms.get(name, 0.0) + duration_ms

    def mark_embedding_model_load(self, duration_ms: float) -> None:
        self.add_duration("embedding_model_load", duration_ms)
        self._cold_flags["embedding_was_cold"] = True

    def mark_reranker_model_load(self, duration_ms: float) -> None:
        self.add_duration("reranker_model_load", duration_ms)
        self._cold_flags["reranker_was_cold"] = True

    def mark_first_token(self) -> None:
        if self._first_token_ns is None:
            self._first_token_ns = time.perf_counter_ns()
            self._durations_ms["total_time_to_first_token"] = self._elapsed_ms(
                self._started_ns,
                self._first_token_ns,
            )

    def set_metric(self, name: str, value: Any) -> None:
        self._metrics[name] = value

    def payload(self, outcome: str) -> dict:
        now_ns = time.perf_counter_ns()
        durations = dict(self._durations_ms)
        durations["model_load"] = durations.get("embedding_model_load", 0.0) + durations.get("reranker_model_load", 0.0)
        durations["total"] = self._elapsed_ms(self._started_ns, now_ns)

        if self.streaming and "llm_generation" in durations and "llm_time_to_first_token" in durations:
            durations.setdefault(
                "llm_stream_after_first_token",
                max(0.0, durations["llm_generation"] - durations["llm_time_to_first_token"]),
            )

        embedding_cold = self._cold_flags["embedding_was_cold"]
        reranker_cold = self._cold_flags["reranker_was_cold"]
        return {
            "event": "pipeline_timing",
            "request_id": self.request_id,
            "endpoint": self.endpoint,
            "streaming": self.streaming,
            "outcome": outcome,
            "request_was_cold": embedding_cold or reranker_cold,
            "embedding_was_cold": embedding_cold,
            "reranker_was_cold": reranker_cold,
            "process_id": self.process_id,
            "config": {
                "candidate_k": PIPELINE_CONFIG.get("reranker_max_candidates"),
                "reranker_batch_size": PIPELINE_CONFIG.get("reranker_batch_size"),
                "reranker_max_length": PIPELINE_CONFIG.get("reranker_max_length"),
                "reranking": PIPELINE_CONFIG.get("reranking"),
            },
            "metrics": dict(self._metrics),
            "durations_ms": {key: round(value, 3) for key, value in sorted(durations.items())},
        }

    def emit_once(self, outcome: str) -> None:
        if self._emitted or not self.enabled:
            return
        self._emitted = True
        logger.info(json.dumps(self.payload(outcome), ensure_ascii=False, sort_keys=True))
