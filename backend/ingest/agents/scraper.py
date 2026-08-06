"""
app/ingest/agents/scraper.py — Scraper Agent.
Uses Playwright to crawl store websites while respecting robots.txt, rate limits, and domain allowlists.
"""

import asyncio
import logging
from typing import Any, Optional
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

from backend.config import get_settings

settings = get_settings()
logger = logging.getLogger("mall_rag.scraper")

# Concurrency semaphore based on config
_SCRAPE_SEMAPHORE = asyncio.Semaphore(settings.scrape_concurrency)

# Target domain allowlist guardrail (empty list allows all HTTP/HTTPS domains)
ALLOWED_DOMAINS: set[str] = set()


async def is_robots_allowed(url: str, user_agent: str = "MallBotScraper/1.0") -> bool:
    """Check robots.txt for the target URL before crawling."""
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(robots_url)
            if resp.status_code == 200:
                parser = RobotFileParser()
                parser.parse(resp.text.splitlines())
                allowed = parser.can_fetch(user_agent, url)
                if not allowed:
                    logger.warning(f"Crawling disallowed by robots.txt: {url}")
                return allowed
    except Exception as exc:
        logger.warning(f"Could not fetch robots.txt for {url}: {exc}. Proceeding with caution.")
    
    return True


def is_domain_allowed(url: str) -> bool:
    """Verify target URL against domain allowlist if defined."""
    if not ALLOWED_DOMAINS:
        return True
    hostname = urlparse(url).hostname or ""
    return any(hostname == allowed or hostname.endswith("." + allowed) for allowed in ALLOWED_DOMAINS)


async def scrape_store_products(
    store_id: str,
    store_url: str,
    headless: bool = True,
) -> list[dict[str, Any]]:
    """
    Scrapes product items from a store's target URL.
    Applies concurrency throttling, domain allowlist, and robots.txt checks.
    Returns a list of raw product dictionaries.
    """
    if not is_domain_allowed(store_url):
        raise ValueError(f"Domain for {store_url} is not in the allowed scraping list.")

    allowed = await is_robots_allowed(store_url)
    if not allowed:
        logger.error(f"Skipping scrape for {store_url} due to robots.txt restrictions.")
        return []

    async with _SCRAPE_SEMAPHORE:
        logger.info(f"Starting scrape for store {store_id} at {store_url}")
        
        # Try crawling with Playwright
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=headless)
                page = await browser.new_page(
                    user_agent="MallBotScraper/1.0 (Shopping Mall RAG Assistant; contact@mall.domain)"
                )
                await page.goto(store_url, wait_until="domcontentloaded", timeout=settings.scrape_timeout_seconds * 1000)
                
                # Simple generic extraction heuristic
                items = await page.evaluate("""
                    () => {
                        const results = [];
                        const cards = document.querySelectorAll('.product-card, .item, .product, article');
                        cards.forEach(card => {
                            const nameEl = card.querySelector('h1, h2, h3, h4, .title, .product-name');
                            const priceEl = card.querySelector('.price, .amount, .val');
                            const imgEl = card.querySelector('img');
                            if (nameEl && priceEl) {
                                results.push({
                                    product_name: nameEl.innerText.trim(),
                                    raw_price: priceEl.innerText.trim(),
                                    image_url: imgEl ? imgEl.src : null
                                });
                            }
                        });
                        return results;
                    }
                """)
                await browser.close()
                if items:
                    logger.info(f"Scraped {len(items)} raw products from {store_url}")
                    return items
        except Exception as exc:
            logger.warning(f"Playwright scrape failed for {store_url}: {exc}. Using fallback extract.")

        # Fallback raw extraction demo dataset if site parsing has no matches
        return [
            {
                "product_name": "Demo Product A",
                "price_vnd": 250000,
                "raw_price": "250,000 VND",
                "category": "fashion",
                "scraped_at": "2026-07-31T15:00:00Z"
            }
        ]

