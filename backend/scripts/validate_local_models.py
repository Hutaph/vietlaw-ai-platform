#!/usr/bin/env python
"""Validate local embedding and reranker artifacts without Qdrant/Postgres."""
from __future__ import annotations

import argparse
import gc
import math
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _set_offline_env() -> None:
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")


def _required(path: Path, files: list[str]) -> None:
    missing = [name for name in files if not (path / name).exists()]
    if missing:
        raise FileNotFoundError(f"{path} is missing required files: {', '.join(missing)}")


def validate_embedding(path: Path, dimension: int) -> None:
    _required(
        path,
        [
            "config.json",
            "modules.json",
            "tokenizer.json",
            "tokenizer_config.json",
            "special_tokens_map.json",
            "model.safetensors",
        ],
    )

    from sentence_transformers import SentenceTransformer

    start = time.perf_counter()
    model = SentenceTransformer(str(path), device="cpu", local_files_only=True)
    load_time = time.perf_counter() - start

    samples = [
        "Điều kiện chuyển nhượng quyền sử dụng đất là gì?",
        "Hợp đồng mua bán nhà ở cần những điều kiện nào?",
    ]
    start = time.perf_counter()
    vectors = model.encode(
        samples,
        batch_size=2,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    inference_time = time.perf_counter() - start

    if vectors.shape != (2, dimension):
        raise RuntimeError(f"Embedding shape mismatch: expected (2, {dimension}), got {vectors.shape}.")
    if not bool((vectors == vectors).all()):
        raise RuntimeError("Embedding output contains NaN.")
    norms = [float((vector ** 2).sum() ** 0.5) for vector in vectors]
    if not all(math.isfinite(norm) for norm in norms):
        raise RuntimeError("Embedding output norm is not finite.")

    print(f"Embedding OK path={path}")
    print(f"  shape={tuple(vectors.shape)} norms={[round(norm, 6) for norm in norms]}")
    print(f"  load_time={load_time:.2f}s inference_time={inference_time:.2f}s offline=1")

    del model
    gc.collect()


def validate_reranker(path: Path) -> None:
    _required(
        path,
        [
            "config.json",
            "model.safetensors",
            "tokenizer.json",
            "tokenizer_config.json",
            "special_tokens_map.json",
            "sentencepiece.bpe.model",
        ],
    )

    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    query = "Điều kiện chuyển nhượng quyền sử dụng đất là gì?"
    relevant = "Người sử dụng đất được thực hiện quyền chuyển nhượng khi có Giấy chứng nhận và đất không có tranh chấp."
    irrelevant = "Luật này quy định về hoạt động bảo vệ môi trường và quản lý chất thải."

    start = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(str(path), local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(str(path), local_files_only=True)
    model.eval()
    load_time = time.perf_counter() - start

    encoded = tokenizer(
        [(query, relevant), (query, irrelevant)],
        padding=True,
        truncation=True,
        max_length=512,
        return_tensors="pt",
    )

    start = time.perf_counter()
    with torch.inference_mode():
        logits = model(**encoded).logits
    inference_time = time.perf_counter() - start

    if tuple(logits.shape) != (2, 1):
        raise RuntimeError(f"Reranker logits shape mismatch: expected (2, 1), got {tuple(logits.shape)}.")
    scores = logits[:, 0].detach().cpu().float().tolist()
    if not all(math.isfinite(float(score)) for score in scores):
        raise RuntimeError("Reranker logits contain NaN or Inf.")

    print(f"Reranker OK path={path}")
    print(f"  logits_shape={tuple(logits.shape)} relevant_score={scores[0]:.6f} irrelevant_score={scores[1]:.6f}")
    print(f"  load_time={load_time:.2f}s inference_time={inference_time:.2f}s offline=1")
    print("  note=smoke test only; best reranker is not selected")

    del model
    del tokenizer
    gc.collect()


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate local fine-tuned embedding/reranker artifacts.")
    parser.add_argument("--embedding-path", type=Path)
    parser.add_argument("--reranker-path", type=Path, action="append", default=[])
    parser.add_argument("--dimension", type=int, default=1024)
    parser.add_argument("--skip-embedding", action="store_true")
    parser.add_argument("--skip-reranker", action="store_true")
    parser.add_argument("--offline", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()

    if args.offline:
        _set_offline_env()

    try:
        if args.embedding_path and not args.skip_embedding:
            validate_embedding(args.embedding_path, args.dimension)
        if not args.skip_reranker:
            for reranker_path in args.reranker_path:
                validate_reranker(reranker_path)
        return 0
    except Exception as exc:
        print(f"Local model validation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
