"""
tests/test_readers.py — Unit tests for the LLM reader layer.

All LiteLLM calls are mocked so tests run offline without any API keys.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.ingest.extractors.chunker import Chunk
from backend.ingest.readers.base_reader import ReadTask, ReadResult, BaseDocumentReader
from backend.ingest.readers.provider_registry import get_provider_config, list_providers, PROVIDERS
from backend.ingest.readers.litellm_reader import LiteLLMReader, _build_user_prompt


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_chunks() -> list[Chunk]:
    return [
        Chunk(
            text="iPhone 15 Pro — Price: 25,000,000 VND. Category: Electronics.",
            chunk_index=0,
            total_chunks=2,
            heading="Products",
            source="catalog.pdf",
            source_type="pdf",
        ),
        Chunk(
            text="Nike Air Max — Price: 3,500,000 VND. Category: Footwear.",
            chunk_index=1,
            total_chunks=2,
            heading="Products",
            source="catalog.pdf",
            source_type="pdf",
        ),
    ]


def make_mock_response(content: str, in_tokens: int = 100, out_tokens: int = 50):
    """Build a mock LiteLLM response object."""
    usage = MagicMock()
    usage.prompt_tokens = in_tokens
    usage.completion_tokens = out_tokens

    choice = MagicMock()
    choice.message.content = content

    response = MagicMock()
    response.choices = [choice]
    response.usage = usage
    return response


# ── Provider registry tests ───────────────────────────────────────────────────

class TestProviderRegistry:

    def test_all_providers_have_model(self):
        for name, config in PROVIDERS.items():
            assert "model" in config, f"Provider '{name}' missing 'model' key"
            assert config["model"], f"Provider '{name}' has empty model"

    def test_get_provider_config_known(self):
        cfg = get_provider_config("openai")
        assert cfg["model"] == "openai/gpt-4o"

    def test_get_provider_config_fallback(self):
        cfg = get_provider_config("unknown_provider_xyz")
        assert cfg["model"].startswith("ollama/")  # Falls back to local

    def test_list_providers_returns_all(self):
        providers = list_providers()
        names = [p["name"] for p in providers]
        assert "openai" in names
        assert "anthropic" in names
        assert "gemini" in names
        assert "local" in names

    def test_anthropic_has_caching_flag(self):
        cfg = get_provider_config("anthropic")
        assert cfg.get("use_prompt_caching") is True

    def test_gemini_has_native_pdf_flag(self):
        cfg = get_provider_config("gemini")
        assert cfg.get("native_pdf") is True


# ── Prompt builder tests ──────────────────────────────────────────────────────

class TestPromptBuilders:

    def test_summarize_prompt(self):
        prompt = _build_user_prompt(ReadTask.SUMMARIZE, "Document content here")
        assert "Document content" in prompt
        assert "summary" in prompt.lower()

    def test_extract_prompt_with_schema(self):
        schema = {"product_name": "str", "price": "number"}
        prompt = _build_user_prompt(ReadTask.EXTRACT_STRUCTURED, "Content", schema=schema)
        assert "JSON" in prompt
        assert "product_name" in prompt

    def test_qa_prompt_with_question(self):
        prompt = _build_user_prompt(ReadTask.QA, "Context here", question="What is the price?")
        assert "What is the price?" in prompt
        assert "Context" in prompt

    def test_enrich_prompt(self):
        prompt = _build_user_prompt(ReadTask.ENRICH, "Some text chunk")
        assert "metadata" in prompt.lower() or "enrich" in prompt.lower() or "category" in prompt.lower()


# ── LiteLLMReader tests ───────────────────────────────────────────────────────

class TestLiteLLMReader:
    """
    Tests patch _call_litellm directly so they work regardless of
    whether litellm is installed. This is a better unit test boundary anyway.
    """

    def _make_call_mock(self, content: str, in_tokens: int = 100, out_tokens: int = 50):
        """Return an AsyncMock for _call_litellm that returns {content, usage}."""
        return AsyncMock(return_value={
            "content": content,
            "usage": {"prompt_tokens": in_tokens, "completion_tokens": out_tokens},
        })

    @pytest.mark.asyncio
    async def test_summarize_task(self, sample_chunks):
        reader = LiteLLMReader(provider="local")
        mock = self._make_call_mock("This catalog lists electronics and footwear products.")

        with patch.object(reader, "_call_litellm", mock):
            result = await reader.read(sample_chunks, task=ReadTask.SUMMARIZE)

        assert result.task == ReadTask.SUMMARIZE
        assert result.provider == "local"
        assert result.summary is not None
        assert len(result.summary) > 0
        assert result.error is None
        assert result.input_tokens == 100
        assert result.output_tokens == 50

    @pytest.mark.asyncio
    async def test_extract_structured_task(self, sample_chunks):
        reader = LiteLLMReader(provider="local")
        mock_json = '{"products": [{"name": "iPhone 15 Pro", "price": 25000000}]}'
        mock = self._make_call_mock(mock_json)

        with patch.object(reader, "_call_litellm", mock):
            result = await reader.read(sample_chunks, task=ReadTask.EXTRACT_STRUCTURED)

        assert result.task == ReadTask.EXTRACT_STRUCTURED
        assert result.extracted_data is not None
        assert "products" in result.extracted_data

    @pytest.mark.asyncio
    async def test_extract_structured_invalid_json_salvaged(self, sample_chunks):
        """If LLM returns invalid JSON, raw_response should be saved."""
        reader = LiteLLMReader(provider="local")
        mock = self._make_call_mock("This is not JSON at all")

        with patch.object(reader, "_call_litellm", mock):
            result = await reader.read(sample_chunks, task=ReadTask.EXTRACT_STRUCTURED)

        assert result.extracted_data is not None
        assert "raw_response" in result.extracted_data

    @pytest.mark.asyncio
    async def test_qa_task(self, sample_chunks):
        reader = LiteLLMReader(provider="local")
        mock = self._make_call_mock("The price of iPhone 15 Pro is 25,000,000 VND.")

        with patch.object(reader, "_call_litellm", mock):
            result = await reader.read(
                sample_chunks,
                task=ReadTask.QA,
                question="What is the price of iPhone 15 Pro?",
            )

        assert result.task == ReadTask.QA
        assert result.summary is not None
        assert "25,000,000" in result.summary

    @pytest.mark.asyncio
    async def test_enrich_task(self, sample_chunks):
        reader = LiteLLMReader(provider="local")
        enrich_json = (
            '{"category": "Electronics", "tags": ["phone", "apple"], '
            '"language": "vi", "sentiment": "neutral", "key_entities": ["iPhone 15 Pro"]}'
        )
        mock = self._make_call_mock(enrich_json)

        with patch.object(reader, "_call_litellm", mock):
            result = await reader.read(sample_chunks, task=ReadTask.ENRICH)

        assert result.task == ReadTask.ENRICH
        assert result.enriched_chunks is not None
        assert len(result.enriched_chunks) == len(sample_chunks)
        # Metadata should be merged into each chunk
        first = result.enriched_chunks[0]
        assert "category" in first.metadata

    @pytest.mark.asyncio
    async def test_empty_chunks_returns_error(self):
        reader = LiteLLMReader(provider="local")
        result = await reader.read([], task=ReadTask.SUMMARIZE)
        assert result.error == "No chunks provided"

    @pytest.mark.asyncio
    async def test_litellm_exception_handled_gracefully(self, sample_chunks):
        reader = LiteLLMReader(provider="local")
        mock = AsyncMock(side_effect=Exception("API error"))

        with patch.object(reader, "_call_litellm", mock):
            result = await reader.read(sample_chunks, task=ReadTask.SUMMARIZE)

        assert result.error is not None
        assert "API error" in result.error

    def test_context_builder_respects_limit(self, sample_chunks):
        """_build_context should truncate to max_chars."""
        context = BaseDocumentReader._build_context(sample_chunks, max_chars=50)
        assert len(context) <= 200  # Truncation message adds some chars

