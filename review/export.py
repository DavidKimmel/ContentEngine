"""Export module — assemble final draft Markdown files with frontmatter."""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

import yaml

_DRAFTS_DIR = Path(__file__).resolve().parents[1] / "drafts"
_DB_DIR = Path(__file__).resolve().parents[1] / "db"


# ---------------------------------------------------------------------------
# Draft export (used by pipeline)
# ---------------------------------------------------------------------------


def export_draft(
    topic: dict[str, Any],
    outline: dict[str, Any],
    draft: str,
    seo: dict[str, Any],
) -> str:
    """Assemble and write a complete Markdown file to drafts/.

    Returns the full file path as a string.
    """
    # --- 1. Build frontmatter ---
    frontmatter: dict[str, Any] = {
        "title": seo.get("optimized_title", outline.get("title", "")),
        "slug": outline.get("slug", "untitled"),
        "meta_description": seo.get(
            "optimized_meta_description", outline.get("meta_description", "")
        ),
        "primary_keyword": outline.get("primary_keyword", ""),
        "secondary_keywords": outline.get("secondary_keywords", []),
        "featured_snippet_target": outline.get("featured_snippet_target", ""),
        "schema_type": seo.get("schema_type", "Article"),
        "estimated_read_time": seo.get("estimated_read_time", ""),
        "seo_score": seo.get("seo_score", 0),
        "status": "PENDING_REVIEW",
        "date_generated": date.today().isoformat(),
        "source": topic.get("source", ""),
        "source_url": topic.get("url", ""),
        "doi": topic.get("doi", ""),
        "resurgent_angle": outline.get("resurgent_angle", ""),
    }

    fm_str = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)

    # --- 2. SEO notes comment block ---
    issues = seo.get("issues", [])
    suggestions = seo.get("suggestions", [])
    links = seo.get("internal_links_to_add", [])

    seo_lines = ["<!-- SEO NOTES"]
    seo_lines.append(f"SEO Score: {seo.get('seo_score', 'N/A')}/100")
    seo_lines.append(
        f"Primary keyword density: {seo.get('primary_keyword_density', 'N/A')}"
    )
    seo_lines.append("")

    if issues:
        seo_lines.append("Issues:")
        for issue in issues:
            seo_lines.append(f"  - [ ] {issue}")
        seo_lines.append("")

    if suggestions:
        seo_lines.append("Suggestions:")
        for suggestion in suggestions:
            seo_lines.append(f"  - [ ] {suggestion}")
        seo_lines.append("")

    if links:
        seo_lines.append("Internal links to add:")
        for link in links:
            seo_lines.append(f"  - [ ] {link}")
        seo_lines.append("")

    seo_lines.append("-->")
    seo_block = "\n".join(seo_lines)

    # --- 3. Sources section ---
    source_lines = ["## Sources", ""]
    if topic.get("url"):
        source_lines.append(f"- Original source: {topic['url']}")
    if topic.get("doi"):
        source_lines.append(f"- DOI: {topic['doi']}")
    sources_block = "\n".join(source_lines)

    # --- 4. Assemble full file ---
    parts = [
        f"---\n{fm_str}---",
        seo_block,
        draft,
        sources_block,
    ]
    content = "\n\n".join(parts) + "\n"

    # --- 5. Write to file ---
    slug = outline.get("slug", "untitled")
    filename = f"{slug}.md"
    filepath = _DRAFTS_DIR / filename
    filepath.write_text(content, encoding="utf-8")

    return str(filepath)


# ---------------------------------------------------------------------------
# Review functions
# ---------------------------------------------------------------------------

_FM_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)


def _read_frontmatter(filepath: Path) -> dict[str, Any]:
    """Read only the YAML frontmatter from a Markdown file."""
    text = filepath.read_text(encoding="utf-8")
    match = _FM_RE.match(text)
    if not match:
        return {}
    return yaml.safe_load(match.group(1)) or {}


def list_drafts() -> list[dict[str, Any]]:
    """Scan drafts/ for .md files and return frontmatter summaries."""
    results: list[dict[str, Any]] = []
    for fp in sorted(_DRAFTS_DIR.glob("*.md")):
        fm = _read_frontmatter(fp)
        if not fm:
            continue
        results.append(
            {
                "filename": fp.name,
                "title": fm.get("title", ""),
                "status": fm.get("status", "UNKNOWN"),
                "seo_score": fm.get("seo_score", ""),
                "primary_keyword": fm.get("primary_keyword", ""),
                "estimated_read_time": fm.get("estimated_read_time", ""),
                "date_generated": fm.get("date_generated", ""),
            }
        )
    return results


def mark_approved(slug: str) -> None:
    """Mark a draft as APPROVED in both the .md frontmatter and scored_queue.json."""
    filepath = _DRAFTS_DIR / f"{slug}.md"
    if not filepath.exists():
        raise FileNotFoundError(f"No draft found for slug: {slug}")

    # Update frontmatter in the Markdown file
    text = filepath.read_text(encoding="utf-8")
    updated = text.replace("status: PENDING_REVIEW", "status: APPROVED", 1).replace(
        "status: NEEDS_REVISION", "status: APPROVED", 1
    )
    filepath.write_text(updated, encoding="utf-8")

    # Update scored_queue.json
    queue_path = _DB_DIR / "scored_queue.json"
    if queue_path.exists():
        queue_data = json.loads(queue_path.read_text(encoding="utf-8"))
        for topic in queue_data.get("topics", []):
            draft_path = topic.get("draft_path", "")
            if slug in draft_path:
                topic["status"] = "approved"
        queue_path.write_text(
            json.dumps(queue_data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    from rich.console import Console

    Console().print(f"[bold green]Approved:[/bold green] {filepath.name}")


def mark_revision(slug: str, notes: str) -> None:
    """Mark a draft as NEEDS_REVISION and insert revision notes."""
    filepath = _DRAFTS_DIR / f"{slug}.md"
    if not filepath.exists():
        raise FileNotFoundError(f"No draft found for slug: {slug}")

    text = filepath.read_text(encoding="utf-8")

    # Update status
    updated = text.replace("status: PENDING_REVIEW", "status: NEEDS_REVISION", 1).replace(
        "status: APPROVED", "status: NEEDS_REVISION", 1
    )

    # Insert revision notes after the SEO NOTES comment block
    revision_block = f"\n\n<!-- REVISION NOTES: {notes} -->"
    updated = updated.replace("\n-->", f"\n-->{revision_block}", 1)

    filepath.write_text(updated, encoding="utf-8")

    from rich.console import Console

    Console().print(
        f"[bold yellow]Marked for revision:[/bold yellow] {filepath.name}"
    )
