"""
Context builder module for constructing LLM-ready context strings.

Protocol:
    BaseContextBuilder: shared interface for context building strategies.

Implementations:
    - NestedContextBuilder: default two-level recursive context builder.
"""
from app.services.context_builder.base import BaseContextBuilder
from app.services.context_builder.nested_context import NestedContextBuilder

__all__ = ["BaseContextBuilder", "NestedContextBuilder"]
