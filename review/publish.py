"""Publish module — push approved drafts to CMS platforms."""

from __future__ import annotations

import json
import os
import re
from base64 import b64encode
from datetime import date
from pathlib import Path
from typing import Any

import requests
import yaml
from dotenv import load_dotenv
from rich.console import Console

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

_DRAFTS_DIR = Path(__file__).resolve().parents[1] / "drafts"
_DB_DIR = Path(__file__).resolve().parents[1] / "db"
_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)", re.DOTALL)

console = Console()


# ---------------------------------------------------------------------------
# Frontmatter helpers
# ---------------------------------------------------------------------------


def _read_draft(slug: str) -> tuple[dict[str, Any], str, Path]:
    """Read a draft file, return (frontmatter_dict, body_text, filepath)."""
    filepath = _DRAFTS_DIR / f"{slug}.md"
    if not filepath.exists():
        raise FileNotFoundError(f"No draft found for slug: {slug}")

    text = filepath.read_text(encoding="utf-8")
    match = _FM_RE.match(text)
    if not match:
        raise ValueError(f"Could not parse frontmatter in {filepath.name}")

    fm = yaml.safe_load(match.group(1)) or {}
    body = match.group(2).strip()
    return fm, body, filepath


def _update_frontmatter(filepath: Path, updates: dict[str, Any]) -> None:
    """Update specific frontmatter fields in a draft file."""
    text = filepath.read_text(encoding="utf-8")
    match = _FM_RE.match(text)
    if not match:
        return

    fm = yaml.safe_load(match.group(1)) or {}
    fm.update(updates)
    body = match.group(2)

    fm_str = yaml.dump(fm, default_flow_style=False, sort_keys=False)
    filepath.write_text(f"---\n{fm_str}---\n{body}", encoding="utf-8")


def _update_queue_status(slug: str, status: str) -> None:
    """Update a topic's status in scored_queue.json by matching its draft_path."""
    queue_path = _DB_DIR / "scored_queue.json"
    if not queue_path.exists():
        return

    queue_data = json.loads(queue_path.read_text(encoding="utf-8"))
    for topic in queue_data.get("topics", []):
        if slug in topic.get("draft_path", ""):
            topic["status"] = status
    queue_path.write_text(
        json.dumps(queue_data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# CMS publishers
# ---------------------------------------------------------------------------


def _publish_wordpress(
    title: str, slug: str, body: str, meta: str, tags: list[str]
) -> str:
    """POST to WordPress REST API as a draft. Returns the WP post ID."""
    wp_url = os.environ.get("WP_URL", "").rstrip("/")
    wp_user = os.environ.get("WP_USER", "")
    wp_pass = os.environ.get("WP_APP_PASSWORD", "")

    if not all([wp_url, wp_user, wp_pass]):
        raise ValueError(
            "Missing WordPress credentials. Set WP_URL, WP_USER, and "
            "WP_APP_PASSWORD in .env"
        )

    credentials = b64encode(f"{wp_user}:{wp_pass}".encode()).decode()
    headers = {
        "Authorization": f"Basic {credentials}",
        "Content-Type": "application/json",
    }

    payload = {
        "title": title,
        "slug": slug,
        "content": body,
        "status": "draft",
        "excerpt": meta,
    }

    resp = requests.post(
        f"{wp_url}/wp-json/wp/v2/posts",
        headers=headers,
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    post_id = resp.json().get("id", "unknown")
    return str(post_id)


def _publish_webflow(
    title: str, slug: str, body: str, meta: str, tags: list[str]
) -> str:
    """POST to Webflow CMS API v2 as a draft. Returns the Webflow item ID."""
    api_key = os.environ.get("WEBFLOW_API_KEY", "")
    collection_id = os.environ.get("WEBFLOW_COLLECTION_ID", "")

    if not all([api_key, collection_id]):
        raise ValueError(
            "Missing Webflow credentials. Set WEBFLOW_API_KEY and "
            "WEBFLOW_COLLECTION_ID in .env"
        )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "accept": "application/json",
    }

    payload = {
        "isArchived": False,
        "isDraft": True,
        "fieldData": {
            "name": title,
            "slug": slug,
            "post-body": body,
            "meta-description": meta,
        },
    }

    resp = requests.post(
        f"https://api.webflow.com/v2/collections/{collection_id}/items",
        headers=headers,
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    item_id = resp.json().get("id", "unknown")
    return str(item_id)


def _publish_generic(
    title: str, slug: str, body: str, meta: str, tags: list[str]
) -> str:
    """POST to a generic CMS endpoint as JSON. Returns the response status code."""
    cms_url = os.environ.get("GENERIC_CMS_URL", "")
    cms_key = os.environ.get("GENERIC_CMS_KEY", "")

    if not cms_url:
        raise ValueError("Missing GENERIC_CMS_URL in .env")

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if cms_key:
        headers["Authorization"] = f"Bearer {cms_key}"

    payload = {
        "title": title,
        "slug": slug,
        "body": body,
        "meta_description": meta,
        "tags": tags,
        "status": "draft",
    }

    resp = requests.post(cms_url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    return str(resp.status_code)


_PUBLISHERS = {
    "wordpress": _publish_wordpress,
    "webflow": _publish_webflow,
    "generic": _publish_generic,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def publish_draft(slug: str) -> bool:
    """Publish an approved draft to the configured CMS.

    Returns True on success, False on failure. Never publishes unapproved drafts.
    """
    try:
        fm, body, filepath = _read_draft(slug)
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        return False

    status = fm.get("status", "")
    if status != "APPROVED":
        console.print(
            f"[bold yellow]Warning:[/bold yellow] Draft '{slug}' has status "
            f"'{status}', not APPROVED. Skipping — approve it first."
        )
        return False

    cms_type = os.environ.get("CMS_TYPE", "").lower().strip()
    publisher = _PUBLISHERS.get(cms_type)
    if not publisher:
        console.print(
            f"[bold red]Error:[/bold red] Unknown or missing CMS_TYPE '{cms_type}'. "
            f"Set CMS_TYPE in .env to: wordpress, webflow, or generic"
        )
        return False

    title = fm.get("title", "")
    meta = fm.get("meta_description", "")
    tags = fm.get("secondary_keywords", [])

    try:
        result = publisher(title, slug, body, meta, tags)
    except Exception as exc:
        console.print(f"[bold red]Publish failed:[/bold red] {exc}")
        return False

    # Success — update status
    _update_frontmatter(filepath, {
        "status": "PUBLISHED",
        "published_date": date.today().isoformat(),
    })
    _update_queue_status(slug, "published")

    console.print(
        f"[bold green]Published:[/bold green] {filepath.name} "
        f"(CMS: {cms_type}, result: {result})"
    )
    return True
