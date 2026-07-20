"""
Backward-compatible module.
Real logic lives in:
  - app/services/knowledge_base.py
  - app/services/embedding/
  - app/services/search/
  - app/services/pipeline.py
This file exists to avoid breaking older imports.
"""
from app.services.pipeline import get_pipeline, init_pipeline  # noqa: F401
