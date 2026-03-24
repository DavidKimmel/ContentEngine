"""Google Trends scraper — fetch rising PT-related queries via pytrends."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import yaml
from pytrends.request import TrendReq

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.yaml"


def _load_keywords() -> list[str]:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as fh:
        cfg: dict[str, Any] = yaml.safe_load(fh)
    return cfg.get("pt_keywords", [])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

TopicDict = dict[str, Any]

_RISING_CAP = 5


def fetch_trends() -> list[TopicDict]:
    """Return deduplicated topic dicts from Google Trends rising queries.

    Searches the past 7 days, US only, capped at 5 rising queries per keyword.
    """
    keywords = _load_keywords()
    if not keywords:
        return []

    pytrends = TrendReq(hl="en-US", tz=360)
    seen_titles: set[str] = set()
    results: list[TopicDict] = []

    for kw in keywords:
        try:
            pytrends.build_payload([kw], timeframe="now 7-d", geo="US")
            related: dict[str, Any] = pytrends.related_queries()
        except Exception:
            continue

        rising_df = related.get(kw, {}).get("rising")
        if rising_df is None or rising_df.empty:
            continue

        for _, row in rising_df.head(_RISING_CAP).iterrows():
            title = str(row.get("query", "")).strip()
            if not title or title.lower() in seen_titles:
                continue

            seen_titles.add(title.lower())

            # Google Trends "value" for rising queries can be an int or str
            raw_value = row.get("value", 0)
            try:
                score = min(float(raw_value), 100.0)
            except (TypeError, ValueError):
                score = 50.0

            results.append(
                {
                    "title": title,
                    "source": "google_trends",
                    "url": f"https://trends.google.com/trends/explore?q={title.replace(' ', '+')}&geo=US",
                    "date": "",
                    "score": round(score, 1),
                    "summary": f"Rising Google Trends query related to '{kw}'.",
                    "doi": "",
                }
            )

        # Be polite to the API
        time.sleep(1.0)

    return results


# ---------------------------------------------------------------------------
# Standalone
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from rich.console import Console
    from rich.table import Table

    console = Console()
    console.print("[bold blue]Fetching Google Trends rising queries...[/bold blue]\n")

    topics = fetch_trends()

    table = Table(title="Google Trends — Rising PT Queries")
    table.add_column("#", style="dim", width=4)
    table.add_column("Title", style="cyan", max_width=50)
    table.add_column("Score", justify="right")
    table.add_column("URL", style="dim", max_width=60)

    for i, t in enumerate(topics, 1):
        table.add_row(str(i), t["title"], str(t["score"]), t["url"])

    console.print(table)
    console.print(f"\n[bold green]Total:[/bold green] {len(topics)} topics")
