"""
app/ingest/cli.py — Ingestion Typer CLI.
Executable commands for scraping, validating, and indexing mall store data.
Usage:
  python -m app.ingest.cli scrape --store-id <UUID> --url <URL>
  python -m app.ingest.cli pipeline --store-id <UUID> --url <URL>
"""

import asyncio
import json
import uuid
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from app.ingest.agents.scraper import scrape_store_products
from app.ingest.agents.validator import validate_scraped_items
from app.ingest.agents.indexer import index_validated_products
from app.ingest.agents.document_ingester import DocumentIngester
from app.ingest.readers.base_reader import ReadTask
from app.ingest.readers.provider_registry import list_providers

app = typer.Typer(name="mall-ingest", help="CLI tool for mall store data ingestion.")
console = Console()


@app.command()
def scrape(
    store_id: str = typer.Option(..., "--store-id", "-s", help="Store UUID"),
    url: str = typer.Option(..., "--url", "-u", help="Store target URL"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Optional output JSON file path"),
):
    """Scrape raw product data from a store URL."""
    console.print(f"[bold blue]Scraping store {store_id} at {url}...[/bold blue]")
    raw_items = asyncio.run(scrape_store_products(store_id=store_id, store_url=url))
    
    console.print(f"[green]Scraped {len(raw_items)} items successfully.[/green]")
    if output:
        with open(output, "w", encoding="utf-8") as f:
            json.dumps(raw_items, f, indent=2, ensure_ascii=False)
        console.print(f"Saved raw items to {output}")


@app.command()
def pipeline(
    store_id: str = typer.Option(..., "--store-id", "-s", help="Store UUID"),
    url: str = typer.Option(..., "--url", "-u", help="Store target URL"),
    store_name: str = typer.Option("Mall Store", "--store-name", help="Store Name"),
    floor: int = typer.Option(1, "--floor", help="Floor number"),
):
    """Run full pipeline: Scrape -> Validate -> Index."""
    job_id = str(uuid.uuid4())
    console.print(f"[bold cyan]Starting pipeline job {job_id} for store {store_id}...[/bold cyan]")

    async def _run():
        # Step 1: Scrape
        raw_items = await scrape_store_products(store_id=store_id, store_url=url)
        console.print(f"• Scraped {len(raw_items)} raw items")

        # Step 2: Validate
        val_results = await validate_scraped_items(job_id=job_id, store_id=store_id, raw_items=raw_items)
        valid_products = [r.validated_product for r in val_results if r.is_valid and r.validated_product]
        console.print(f"• Validated {len(valid_products)} products ({len(val_results) - len(valid_products)} flagged)")

        # Step 3: Index
        indexed_count = await index_validated_products(valid_products, store_name=store_name, floor=floor)
        console.print(f"[bold green]• Indexed {indexed_count} products into Qdrant![/bold green]")

    asyncio.run(_run())


@app.command()
def ingest_file(
    file: str = typer.Option(..., "--file", "-f", help="Path to file (PDF, DOCX, TXT, JSON, image)"),
    store_id: str = typer.Option(..., "--store-id", "-s", help="Store UUID"),
    store_name: str = typer.Option("Mall Store", "--store-name", help="Store name"),
    floor: int = typer.Option(1, "--floor", help="Floor number"),
    provider: Optional[str] = typer.Option(
        None, "--provider", "-p",
        help="LLM reader provider: openai | anthropic | gemini | local | none"
    ),
    task: str = typer.Option(
        "extract_structured", "--task", "-t",
        help="Reader task: summarize | extract_structured | enrich | qa"
    ),
):
    """Ingest a local file (PDF, DOCX, TXT, JSON, image) into the RAG pipeline."""
    console.print(f"[bold cyan]\u2192 Ingesting file:[/bold cyan] {file}")
    console.print(f"  Store: {store_name} | Floor: {floor} | Provider: {provider or 'config default'}")

    async def _run():
        ingester = DocumentIngester(
            store_id=store_id,
            store_name=store_name,
            floor=floor,
        )
        result = await ingester.ingest_file(
            file_path=file,
            provider=provider,
            task=ReadTask(task),
        )
        return result

    result = asyncio.run(_run())
    console.print(f"[bold green]\u2713 Indexed {result.chunks_indexed} chunks[/bold green]")
    if result.llm_provider:
        console.print(f"  LLM: {result.llm_provider} | Task: {result.llm_task}")
    if result.read_result and result.read_result.summary:
        console.print(f"\n[dim]Summary:[/dim] {result.read_result.summary[:300]}")


@app.command()
def ingest_url(
    url: str = typer.Option(..., "--url", "-u", help="URL to ingest (HTML page or direct PDF/image)"),
    store_id: str = typer.Option(..., "--store-id", "-s", help="Store UUID"),
    store_name: str = typer.Option("Mall Store", "--store-name", help="Store name"),
    floor: int = typer.Option(1, "--floor", help="Floor number"),
    mode: str = typer.Option(
        "auto", "--mode", "-m",
        help="Capture mode: auto | html | pdf | image"
    ),
    provider: Optional[str] = typer.Option(
        None, "--provider", "-p",
        help="LLM reader provider: openai | anthropic | gemini | local | none"
    ),
    task: str = typer.Option(
        "extract_structured", "--task", "-t",
        help="Reader task: summarize | extract_structured | enrich | qa"
    ),
    screenshot: bool = typer.Option(False, "--screenshot", help="Capture a page screenshot"),
):
    """Ingest content from a URL (JS-rendered page, PDF, or image)."""
    console.print(f"[bold cyan]\u2192 Ingesting URL:[/bold cyan] {url}")
    console.print(f"  Mode: {mode} | Provider: {provider or 'config default'} | Task: {task}")

    async def _run():
        ingester = DocumentIngester(
            store_id=store_id,
            store_name=store_name,
            floor=floor,
        )
        result = await ingester.ingest_url(
            url=url,
            mode=mode,
            provider=provider,
            task=ReadTask(task),
            capture_screenshot=screenshot,
        )
        return result

    result = asyncio.run(_run())
    console.print(f"[bold green]\u2713 Indexed {result.chunks_indexed} chunks[/bold green]")
    if result.llm_provider:
        console.print(f"  LLM: {result.llm_provider} | Task: {result.llm_task}")
    if result.read_result and result.read_result.summary:
        console.print(f"\n[dim]Summary:[/dim] {result.read_result.summary[:300]}")


@app.command()
def list_providers_cmd():
    """List all available LLM reader providers and their capabilities."""
    providers = list_providers()
    table = Table(title="Available LLM Reader Providers")
    table.add_column("Name", style="bold cyan")
    table.add_column("Model", style="yellow")
    table.add_column("Notes", style="dim")
    for p in providers:
        table.add_row(p["name"], p["model"], p["notes"])
    console.print(table)


if __name__ == "__main__":
    app()
