"""Published topics history — duplicate detection across pipeline runs."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

_HISTORY_PATH = Path(__file__).resolve().parent / "published_topics.json"


def load_history() -> list[dict[str, Any]]:
    """Load published topics history.

    Returns list of dicts with: slug, title, primary_keyword, published_date, category.
    Returns empty list if file doesn't exist.
    """
    if not _HISTORY_PATH.exists():
        return []
    try:
        data = json.loads(_HISTORY_PATH.read_text(encoding="utf-8"))
        return data.get("entries", [])
    except (json.JSONDecodeError, KeyError):
        return []


def is_duplicate(topic: dict[str, Any], history: list[dict[str, Any]]) -> bool:
    """Check if a topic duplicates any previously published entry.

    Returns True if ANY of:
    - Title has >60% word overlap with a history entry title
    - primary_keyword (if set) exactly matches a history entry primary_keyword
    """
    if not history:
        return False

    title = topic.get("title", "")
    title_words = set(title.lower().split())

    for entry in history:
        # Word overlap check
        entry_words = set(entry.get("title", "").lower().split())
        if title_words and entry_words:
            overlap = len(title_words & entry_words) / min(
                len(title_words), len(entry_words)
            )
            if overlap > 0.60:
                return True

        # Primary keyword exact match
        topic_kw = topic.get("primary_keyword", "").strip().lower()
        entry_kw = entry.get("primary_keyword", "").strip().lower()
        if topic_kw and entry_kw and topic_kw == entry_kw:
            return True

    return False


def add_to_history(outline: dict[str, Any], category: str) -> None:
    """Append a new entry to published_topics.json.

    Creates the file if it doesn't exist.
    """
    history = load_history()
    history.append(
        {
            "slug": outline.get("slug", ""),
            "title": outline.get("title", ""),
            "primary_keyword": outline.get("primary_keyword", ""),
            "category": category,
            "published_date": date.today().isoformat(),
        }
    )
    _HISTORY_PATH.write_text(
        json.dumps({"entries": history}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
