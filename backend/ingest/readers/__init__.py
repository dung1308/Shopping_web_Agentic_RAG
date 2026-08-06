"""
app/ingest/readers/__init__.py — Multi-provider LLM document reader package.

Provides a unified LiteLLM-backed reader that can enrich, summarize, or
extract structured data from document chunks using any configured provider.
"""

from backend.ingest.readers.base_reader import BaseDocumentReader, ReadTask, ReadResult
from backend.ingest.readers.provider_registry import PROVIDERS, get_provider_config
from backend.ingest.readers.litellm_reader import LiteLLMReader

__all__ = [
    "BaseDocumentReader",
    "ReadTask",
    "ReadResult",
    "PROVIDERS",
    "get_provider_config",
    "LiteLLMReader",
]

