"""Read-only legal corpus integrity audit.

This script never mutates PostgreSQL or Qdrant. It can be run against local JSON
only, or with optional database/vector checks when credentials are available.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import JSON_DATA_PATH


def _load_json_corpus(json_data_path: str | Path) -> dict[str, dict[str, Any]]:
    clauses: dict[str, dict[str, Any]] = {}
    for file_path in Path(json_data_path).glob("*.json"):
        with file_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        law = data.get("law_info", {})
        for clause in data.get("clauses", []):
            source_id = clause.get("id")
            if not source_id:
                continue
            clauses[source_id] = {
                "law_id": law.get("law_id"),
                "law_name": law.get("law_name"),
                "position": clause.get("position", {}),
                "content": clause.get("content", ""),
                "file": str(file_path),
            }
    return clauses


def audit_json_corpus(json_data_path: str | Path = JSON_DATA_PATH) -> dict[str, Any]:
    clauses = _load_json_corpus(json_data_path)
    source_ids = list(clauses)
    identity_counts = Counter()
    for clause in clauses.values():
        pos = clause.get("position", {})
        identity_counts[
            (
                clause.get("law_id"),
                str(pos.get("article", "")),
                str(pos.get("clause", "")),
                str(pos.get("point", "")),
            )
        ] += 1

    duplicate_id_counts = Counter(source_ids)
    empty_text_ids = [source_id for source_id, clause in clauses.items() if not str(clause.get("content", "")).strip()]
    malformed_metadata_ids = []
    for source_id, clause in clauses.items():
        pos = clause.get("position", {})
        if not clause.get("law_id") or not pos or pos.get("article") in (None, ""):
            malformed_metadata_ids.append(source_id)
    collisions = [
        "|".join(identity)
        for identity, count in identity_counts.items()
        if count > 1 and any(identity)
    ]
    return {
        "json_clause_count": len(clauses),
        "duplicate_source_ids": [source_id for source_id, count in duplicate_id_counts.items() if count > 1],
        "empty_text_ids": empty_text_ids,
        "malformed_metadata_ids": malformed_metadata_ids,
        "law_article_clause_collisions": collisions,
        "known_sources": {
            source_id: {
                "present": source_id in clauses,
                "law_id": clauses.get(source_id, {}).get("law_id"),
                "position": clauses.get(source_id, {}).get("position"),
                "empty_text": not bool(str(clauses.get(source_id, {}).get("content", "")).strip()),
            }
            for source_id in ("LDD_2024_D27_K3", "LDD_2024_D45_K1")
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit tracked legal corpus integrity in read-only mode.")
    parser.add_argument("--json-data-path", default=JSON_DATA_PATH)
    parser.add_argument("--output", default="/tmp/vietlaw-quality-improvements/corpus-integrity.json")
    args = parser.parse_args()

    report = audit_json_corpus(args.json_data_path)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output), "json_clause_count": report["json_clause_count"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
