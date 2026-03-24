"""PubMed scraper — fetch recent PT research via NCBI E-utilities REST API."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import requests
import yaml

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
_ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
_MAX_PER_SEARCH = 10

_QUERIES = [
    "ACL reconstruction rehabilitation return to sport",
    "running injury physical therapy biomechanics",
    "dry needling sports physical therapy outcomes",
    "anterior cruciate ligament injury prevention program",
    "sports rehabilitation manual therapy outcomes",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TopicDict = dict[str, Any]


def _esearch(term: str) -> list[str]:
    """Return up to _MAX_PER_SEARCH PubMed IDs for *term*, sorted by date."""
    params = {
        "db": "pubmed",
        "term": term,
        "retmax": _MAX_PER_SEARCH,
        "sort": "date",
        "retmode": "xml",
    }
    resp = requests.get(_ESEARCH_URL, params=params, timeout=15)
    resp.raise_for_status()
    root = ElementTree.fromstring(resp.text)
    return [id_el.text for id_el in root.findall(".//Id") if id_el.text]


def _esummary(pmids: list[str]) -> list[TopicDict]:
    """Fetch document summaries for a list of PubMed IDs."""
    if not pmids:
        return []

    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
    }
    resp = requests.get(_ESUMMARY_URL, params=params, timeout=15)
    resp.raise_for_status()
    root = ElementTree.fromstring(resp.text)

    results: list[TopicDict] = []
    for doc in root.findall(".//DocSum"):
        pmid = ""
        title = ""
        pub_date = ""
        doi = ""

        id_el = doc.find("Id")
        if id_el is not None and id_el.text:
            pmid = id_el.text.strip()

        for item in doc.findall("Item"):
            name = item.attrib.get("Name", "")
            text = (item.text or "").strip()
            if name == "Title":
                title = text.rstrip(".")
            elif name == "PubDate":
                pub_date = text
            elif name == "DOI":
                doi = text
            elif name == "ElocationID" and not doi and text.startswith("doi:"):
                doi = text.replace("doi: ", "").replace("doi:", "").strip()

        if not title:
            continue

        url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""

        results.append(
            {
                "title": title,
                "source": "pubmed",
                "url": url,
                "date": pub_date,
                "score": 0.0,  # raw relevance assigned later by scorer
                "summary": title,
                "doi": doi,
            }
        )

    return results


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fetch_pubmed() -> list[TopicDict]:
    """Return deduplicated topic dicts from PubMed E-utilities.

    Runs 5 hardcoded sports-PT queries, fetches 10 results each (50 total
    before dedup), deduplicates by DOI or title.
    """
    all_topics: list[TopicDict] = []

    for kw in _QUERIES:
        try:
            pmids = _esearch(kw)
            topics = _esummary(pmids)
            all_topics.extend(topics)
        except Exception:
            continue
        time.sleep(0.5)

    # Deduplicate by DOI first, then by lowered title
    seen_dois: set[str] = set()
    seen_titles: set[str] = set()
    deduped: list[TopicDict] = []

    for t in all_topics:
        doi = t["doi"]
        low_title = t["title"].lower()

        if doi:
            if doi in seen_dois:
                continue
            seen_dois.add(doi)
        else:
            if low_title in seen_titles:
                continue
        seen_titles.add(low_title)
        deduped.append(t)

    return deduped


# ---------------------------------------------------------------------------
# Standalone
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from rich.console import Console
    from rich.table import Table

    console = Console()
    console.print("[bold blue]Fetching PubMed articles...[/bold blue]\n")

    topics = fetch_pubmed()

    table = Table(title="PubMed — Recent PT Research")
    table.add_column("#", style="dim", width=4)
    table.add_column("Title", style="cyan", max_width=55)
    table.add_column("Date", width=12)
    table.add_column("DOI", style="dim", max_width=30)

    for i, t in enumerate(topics, 1):
        table.add_row(str(i), t["title"][:55], t["date"], t["doi"][:30])

    console.print(table)
    console.print(f"\n[bold green]Total:[/bold green] {len(topics)} topics")
