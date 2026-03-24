"""Scrapers package — aggregate all topic sources."""

from __future__ import annotations

from typing import Any

from rich.console import Console

from scrapers.competitors import fetch_competitors
from scrapers.pubmed import fetch_pubmed
from scrapers.trends import fetch_trends

TopicDict = dict[str, Any]


def run_all_scrapers() -> list[TopicDict]:
    """Run every scraper, print a summary, and return the combined topic list."""
    console = Console()
    console.print("[bold blue]Running all scrapers...[/bold blue]\n")

    trends_topics = fetch_trends()
    console.print(f"  Google Trends: [cyan]{len(trends_topics)}[/cyan] topics")

    pubmed_topics = fetch_pubmed()
    console.print(f"  PubMed:        [cyan]{len(pubmed_topics)}[/cyan] topics")

    competitor_topics = fetch_competitors()
    console.print(f"  Competitors:   [cyan]{len(competitor_topics)}[/cyan] topics")

    combined = trends_topics + pubmed_topics + competitor_topics
    console.print(f"\n[bold green]Total scraped:[/bold green] {len(combined)} topics")

    return combined
