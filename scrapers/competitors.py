"""Competitor blog scraper — extract recent posts from competitor sitemaps."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import requests
import yaml

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.yaml"
_BLOG_PATH_RE = re.compile(r"/(blog|post|article|news|resources)/", re.IGNORECASE)
_ARTICLES_PER_SITEMAP = 15

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# R2P fallback pages when sitemap yields 0 blog-path URLs
_R2P_FALLBACKS = [
    "https://rehab2perform.com/blog",
    "https://rehab2perform.com/resources",
    "https://rehab2perform.com/news",
]


def _load_sitemaps() -> list[str]:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as fh:
        cfg: dict[str, Any] = yaml.safe_load(fh)
    return cfg.get("competitor_sitemaps", [])


# ---------------------------------------------------------------------------
# XML parsing — resilient
# ---------------------------------------------------------------------------


def _parse_sitemap_xml(text: str) -> list[str]:
    """Extract all <loc> text from sitemap XML, tolerant of malformed markup."""
    root = None

    # Try lxml with recovery first
    try:
        from lxml import etree as lxml_etree

        parser = lxml_etree.XMLParser(recover=True)
        root = lxml_etree.fromstring(text.encode("utf-8"), parser=parser)
    except Exception:
        pass

    # Fallback to stdlib ElementTree
    if root is None:
        try:
            from xml.etree import ElementTree

            root = ElementTree.fromstring(text)
        except Exception:
            return []

    # Extract namespace if present
    tag = root.tag if hasattr(root, "tag") else ""
    ns = ""
    if isinstance(tag, str) and tag.startswith("{"):
        ns = tag.split("}")[0] + "}"

    urls: list[str] = []
    for loc in root.iter(f"{ns}loc"):
        url = (loc.text or "").strip()
        if url:
            urls.append(url)

    return urls


# ---------------------------------------------------------------------------
# Link extraction from HTML pages (for R2P fallback)
# ---------------------------------------------------------------------------


class _LinkExtractor(HTMLParser):
    """Simple HTML parser that collects <a href> values matching blog paths."""

    def __init__(self, base_domain: str) -> None:
        super().__init__()
        self.base_domain = base_domain
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        for name, value in attrs:
            if name == "href" and value:
                url = value.strip()
                # Make relative URLs absolute
                if url.startswith("/"):
                    url = f"https://{self.base_domain}{url}"
                if _BLOG_PATH_RE.search(url) and self.base_domain in url:
                    self.links.append(url)


def _extract_links_from_page(page_url: str) -> list[str]:
    """Fetch an HTML page and return all blog-like <a href> links."""
    try:
        resp = requests.get(page_url, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception:
        return []

    from urllib.parse import urlparse

    domain = urlparse(page_url).netloc
    parser = _LinkExtractor(domain)
    try:
        parser.feed(resp.text)
    except Exception:
        return []

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for link in parser.links:
        if link not in seen:
            seen.add(link)
            unique.append(link)
    return unique


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TopicDict = dict[str, Any]


def _extract_urls_from_sitemap(sitemap_url: str) -> list[str]:
    """Fetch a sitemap XML and return all <loc> URLs that look like blog posts."""
    resp = requests.get(sitemap_url, headers=_HEADERS, timeout=15)
    resp.raise_for_status()

    all_urls = _parse_sitemap_xml(resp.text)
    return [u for u in all_urls if _BLOG_PATH_RE.search(u)]


def _scrape_article(url: str) -> TopicDict | None:
    """Use newspaper3k to extract title and leading text from a URL."""
    try:
        from newspaper import Article

        article = Article(url)
        article.download()
        article.parse()

        title = (article.title or "").strip()
        if not title:
            return None

        body = (article.text or "").strip()
        summary = body[:300].rsplit(" ", 1)[0] if body else ""

        pub_date = ""
        if article.publish_date:
            pub_date = article.publish_date.date().isoformat()

        return {
            "title": title,
            "source": "competitor",
            "url": url,
            "date": pub_date,
            "score": 0.0,
            "summary": summary,
            "doi": "",
        }
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fetch_competitors() -> list[TopicDict]:
    """Return topic dicts scraped from competitor blog sitemaps.

    Skips failed URLs gracefully. Returns an empty list when no sitemaps are
    configured. Falls back to HTML link scraping for R2P if sitemap yields
    no blog URLs.
    """
    from rich.console import Console

    console = Console()
    sitemaps = _load_sitemaps()

    if not sitemaps:
        console.print(
            "[bold yellow]Warning:[/bold yellow] No competitor sitemaps configured "
            "in config.yaml. Skipping competitor scrape."
        )
        return []

    results: list[TopicDict] = []

    for sitemap_url in sitemaps:
        try:
            blog_urls = _extract_urls_from_sitemap(sitemap_url)
        except Exception as exc:
            console.print(
                f"[bold red]Error fetching sitemap[/bold red] {sitemap_url}: {exc}"
            )
            blog_urls = []

        # R2P fallback: if sitemap yielded 0 blog URLs, try scraping index pages
        if not blog_urls and "rehab2perform.com" in sitemap_url:
            console.print(
                "[yellow]  R2P sitemap had 0 blog URLs — trying fallback pages...[/yellow]"
            )
            for fallback_url in _R2P_FALLBACKS:
                found = _extract_links_from_page(fallback_url)
                if found:
                    console.print(
                        f"[green]  Found {len(found)} links from {fallback_url}[/green]"
                    )
                    blog_urls.extend(found)

            # Deduplicate
            seen: set[str] = set()
            deduped: list[str] = []
            for u in blog_urls:
                if u not in seen:
                    seen.add(u)
                    deduped.append(u)
            blog_urls = deduped

        console.print(
            f"  {sitemap_url}: [cyan]{len(blog_urls)}[/cyan] blog URLs found"
        )

        for url in blog_urls[:_ARTICLES_PER_SITEMAP]:
            topic = _scrape_article(url)
            if topic is not None:
                results.append(topic)

    return results


# ---------------------------------------------------------------------------
# Standalone
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from rich.console import Console
    from rich.table import Table

    console = Console()
    console.print("[bold blue]Fetching competitor blog posts...[/bold blue]\n")

    topics = fetch_competitors()

    if not topics:
        console.print("[dim]No competitor articles found.[/dim]")
        raise SystemExit(0)

    table = Table(title="Competitor Blog Posts")
    table.add_column("#", style="dim", width=4)
    table.add_column("Title", style="cyan", max_width=50)
    table.add_column("Date", width=12)
    table.add_column("URL", style="dim", max_width=50)

    for i, t in enumerate(topics, 1):
        table.add_row(str(i), t["title"][:50], t["date"], t["url"][:50])

    console.print(table)
    console.print(f"\n[bold green]Total:[/bold green] {len(topics)} topics")
