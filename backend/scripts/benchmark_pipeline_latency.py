"""Client-side benchmark helper for pipeline latency instrumentation.

The backend must already be running with PIPELINE_TIMING_ENABLED=true.
This script does not mutate runtime config and does not print credentials.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import time
import uuid
from typing import Iterable
from urllib import error, request


def environment_snapshot() -> dict:
    snapshot = {
        "os": platform.platform(),
        "cpu": platform.processor() or "unknown",
        "logical_cores": os.cpu_count(),
        "omp_num_threads": os.environ.get("OMP_NUM_THREADS"),
        "mkl_num_threads": os.environ.get("MKL_NUM_THREADS"),
        "tokenizers_parallelism": os.environ.get("TOKENIZERS_PARALLELISM"),
        "python": platform.python_version(),
    }
    try:
        import psutil  # type: ignore

        snapshot["total_ram_gb"] = round(psutil.virtual_memory().total / (1024 ** 3), 2)
        snapshot["physical_cores"] = psutil.cpu_count(logical=False)
    except Exception:
        snapshot["total_ram_gb"] = None
        snapshot["physical_cores"] = None

    try:
        import torch

        snapshot["torch"] = torch.__version__
        snapshot["torch_num_threads"] = torch.get_num_threads()
        snapshot["torch_num_interop_threads"] = torch.get_num_interop_threads()
        snapshot["cuda_available"] = torch.cuda.is_available()
    except Exception:
        snapshot["torch"] = None
        snapshot["torch_num_threads"] = None
        snapshot["torch_num_interop_threads"] = None
        snapshot["cuda_available"] = None

    return snapshot


def _payload(question: str, streaming: bool, model: str, candidate_k: int, top_k: int) -> dict:
    return {
        "messages": [{"role": "user", "content": question}],
        "model": model,
        "category": "all",
        "temperature": 0.1,
        "maxTokens": 1500,
        "topK": top_k,
        "candidateK": candidate_k,
        "streaming": streaming,
        "enableQueryRewriter": False,
        "enableReranker": True,
        "enableSemanticCache": False,
        "enableMemory": False,
    }


def _iter_sse_lines(response) -> Iterable[str]:
    for raw_line in response:
        line = raw_line.decode("utf-8", errors="replace").strip()
        if line.startswith("data: "):
            yield line[6:]


def run_once(base_url: str, endpoint: str, question: str, timeout: float, model: str, candidate_k: int, top_k: int) -> dict:
    streaming = endpoint.endswith("/stream")
    request_id = f"bench-{uuid.uuid4()}"
    body = json.dumps(_payload(question, streaming, model, candidate_k, top_k), ensure_ascii=False).encode("utf-8")
    req = request.Request(
        f"{base_url.rstrip('/')}{endpoint}",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Request-ID": request_id,
        },
    )

    start = time.perf_counter()
    first_token_at = None
    status = None
    token_count = 0
    context_events = 0
    final_context_ids = []
    error_event = None
    try:
        with request.urlopen(req, timeout=timeout) as response:
            status = response.status
            if streaming:
                for raw in _iter_sse_lines(response):
                    try:
                        event = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    if event.get("type") == "context":
                        context_events += 1
                        final_context_ids = [
                            item.get("id")
                            for item in event.get("data", [])
                            if isinstance(item, dict) and item.get("id")
                        ]
                    elif event.get("type") == "token":
                        token_count += 1
                        if first_token_at is None:
                            first_token_at = time.perf_counter()
                    elif event.get("type") == "error":
                        error_event = event.get("message", "error")
                    elif event.get("type") == "done":
                        break
            else:
                data = json.loads(response.read().decode("utf-8"))
                token_count = 1 if data.get("text") else 0
                final_context_ids = [
                    item.get("id")
                    for item in data.get("contextUsed", [])
                    if isinstance(item, dict) and item.get("id")
                ]
    except error.HTTPError as exc:
        status = exc.code
        error_event = f"HTTP {exc.code}"
    total_ms = (time.perf_counter() - start) * 1000
    ttft_ms = (first_token_at - start) * 1000 if first_token_at is not None else None
    return {
        "request_id": request_id,
        "endpoint": endpoint,
        "status": status,
        "client_total_ms": round(total_ms, 3),
        "client_time_to_first_token_ms": round(ttft_ms, 3) if ttft_ms is not None else None,
        "token_events": token_count,
        "context_events": context_events,
        "final_context_ids": final_context_ids,
        "error": error_event,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark chat pipeline latency against a running backend.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--endpoint", default="/chat/stream", choices=["/chat", "/chat/stream"])
    parser.add_argument("--question", action="append", default=[])
    parser.add_argument("--timeout", type=float, default=300)
    parser.add_argument("--model", default="gemini-3.1-flash-lite")
    parser.add_argument("--candidate-k", type=int, default=10)
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    questions = args.question or [
        "Hợp đồng chuyển nhượng quyền sử dụng đất có bắt buộc phải công chứng không?",
        "Điều kiện chuyển nhượng quyền sử dụng đất theo pháp luật hiện hành là gì?",
        "Hợp đồng chuyển nhượng quyền sử dụng đất có bắt buộc phải công chứng không?",
    ]

    results = [
        run_once(args.base_url, args.endpoint, question, args.timeout, args.model, args.candidate_k, args.top_k)
        for question in questions
    ]
    print(json.dumps({"environment": environment_snapshot(), "results": results}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
