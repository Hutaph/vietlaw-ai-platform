"""
Context Builder Module — Strategies cho việc xây dựng context string cho LLM.

Protocol:
    BaseContextBuilder: Interface chung cho tất cả context building strategies.

Implementations:
    - NestedContextBuilder: Xây dựng context đệ quy 2 cấp (mặc định)
"""
from app.services.context_builder.base import BaseContextBuilder
from app.services.context_builder.nested_context import NestedContextBuilder

__all__ = ["BaseContextBuilder", "NestedContextBuilder"]
