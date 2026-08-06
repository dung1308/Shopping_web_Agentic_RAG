"""
app/ingest/readers/provider_registry.py — LLM provider configuration registry.

Maps short provider names → LiteLLM model strings + provider-specific options.

Providers:
  "openai"    → GPT-4o (best multimodal quality, vision for images)
  "anthropic" → Claude Sonnet (Files API, prompt caching, citations, 1M ctx)
  "gemini"    → Gemini 2.0 Flash (fast, native PDF inline, multimodal)
  "local"     → Ollama/qwen2.5 (no API key, CPU-safe, offline)

Each entry contains:
  model         : LiteLLM model string (provider/model-name)
  max_tokens    : Max output tokens for this provider
  context_limit : Approx input context limit in chars
  api_base      : Override base URL (for local Ollama)
  notes         : Human-readable feature summary
"""

from __future__ import annotations

from typing import Any

from backend.config import get_settings

settings = get_settings()

PROVIDERS: dict[str, dict[str, Any]] = {
    "openai": {
        "model": "openai/gpt-4o",
        "max_tokens": 4096,
        "context_limit": 100_000,         # ~128k token context, use 100k char budget
        "vision": True,                   # Can process base64 images
        "notes": "Best quality, vision support for images. Requires OPENAI_API_KEY.",
    },
    "anthropic": {
        "model": "anthropic/claude-sonnet-4-5",
        "max_tokens": 8192,
        "context_limit": 600_000,         # 1M token context window
        "vision": True,
        "use_prompt_caching": True,       # Cache document context between calls (60-90% savings)
        "use_files_api": True,            # Upload-once, reference by file_id
        "notes": (
            "Best for large PDFs. Files API + prompt caching reduce cost by 60-90%."
            " Citations API for source tracing. Requires ANTHROPIC_API_KEY."
        ),
    },
    "gemini": {
        "model": "gemini/gemini-2.0-flash",
        "max_tokens": 8192,
        "context_limit": 400_000,         # ~1M token context
        "vision": True,
        "native_pdf": True,               # Pass raw PDF bytes inline (no Docling needed)
        "notes": (
            "Fastest provider. Native PDF + image processing. "
            "Multimodal file search. Requires GEMINI_API_KEY."
        ),
    },
    "local": {
        "model": f"ollama/{settings.llm_model}",
        "max_tokens": int(settings.llm_max_tokens),
        "context_limit": 30_000,          # Depends on local model context length
        "api_base": str(settings.llm_base_url).rstrip("/v1").rstrip("/"),
        "vision": False,
        "notes": (
            "Local Ollama model — no API key, CPU-safe, offline. "
            "Best for development and testing."
        ),
    },
}


def get_provider_config(provider_name: str) -> dict[str, Any]:
    """
    Return provider config dict by short name.
    Falls back to 'local' if provider_name is unknown.

    Args:
        provider_name: One of "openai", "anthropic", "gemini", "local"

    Returns:
        Provider configuration dict
    """
    name = provider_name.lower().strip()
    if name not in PROVIDERS:
        import logging
        logging.getLogger("mall_rag.provider_registry").warning(
            f"Unknown provider '{provider_name}', falling back to 'local'"
        )
        name = "local"
    return PROVIDERS[name]


def list_providers() -> list[dict[str, Any]]:
    """Return a list of all registered providers with their notes."""
    return [
        {"name": k, "model": v["model"], "notes": v.get("notes", "")}
        for k, v in PROVIDERS.items()
    ]

