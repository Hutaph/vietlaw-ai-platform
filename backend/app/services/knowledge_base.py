"""
In-memory legal knowledge base.
Separated from vectorstore.py so other modules can access legal metadata
without depending on a vector store.
"""
import os
import json
import glob
from pathlib import Path
from typing import Dict, Any, Iterable, List, Optional

from app.config import CORPUS_EMBED_LEVELS, CORPUS_JSONL_PATH, JSON_DATA_PATH
from app.utils.logging import setup_logger

logger = setup_logger("vietlaw.knowledge_base")

# --- Module-level state ---
KNOWLEDGE_BASE: Dict[str, Any] = {}
LAW_METADATA: Dict[str, Any] = {}

ALL_LAWS_CATEGORY = "all"
CIVIL_CATEGORY = "civil"
FAMILY_PERSONAL_CATEGORY = "family-personal"
LAND_CATEGORY = "land"
REAL_ESTATE_CATEGORY = "real-estate"
CONSTRUCTION_ENVIRONMENT_CATEGORY = "construction-environment"
TRAFFIC_CATEGORY = "traffic"
PUBLIC_ORDER_SANCTIONS_CATEGORY = "public-order-sanctions"

_CATEGORY_LAW_IDS = {
    CIVIL_CATEGORY: {"BLTTDS_2015"},
    FAMILY_PERSONAL_CATEGORY: set(),
    LAND_CATEGORY: {"LDD_2024"},
    REAL_ESTATE_CATEGORY: {"LKDBDS_2023", "LNO_2023"},
    CONSTRUCTION_ENVIRONMENT_CATEGORY: {"LXD_2014", "LBVMT_2020"},
    TRAFFIC_CATEGORY: set(),
    PUBLIC_ORDER_SANCTIONS_CATEGORY: set(),
}

_LEGACY_CATEGORY_ALIASES = {
    "Chung": ALL_LAWS_CATEGORY,
    "Tất cả các luật": ALL_LAWS_CATEGORY,
    "Tất cả văn bản": ALL_LAWS_CATEGORY,
    "Dân sự": CIVIL_CATEGORY,
    "Gia đình & Nhân thân": FAMILY_PERSONAL_CATEGORY,
    "Đất đai": LAND_CATEGORY,
    "Bất động sản": REAL_ESTATE_CATEGORY,
    "Xây dựng & Môi trường": CONSTRUCTION_ENVIRONMENT_CATEGORY,
    "Giao thông": TRAFFIC_CATEGORY,
    "Trật tự & Xử phạt": PUBLIC_ORDER_SANCTIONS_CATEGORY,
    "Kinh doanh": REAL_ESTATE_CATEGORY,
    "Bảo vệ môi trường": CONSTRUCTION_ENVIRONMENT_CATEGORY,
    "Môi trường": CONSTRUCTION_ENVIRONMENT_CATEGORY,
    "Tố tụng dân sự": CIVIL_CATEGORY,
    "Nhà ở": REAL_ESTATE_CATEGORY,
    "Nhà ở & Xây dựng": REAL_ESTATE_CATEGORY,
    "Kinh doanh bất động sản": REAL_ESTATE_CATEGORY,
    "civil-family-personal": CIVIL_CATEGORY,
    "land-property-environment": LAND_CATEGORY,
    "housing-construction": REAL_ESTATE_CATEGORY,
    "real-estate-business": REAL_ESTATE_CATEGORY,
    "environment": CONSTRUCTION_ENVIRONMENT_CATEGORY,
    "civil-procedure": CIVIL_CATEGORY,
}


def _merge_position(record: Dict[str, Any]) -> Dict[str, Any]:
    hierarchy = record.get("hierarchy")
    position = dict(hierarchy) if isinstance(hierarchy, dict) else {}
    for key in ("level", "number", "title", "citation_label", "order_index"):
        value = record.get(key)
        if value not in (None, ""):
            position[key] = value
    return position


def _display_law_name(record: Dict[str, Any], fallback: str) -> str:
    title = str(record.get("title") or "").strip()
    citation_label = str(record.get("citation_label") or "").strip()
    level = str(record.get("level") or "").strip()

    if level == "document" and title:
        return title
    if level == "document" and citation_label:
        return citation_label
    return fallback


def _iter_legacy_json_clauses(json_data_path: str | Path = JSON_DATA_PATH) -> Iterable[Dict[str, Any]]:
    for file_path in Path(json_data_path).glob("*.json"):
        with file_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        law_info = data.get("law_info", {})
        law_id = law_info.get("law_id")
        law_name = law_info.get("law_name", "")
        for clause in data.get("clauses", []):
            source_id = clause.get("id")
            content = clause.get("content", "")
            if not source_id or not law_id:
                continue
            yield {
                "id": source_id,
                "law_id": law_id,
                "law_name": law_name,
                "summary": law_info.get("executive_summary", ""),
                "category": determine_category(law_name),
                "position": clause.get("position", {}),
                "content": content,
                "cross_references": clause.get("cross_references", []),
            }


def _iter_jsonl_corpus_clauses(corpus_jsonl_path: str | Path = CORPUS_JSONL_PATH) -> Iterable[Dict[str, Any]]:
    law_names: Dict[str, str] = {}
    path = Path(corpus_jsonl_path)
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid corpus JSONL at {path}:{line_number}: {exc}") from exc

            law_id = str(record.get("law_id") or "").strip()
            source_id = str(record.get("node_id") or "").strip()
            content = str(record.get("text") or "").strip()
            level = str(record.get("level") or "").strip().lower()
            if not law_id or not source_id or not content:
                continue

            current_law_name = law_names.get(law_id, law_id)
            law_name = _display_law_name(record, current_law_name)
            if law_name and (record.get("level") == "document" or law_id not in law_names):
                law_names[law_id] = law_name
            if CORPUS_EMBED_LEVELS and level not in CORPUS_EMBED_LEVELS:
                continue

            yield {
                "id": source_id,
                "law_id": law_id,
                "law_name": law_names.get(law_id, law_name or law_id),
                "summary": "",
                "category": determine_category(law_names.get(law_id, law_name or "")),
                "position": _merge_position(record),
                "content": content,
                "cross_references": [],
                "metadata": {
                    "anchors": record.get("anchors", []),
                    "citation_label": record.get("citation_label", ""),
                    "raw_path": record.get("raw_path", ""),
                    "source_url": record.get("source_url", ""),
                    "text_hash": record.get("text_hash", ""),
                },
            }


def determine_category(law_name: str) -> str:
    """Classify a legal document into the frontend category taxonomy."""
    name_lower = law_name.lower()

    if "tố tụng dân sự" in name_lower:
        return CIVIL_CATEGORY
    if "đất đai" in name_lower:
        return LAND_CATEGORY
    if "kinh doanh bất động sản" in name_lower or "nhà ở" in name_lower:
        return REAL_ESTATE_CATEGORY
    if "xây dựng" in name_lower or "môi trường" in name_lower:
        return CONSTRUCTION_ENVIRONMENT_CATEGORY

    return ALL_LAWS_CATEGORY


def normalize_category(category: Optional[str]) -> str:
    """Normalize current category ids and legacy client-provided values."""
    if not category:
        return ALL_LAWS_CATEGORY
    return _LEGACY_CATEGORY_ALIASES.get(category, category)


def document_matches_category(
    metadata: Dict[str, Any],
    category: Optional[str],
) -> bool:
    """Check whether a document matches a category, including legacy FAISS metadata."""
    normalized_category = normalize_category(category)
    if normalized_category == ALL_LAWS_CATEGORY:
        return True

    law_id = metadata.get("law_id")
    
    if normalized_category.upper() in ["LKDBDS_2023", "LTTPHS_2025", "LNO_2023", "LBVMT_2020", "LXD_2014", "LDD_2024", "LCC_2024", "BLTTDS_2015"]:
        return law_id == normalized_category.upper()
        
    allowed_law_ids = _CATEGORY_LAW_IDS.get(normalized_category)
    if allowed_law_ids is not None:
        return law_id in allowed_law_ids

    law_metadata = LAW_METADATA.get(law_id, {})
    document_category = law_metadata.get("category")

    if not document_category:
        document_category = normalize_category(metadata.get("category"))

    return document_category == normalized_category


def load_knowledge_base() -> None:
    """Load the corpus into RAM for context building and document metadata."""
    global KNOWLEDGE_BASE, LAW_METADATA
    KNOWLEDGE_BASE.clear()
    LAW_METADATA.clear()

    corpus_jsonl = Path(CORPUS_JSONL_PATH)
    if corpus_jsonl.exists():
        logger.info("Đang nạp corpus JSONL vào bộ nhớ: %s", corpus_jsonl)
        clause_iterable = _iter_jsonl_corpus_clauses(corpus_jsonl)
    else:
        json_files = glob.glob(os.path.join(JSON_DATA_PATH, "*.json"))
        logger.info("Đang nạp %d file JSON legacy vào bộ nhớ...", len(json_files))
        clause_iterable = _iter_legacy_json_clauses(JSON_DATA_PATH)

    for clause in clause_iterable:
        law_id = clause["law_id"]
        law_name = clause.get("law_name", law_id)
        LAW_METADATA.setdefault(
            law_id,
            {
                "law_name": law_name,
                "summary": clause.get("summary", ""),
                "category": clause.get("category") or determine_category(law_name),
            },
        )
        if law_name and LAW_METADATA[law_id].get("law_name") in ("", law_id):
            LAW_METADATA[law_id]["law_name"] = law_name
            LAW_METADATA[law_id]["category"] = determine_category(law_name)

        KNOWLEDGE_BASE[clause["id"]] = {
            "law_id": law_id,
            "position": clause.get("position", {}),
            "content": clause.get("content", ""),
            "cross_references": clause.get("cross_references", []),
            "metadata": clause.get("metadata", {}),
        }

    logger.info(
        "Nạp dữ liệu vào RAM hoàn tất! (%d điều khoản, %d văn bản)",
        len(KNOWLEDGE_BASE), len(LAW_METADATA)
    )


def get_clause(clause_id: str) -> Optional[Dict[str, Any]]:
    """Return one clause by id."""
    return KNOWLEDGE_BASE.get(clause_id)


def get_law_metadata(law_id: str) -> Optional[Dict[str, Any]]:
    """Return legal document metadata by law id."""
    return LAW_METADATA.get(law_id)


def resolve_reference_data(target_id: str) -> List[Dict[str, Any]]:
    """Resolve one exact clause or collect all clauses under an article."""
    if target_id in KNOWLEDGE_BASE:
        return [KNOWLEDGE_BASE[target_id]]

    results = []
    search_prefix = f"{target_id}_"
    for k, v in KNOWLEDGE_BASE.items():
        if k.startswith(search_prefix):
            results.append(v)
    return results
