"""
app/ingest/extractors/playwright_extractor.py — Playwright-powered JS-page capture.

Captures:
  1. Full rendered HTML after JavaScript execution
  2. XHR / fetch JSON responses intercepted during page load (JS API calls)
  3. Optional base64 screenshot (for image-based visual analysis)

The captured HTML is intended to be passed directly into DoclingExtractor.from_html().
Intercepted JSON payloads go into DoclingExtractor.from_json() for each payload.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger("mall_rag.extractor.playwright")


@dataclass
class PlaywrightCapture:
    """Full capture result from a Playwright page visit."""
    url: str
    html: str                                 # Final rendered HTML
    xhr_payloads: list[dict[str, Any]] = field(default_factory=list)  # Intercepted JSON
    screenshot_b64: str | None = None          # Optional page screenshot
    page_title: str = ""
    final_url: str = ""                        # URL after redirects


class PlaywrightExtractor:
    """
    Captures fully rendered HTML and XHR API responses from JavaScript-heavy pages.

    Respects:
    - robots.txt
    - Concurrency limits (SCRAPE_CONCURRENCY from config)
    - Domain allowlists (optional)

    Usage:
        extractor = PlaywrightExtractor()
        capture = await extractor.capture("https://shop.example.com/products")
        # → capture.html for DoclingExtractor.from_html()
        # → capture.xhr_payloads for DoclingExtractor.from_json()
    """

    _semaphore: asyncio.Semaphore | None = None
    ALLOWED_DOMAINS: set[str] = set()  # Empty = allow all

    @classmethod
    def _get_semaphore(cls) -> asyncio.Semaphore:
        if cls._semaphore is None:
            cls._semaphore = asyncio.Semaphore(settings.scrape_concurrency)
        return cls._semaphore

    # ── Robots.txt check ────────────────────────────────────────────────────

    async def _is_robots_allowed(self, url: str) -> bool:
        """Check robots.txt before crawling."""
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(robots_url)
                if resp.status_code == 200:
                    parser = RobotFileParser()
                    parser.parse(resp.text.splitlines())
                    allowed = parser.can_fetch("MallBotScraper/1.0", url)
                    if not allowed:
                        logger.warning(f"robots.txt disallows: {url}")
                    return allowed
        except Exception as exc:
            logger.warning(f"Could not fetch robots.txt for {url}: {exc}. Proceeding.")
        return True

    def _is_domain_allowed(self, url: str) -> bool:
        """Check domain allowlist if configured."""
        if not self.ALLOWED_DOMAINS:
            return True
        hostname = urlparse(url).hostname or ""
        return any(
            hostname == d or hostname.endswith("." + d)
            for d in self.ALLOWED_DOMAINS
        )

    # ── Main capture method ─────────────────────────────────────────────────

    async def capture(
        self,
        url: str,
        capture_screenshot: bool = False,
        wait_for: str = "networkidle",          # "load" | "domcontentloaded" | "networkidle"
        intercept_xhr: bool = True,
        headless: bool | None = None,
    ) -> PlaywrightCapture:
        """
        Navigate to `url`, wait for JS to render, and capture:
        - Rendered HTML DOM
        - Intercepted XHR/fetch JSON responses
        - Optional full-page screenshot

        Args:
            url: Target URL to capture
            capture_screenshot: If True, take a base64 full-page screenshot
            wait_for: Playwright wait_until strategy
            intercept_xhr: If True, intercept and collect JSON API responses
            headless: Override PLAYWRIGHT_HEADLESS setting

        Returns:
            PlaywrightCapture with html, xhr_payloads, and optional screenshot
        """
        if not self._is_domain_allowed(url):
            raise ValueError(f"Domain not in allowlist: {urlparse(url).hostname}")

        if not await self._is_robots_allowed(url):
            raise PermissionError(f"robots.txt disallows crawling: {url}")

        _headless = headless if headless is not None else settings.playwright_headless

        async with self._get_semaphore():
            return await self._do_capture(url, _headless, capture_screenshot,
                                           wait_for, intercept_xhr)

    async def _do_capture(
        self,
        url: str,
        headless: bool,
        capture_screenshot: bool,
        wait_for: str,
        intercept_xhr: bool,
    ) -> PlaywrightCapture:
        try:
            from playwright.async_api import async_playwright, Request, Response
        except ImportError as exc:
            raise RuntimeError(
                "Playwright is not installed. Run: playwright install chromium"
            ) from exc

        xhr_payloads: list[dict[str, Any]] = []
        screenshot_b64: str | None = None

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(
                user_agent="MallBotScraper/1.0 (RAG Ingestion; contact@mall.domain)",
                viewport={"width": 1280, "height": 900},
            )
            page = await context.new_page()

            # ── XHR / fetch interception ────────────────────────────────────
            if intercept_xhr:
                async def handle_response(response: Response) -> None:
                    ct = response.headers.get("content-type", "")
                    if "application/json" in ct:
                        try:
                            body = await response.json()
                            xhr_payloads.append({
                                "url": response.url,
                                "status": response.status,
                                "data": body,
                            })
                            logger.debug(f"Intercepted JSON from: {response.url}")
                        except Exception:
                            pass  # Non-JSON or streaming body, skip

                page.on("response", handle_response)

            # ── Navigate and wait ───────────────────────────────────────────
            logger.info(f"Playwright capturing: {url} (wait_for={wait_for})")
            response = await page.goto(
                url,
                wait_until=wait_for,
                timeout=settings.scrape_timeout_seconds * 1000,
            )

            # Extra scroll to trigger lazy-loaded content
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1500)

            # ── Capture HTML ────────────────────────────────────────────────
            html = await page.content()
            page_title = await page.title()
            final_url = page.url

            # ── Optional screenshot ─────────────────────────────────────────
            if capture_screenshot:
                screenshot_bytes = await page.screenshot(full_page=True)
                screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
                logger.info(f"Screenshot captured ({len(screenshot_bytes) // 1024} KB)")

            await browser.close()

        logger.info(
            f"Playwright capture done: {url} "
            f"| HTML={len(html) // 1024}KB "
            f"| XHR payloads={len(xhr_payloads)}"
        )

        return PlaywrightCapture(
            url=url,
            html=html,
            xhr_payloads=xhr_payloads,
            screenshot_b64=screenshot_b64,
            page_title=page_title,
            final_url=final_url,
        )
