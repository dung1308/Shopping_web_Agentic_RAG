"""
app/vector/qdrant_client.py — Legacy compatibility module forwarding to chroma_client.py.
"""

from app.vector.chroma_client import (
    init_chroma as init_qdrant,
    get_chroma as get_qdrant,
    upsert_vectors,
    search_vectors,
)

__all__ = ["init_qdrant", "get_qdrant", "upsert_vectors", "search_vectors"]
