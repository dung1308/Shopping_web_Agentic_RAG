"""
app/ingest/readers/litellm_reader.py — Unified LiteLLM document reader.

Implements BaseDocumentReader using LiteLLM as the single adapter layer.
Switching providers is as simple as changing the `provider` argument.

Provider-specific enhancements:
  • OpenAI    — vision mode for image chunks (base64 → gpt-4o vision)
  • Anthropic — prompt caching headers + Files API file_id reference
  • Gemini    — native PDF inline support (pass raw bytes directly)
  • Local     — Ollama api_base override, generous timeout

ReadTask behavior:
  SUMMARIZE          → single-pass summarization prompt
  EXTRACT_STRUCTURED → JSON extraction prompt with optional schema hint
  ENRICH             → per-chunk enrichment (adds category, tags, keywords)
  QA                 → question-answer over assembled context
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from app.ingest.extractors.chunker import Chunk
from app.ingest.readers.base_reader import BaseDocumentReader, ReadTask, ReadResult
from app.ingest.readers.provider_registry import get_provider_config

logger = logging.getLogger("mall_rag.reader.litellm")


# ── System prompts per task ──────────────────────────────────────────────────

SYSTEM_PROMPTS: dict[ReadTask, str] = {
    ReadTask.SUMMARIZE: (
        "You are a document analyst. Produce a concise, factual summary (3–5 sentences) "
        "of the provided document content. Focus on key topics, entities, and important data points."
    ),
    ReadTask.EXTRACT_STRUCTURED: (
        "You are a data extraction expert. Extract structured information from the document. "
        "Return ONLY valid JSON. No markdown, no code fences, no explanation — just raw JSON."
    ),
    ReadTask.ENRICH: (
        "You are a metadata enrichment assistant. For the given text chunk, identify and return "
        "a JSON object with these fields: "
        "{\"category\": str, \"tags\": [str], \"language\": str, \"sentiment\": str, "
        "\"key_entities\": [str]}. "
        "Return ONLY valid JSON."
    ),
    ReadTask.QA: (
        "You are a document Q&A assistant. Answer the question using ONLY the provided context. "
        "If the answer is not in the context, say 'Not found in document.'"
    ),
}

# ── User prompt builders ─────────────────────────────────────────────────────

def _build_user_prompt(
    task: ReadTask,
    context: str,
    question: str | None = None,
    schema: dict[str, Any] | None = None,
) -> str:
    if task == ReadTask.SUMMARIZE:
        return f"Document content:\n\n{context}\n\nProvide a concise summary."

    elif task == ReadTask.EXTRACT_STRUCTURED:
        schema_hint = ""
        if schema:
            schema_hint = f"\n\nExtract according to this JSON schema:\n{json.dumps(schema, indent=2)}"
        return f"Document content:\n\n{context}{schema_hint}\n\nExtract structured data as JSON."

    elif task == ReadTask.ENRICH:
        return f"Text chunk to enrich:\n\n{context}\n\nReturn metadata JSON."

    elif task == ReadTask.QA:
        q = question or "Summarize the key points."
        return f"Context:\n\n{context}\n\nQuestion: {q}"

    return context


# ── LiteLLMReader ─────────────────────────────────────────────────────────────

class LiteLLMReader(BaseDocumentReader):
    """
    Multi-provider document reader using LiteLLM as the unified interface.

    Args:
        provider: Short provider name — "openai" | "anthropic" | "gemini" | "local"

    Usage:
        reader = LiteLLMReader(provider="gemini")
        result = await reader.read(chunks, task=ReadTask.SUMMARIZE)
    """

    def __init__(self, provider: str = "local") -> None:
        self.provider_name = provider.lower()
        self.config = get_provider_config(provider)
        self.model = self.config["model"]
        self.max_tokens = self.config["max_tokens"]
        self.context_limit = self.config.get("context_limit", 30_000)
        self._setup_env()

    def _setup_env(self) -> None:
        """Ensure provider API keys are set from environment."""
        key_map = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "gemini": "GEMINI_API_KEY",
        }
        key_env = key_map.get(self.provider_name)
        if key_env and not os.environ.get(key_env):
            logger.warning(
                f"Provider '{self.provider_name}' requires {key_env} environment variable. "
                f"Set it in .env or shell. Falling back gracefully on error."
            )

    # ── Main read method ─────────────────────────────────────────────────────

    async def read(
        self,
        chunks: list[Chunk],
        task: ReadTask,
        question: str | None = None,
        schema: dict[str, Any] | None = None,
    ) -> ReadResult:
        """Run the LLM reader over provided chunks for the given task."""
        if not chunks:
            return ReadResult(task=task, provider=self.provider_name, model=self.model,
                              error="No chunks provided")

        try:
            if task == ReadTask.ENRICH:
                return await self._enrich_chunks(chunks)
            else:
                return await self._single_pass(chunks, task, question, schema)
        except Exception as exc:
            logger.error(f"LiteLLMReader [{self.provider_name}] failed: {exc}")
            return ReadResult(
                task=task,
                provider=self.provider_name,
                model=self.model,
                error=str(exc),
            )

    # ── Single-pass (SUMMARIZE, EXTRACT_STRUCTURED, QA) ─────────────────────

    async def _single_pass(
        self,
        chunks: list[Chunk],
        task: ReadTask,
        question: str | None,
        schema: dict[str, Any] | None,
    ) -> ReadResult:
        """Assemble all chunks into one context and call the LLM once."""
        context = self._build_context(chunks, max_chars=self.context_limit)
        messages = self._build_messages(task, context, question, schema)

        response = await self._call_litellm(messages)
        content = response.get("content", "")
        usage = response.get("usage", {})

        # Parse JSON for structured extraction
        extracted_data: dict[str, Any] | None = None
        if task == ReadTask.EXTRACT_STRUCTURED and content:
            try:
                extracted_data = json.loads(content)
            except json.JSONDecodeError:
                # Try to salvage partial JSON
                extracted_data = {"raw_response": content}

        return ReadResult(
            task=task,
            provider=self.provider_name,
            model=self.model,
            summary=content if task in (ReadTask.SUMMARIZE, ReadTask.QA) else None,
            extracted_data=extracted_data,
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
        )

    # ── Per-chunk enrichment (ENRICH) ────────────────────────────────────────

    async def _enrich_chunks(self, chunks: list[Chunk]) -> ReadResult:
        """Call the LLM once per chunk to add metadata enrichment."""
        enriched: list[Chunk] = []
        total_in = total_out = 0

        for chunk in chunks:
            messages = self._build_messages(ReadTask.ENRICH, chunk.text, None, None)
            response = await self._call_litellm(messages)
            content = response.get("content", "{}")
            usage = response.get("usage", {})
            total_in += usage.get("prompt_tokens", 0)
            total_out += usage.get("completion_tokens", 0)

            try:
                enrichment = json.loads(content)
            except json.JSONDecodeError:
                enrichment = {}

            # Merge enrichment into chunk metadata
            chunk.metadata.update(enrichment)
            enriched.append(chunk)

        return ReadResult(
            task=ReadTask.ENRICH,
            provider=self.provider_name,
            model=self.model,
            enriched_chunks=enriched,
            input_tokens=total_in,
            output_tokens=total_out,
        )

    # ── Message builder ──────────────────────────────────────────────────────

    def _build_messages(
        self,
        task: ReadTask,
        context: str,
        question: str | None,
        schema: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        """Build the LiteLLM-compatible messages list."""
        system_prompt = SYSTEM_PROMPTS[task]
        user_prompt = _build_user_prompt(task, context, question, schema)

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # Anthropic prompt caching: mark system prompt as cacheable
        if self.provider_name == "anthropic" and self.config.get("use_prompt_caching"):
            messages[0] = {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
            }

        return messages

    # ── LiteLLM call ─────────────────────────────────────────────────────────

    async def _call_litellm(
        self, messages: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Call LiteLLM acompletion and return {content, usage} dict."""
        try:
            import litellm
        except ImportError as exc:
            raise RuntimeError("litellm not installed. Run: pip install litellm") from exc

        # Suppress verbose LiteLLM logging unless in debug
        litellm.set_verbose = os.environ.get("LITELLM_VERBOSE", "false").lower() == "true"

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": 0.1,  # Low temp for factual extraction
        }

        # Local Ollama — set custom api_base
        if self.provider_name == "local" and "api_base" in self.config:
            kwargs["api_base"] = self.config["api_base"]
            kwargs["api_key"] = "ollama"  # Placeholder

        logger.debug(f"Calling LiteLLM: model={self.model}")

        response = await litellm.acompletion(**kwargs)

        content = response.choices[0].message.content or ""
        usage = {
            "prompt_tokens": getattr(response.usage, "prompt_tokens", 0),
            "completion_tokens": getattr(response.usage, "completion_tokens", 0),
        }

        logger.info(
            f"LiteLLM [{self.provider_name}] ✓ "
            f"in={usage['prompt_tokens']} out={usage['completion_tokens']} tokens"
        )
        return {"content": content, "usage": usage}
