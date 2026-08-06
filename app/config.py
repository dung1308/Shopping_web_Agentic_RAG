"""
app/config.py — Centralised settings (Pydantic-Settings v2).
All values are loaded from environment variables / .env file.
"""

from functools import lru_cache
from typing import Any, Literal

from pydantic import AnyHttpUrl, Field, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ────────────────────────────────────────────────────────
    app_env: Literal["development", "production", "test"] = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # ── Security ───────────────────────────────────────────────────────────
    api_secret_key: str = Field(..., min_length=32)
    admin_jwt_algorithm: str = "HS256"
    admin_jwt_expire_minutes: int = 60

    # ── Database ───────────────────────────────────────────────────────────
    database_url: str

    @field_validator("database_url", mode="before")
    @classmethod
    def format_async_pg_url(cls, v: Any) -> str:
        s = str(v).strip()
        # Replace driver prefix with postgresql+asyncpg
        if s.startswith("postgres://"):
            s = s.replace("postgres://", "postgresql+asyncpg://", 1)
        elif s.startswith("postgresql://") and not s.startswith("postgresql+"):
            s = s.replace("postgresql://", "postgresql+asyncpg://", 1)

        # Sanitize query parameters for asyncpg compatibility
        # Replace sslmode=... with ssl=require
        if "sslmode=" in s:
            s = s.replace("sslmode=require", "ssl=require").replace("sslmode=prefer", "ssl=prefer").replace("sslmode=disable", "ssl=disable")
        elif "ssl=" not in s and "neon.tech" in s:
            s = s + ("&ssl=require" if "?" in s else "?ssl=require")

        # Remove channel_binding parameter if present (not supported by asyncpg driver)
        if "channel_binding=" in s:
            import re
            s = re.sub(r"&?channel_binding=[^&]+", "", s)
            s = s.replace("?&", "?").rstrip("?&")

        return s

    # ── Redis ──────────────────────────────────────────────────────────────
    redis_url: RedisDsn
    session_ttl_seconds: int = 3600

    # ── ChromaDB ───────────────────────────────────────────────────────────
    # Embedded mode (default, no server needed): set chroma_path to a local folder.
    # HTTP server mode: set chroma_host (e.g. "localhost") and chroma_port.
    chroma_path: str = "./chroma_data"     # used when chroma_host is empty
    chroma_host: str = ""                  # set to hostname for HTTP server mode
    chroma_port: int = 8200                # Chroma HTTP server port
    chroma_collection: str = "mall_products"

    # ── Local LLM ──────────────────────────────────────────────────────────
    llm_base_url: AnyHttpUrl = AnyHttpUrl("http://localhost:11434/v1")
    llm_api_key: str = "ollama"
    llm_model: str = "qwen2.5:7b-instruct"
    llm_temperature: float = Field(0.3, ge=0.0, le=2.0)
    llm_max_tokens: int = Field(2048, ge=256)

    # ── Embedding ──────────────────────────────────────────────────────────
    embed_base_url: AnyHttpUrl = AnyHttpUrl("http://localhost:7997")
    embed_model: str = "BAAI/bge-m3"
    embed_dim: int = 1024

    # ── Scraping ───────────────────────────────────────────────────────────
    playwright_headless: bool = True
    scrape_concurrency: int = Field(4, ge=1, le=20)
    scrape_timeout_seconds: int = 30

    # ── Docling extraction ─────────────────────────────────────────────────
    docling_device: str = "cpu"            # "cpu" | "cuda" | "auto"
    docling_enable_ocr: bool = True
    docling_ocr_engine: str = "easyocr"   # "easyocr" | "tesseract"

    # ── Chunking ───────────────────────────────────────────────────────────
    ingest_chunk_size: int = Field(512, ge=64, le=4096)   # tokens per chunk
    ingest_chunk_overlap: int = Field(64, ge=0, le=512)   # overlap tokens
    ingest_max_file_mb: float = Field(50.0, ge=1.0)       # max local file size

    # ── LLM Reader ─────────────────────────────────────────────────────────
    llm_reader_provider: str = "local"    # "openai" | "anthropic" | "gemini" | "local" | "none"

    # ── MCP ────────────────────────────────────────────────────────────────
    mcp_transport: Literal["stdio", "sse"] = "stdio"
    mcp_sse_port: int = 8001

    @property
    def is_dev(self) -> bool:
        return self.app_env == "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings()  # type: ignore[call-arg]
