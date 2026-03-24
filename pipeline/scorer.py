"""Topic scorer — rank, deduplicate, and filter scraped topics."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.yaml"
_DB_DIR = Path(__file__).resolve().parents[1] / "db"


def _load_config() -> dict[str, Any]:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


# ---------------------------------------------------------------------------
# Sub-score helpers
# ---------------------------------------------------------------------------


def _score_relevance(title: str, keywords: list[str], gaps: list[str]) -> float:
    """0-25: how well does the title match configured keywords / content gaps."""
    title_lower = title.lower()
    targets = [k.lower() for k in keywords] + [g.lower() for g in gaps]

    for target in targets:
        if target in title_lower or title_lower in target:
            return 25.0

    title_words = set(title_lower.split())
    for target in targets:
        target_words = set(target.split())
        if title_words & target_words:
            return 15.0

    return 5.0


def _score_source(source: str) -> float:
    """0-25: authority weight by source type."""
    return {"pubmed": 25.0, "competitor": 20.0, "google_trends": 15.0}.get(
        source, 5.0
    )


def _score_recency(date_str: str) -> float:
    """0-25: freshness based on publication date."""
    if not date_str:
        return 5.0

    now = datetime.now()

    # Try several common date formats from our scrapers
    for fmt in ("%Y-%m-%d", "%Y %b %d", "%Y %b", "%Y"):
        try:
            pub = datetime.strptime(date_str.strip(), fmt)
            delta = now - pub
            if delta <= timedelta(days=30):
                return 25.0
            if delta <= timedelta(days=90):
                return 18.0
            if delta <= timedelta(days=180):
                return 10.0
            return 5.0
        except ValueError:
            continue

    return 5.0


_CLINICAL_WORDS = {
    "acl", "knee", "running", "sport", "athlete",
    "rehab", "physical therapy", "pt", "injury", "pain",
    "shoulder", "hip", "movement", "gait", "strength",
}


def _score_opportunity(title: str, gaps: list[str]) -> float:
    """0-25: does the title align with a known content gap AND clinical domain.

    25 points — title matches a content gap AND contains a clinical word.
    10 points — title matches a content gap but no clinical word.
     0 points — no content gap match.
    """
    title_lower = title.lower()
    title_words = set(title_lower.split())

    gap_match = False
    for gap in gaps:
        gap_lower = gap.lower()
        gap_words = set(gap_lower.split())
        overlap = title_words & gap_words
        meaningful = {w for w in overlap if len(w) > 2}
        if len(meaningful) >= 2:
            gap_match = True
            break

    if not gap_match:
        return 0.0

    # Check for clinical word presence (handle multi-word entries like "physical therapy")
    for cw in _CLINICAL_WORDS:
        if cw in title_lower:
            return 25.0

    return 10.0


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


def _word_overlap_ratio(a: str, b: str) -> float:
    """Return the fraction of shared words between two titles (0.0-1.0)."""
    words_a = set(a.lower().split())
    words_b = set(b.lower().split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    return len(intersection) / min(len(words_a), len(words_b))


def _deduplicate(topics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove topics whose titles share >70% word overlap, keeping higher score."""
    kept: list[dict[str, Any]] = []
    for topic in topics:
        is_dup = False
        for existing in kept:
            if _word_overlap_ratio(topic["title"], existing["title"]) > 0.70:
                is_dup = True
                break
        if not is_dup:
            kept.append(topic)
    return kept


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def score_topics(topics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Score, deduplicate, filter, and rank a list of topic dicts.

    Returns topics sorted by total_score descending, filtered to those
    meeting the minimum score threshold from config.
    """
    cfg = _load_config()
    keywords: list[str] = cfg.get("pt_keywords", [])
    gaps: list[str] = cfg.get("content_gaps", [])
    min_score: float = cfg.get("settings", {}).get("min_score_to_generate", 60.0)

    scored: list[dict[str, Any]] = []
    for t in topics:
        title = t.get("title", "")
        source = t.get("source", "")
        date_str = t.get("date", "")

        relevance = _score_relevance(title, keywords, gaps)
        authority = _score_source(source)
        recency = _score_recency(date_str)
        opportunity = _score_opportunity(title, gaps)
        total = relevance + authority + recency + opportunity

        scored_topic = {
            **t,
            "relevance_score": relevance,
            "authority_score": authority,
            "recency_score": recency,
            "opportunity_score": opportunity,
            "total_score": total,
        }
        scored.append(scored_topic)

    # Sort by total_score descending before dedup so we keep the best
    scored.sort(key=lambda x: x["total_score"], reverse=True)
    deduped = _deduplicate(scored)

    # Filter by minimum score
    qualified = [t for t in deduped if t["total_score"] >= min_score]

    return qualified


def save_queue(topics: list[dict[str, Any]]) -> Path:
    """Persist the scored topic list to db/scored_queue.json with a timestamp."""
    payload = {
        "timestamp": datetime.now().isoformat(),
        "count": len(topics),
        "topics": topics,
    }
    output_path = _DB_DIR / "scored_queue.json"
    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return output_path


# ---------------------------------------------------------------------------
# Standalone
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from rich.console import Console
    from rich.table import Table

    console = Console()

    raw_path = _DB_DIR / "raw_topics.json"
    if not raw_path.exists():
        console.print(
            "[bold red]Error:[/bold red] db/raw_topics.json not found. "
            "Run 'python run.py scrape' first."
        )
        raise SystemExit(1)

    raw_topics = json.loads(raw_path.read_text(encoding="utf-8"))
    console.print(
        f"[bold blue]Scoring {len(raw_topics)} raw topics...[/bold blue]\n"
    )

    scored = score_topics(raw_topics)

    table = Table(title=f"Top Scored Topics ({len(scored)} qualified)")
    table.add_column("#", style="dim", width=4)
    table.add_column("Title", style="cyan", max_width=45)
    table.add_column("Source", width=14)
    table.add_column("Rel", justify="right", width=5)
    table.add_column("Auth", justify="right", width=5)
    table.add_column("Rec", justify="right", width=5)
    table.add_column("Opp", justify="right", width=5)
    table.add_column("Total", justify="right", style="bold green", width=6)

    for i, t in enumerate(scored[:10], 1):
        table.add_row(
            str(i),
            t["title"][:45],
            t["source"],
            str(t["relevance_score"]),
            str(t["authority_score"]),
            str(t["recency_score"]),
            str(t["opportunity_score"]),
            str(t["total_score"]),
        )

    console.print(table)

    out = save_queue(scored)
    console.print(f"\n[bold green]Saved {len(scored)} topics to {out}[/bold green]")
