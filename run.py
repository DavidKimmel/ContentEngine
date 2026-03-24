"""ContentEngine CLI — automated PT blog content pipeline."""

from __future__ import annotations

import json
from pathlib import Path

import click
from rich.console import Console

console = Console()

_DB_DIR = Path(__file__).resolve().parent / "db"


@click.group()
def cli() -> None:
    """ContentEngine: automated PT blog content pipeline."""


@cli.command()
def scrape() -> None:
    """Pull trends, PubMed abstracts, and competitor posts."""
    from scrapers import run_all_scrapers

    topics = run_all_scrapers()

    # Persist raw results
    output_path = _DB_DIR / "raw_topics.json"
    output_path.write_text(
        json.dumps(topics, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    console.print(
        f"\n[bold green]Saved {len(topics)} topics to {output_path}[/bold green]"
    )


@cli.command()
def score() -> None:
    """Rank scraped topics by relevance and gap opportunity."""
    from pipeline.scorer import save_queue, score_topics

    raw_path = _DB_DIR / "raw_topics.json"
    if not raw_path.exists():
        console.print(
            "[bold red]Error:[/bold red] db/raw_topics.json not found. "
            "Run 'python run.py scrape' first."
        )
        raise SystemExit(1)

    raw_topics = json.loads(raw_path.read_text(encoding="utf-8"))
    console.print(f"[bold blue]Scoring {len(raw_topics)} raw topics...[/bold blue]")

    scored = score_topics(raw_topics)
    out = save_queue(scored)

    console.print(
        f"[bold green]{len(scored)} topics made the cut (saved to {out})[/bold green]"
    )


@cli.command()
@click.option("--auto", is_flag=True, help="Generate the top 3 ungenerated topics.")
@click.option("--topic-id", type=int, default=None, help="Generate a specific topic by queue index.")
def generate(auto: bool, topic_id: int | None) -> None:
    """Create outlines and drafts via Claude agents."""
    from pipeline import run_pipeline

    queue_path = _DB_DIR / "scored_queue.json"
    if not queue_path.exists():
        console.print(
            "[bold red]Error:[/bold red] db/scored_queue.json not found. "
            "Run 'python run.py score' first."
        )
        raise SystemExit(1)

    queue_data = json.loads(queue_path.read_text(encoding="utf-8"))
    topics: list[dict] = queue_data.get("topics", [])

    if topic_id is not None:
        if topic_id < 0 or topic_id >= len(topics):
            console.print(
                f"[bold red]Error:[/bold red] topic-id {topic_id} out of range "
                f"(0-{len(topics) - 1})."
            )
            raise SystemExit(1)
        targets = [(topic_id, topics[topic_id])]
    else:
        ungenerated = [
            (i, t) for i, t in enumerate(topics)
            if t.get("status") != "generated"
        ]
        if not ungenerated:
            console.print("[yellow]All topics already generated.[/yellow]")
            return
        limit = 3 if auto else 1
        targets = ungenerated[:limit]

    for idx, topic in targets:
        console.print(
            f"\n[bold cyan]Generating [{idx}]:[/bold cyan] {topic['title'][:60]}"
        )
        filepath = run_pipeline(topic)

        if filepath:
            topics[idx]["status"] = "generated"
            topics[idx]["draft_path"] = filepath
            queue_data["topics"] = topics
            queue_path.write_text(
                json.dumps(queue_data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            console.print(f"[bold green]Done — {filepath}[/bold green]")
        else:
            console.print(f"[bold red]Failed to generate topic {idx}.[/bold red]")


@cli.command()
@click.option("--approve", type=str, default=None, help="Approve a draft by slug.")
@click.option("--revise", type=str, default=None, help="Mark a draft for revision by slug.")
@click.option("--notes", type=str, default="", help="Revision notes (used with --revise).")
def review(approve: str | None, revise: str | None, notes: str) -> None:
    """Review, approve, or request revisions on generated drafts."""
    from review.export import list_drafts, mark_approved, mark_revision

    if approve:
        mark_approved(approve)
        return

    if revise:
        if not notes:
            console.print(
                "[bold red]Error:[/bold red] --notes is required with --revise."
            )
            raise SystemExit(1)
        mark_revision(revise, notes)
        return

    # Default: list all drafts
    from rich.table import Table

    drafts = list_drafts()
    if not drafts:
        console.print("[yellow]No drafts found in drafts/ directory.[/yellow]")
        return

    table = Table(title="Draft Review Queue")
    table.add_column("#", style="dim", width=4)
    table.add_column("Title", style="cyan", max_width=50)
    table.add_column("Status", width=16)
    table.add_column("SEO", justify="right", width=5)
    table.add_column("Read Time", width=12)
    table.add_column("Generated", width=12)

    for i, d in enumerate(drafts, 1):
        status = d["status"]
        if status == "APPROVED":
            style = "[green]APPROVED[/green]"
        elif status == "NEEDS_REVISION":
            style = "[yellow]NEEDS_REVISION[/yellow]"
        else:
            style = "[dim]PENDING_REVIEW[/dim]"

        table.add_row(
            str(i),
            d["title"][:50],
            style,
            str(d["seo_score"]),
            d["estimated_read_time"],
            d["date_generated"],
        )

    console.print(table)


@cli.command()
@click.option("--slug", type=str, default=None, help="Publish a specific approved draft by slug.")
@click.option(
    "--approve-and-publish",
    type=str,
    default=None,
    help="Approve then immediately publish a draft by slug.",
)
@click.option("--all", "publish_all", is_flag=True, help="Publish all APPROVED drafts.")
def publish(slug: str | None, approve_and_publish: str | None, publish_all: bool) -> None:
    """Push approved drafts to the configured CMS."""
    import time

    from review.export import mark_approved
    from review.publish import publish_draft

    if approve_and_publish:
        console.print(f"[bold blue]Approving {approve_and_publish}...[/bold blue]")
        mark_approved(approve_and_publish)
        publish_draft(approve_and_publish)
        return

    if slug:
        publish_draft(slug)
        return

    if publish_all:
        from review.export import list_drafts

        drafts = list_drafts()
        approved = [d for d in drafts if d["status"] == "APPROVED"]
        if not approved:
            console.print("[yellow]No APPROVED drafts to publish.[/yellow]")
            return

        console.print(f"[bold blue]Publishing {len(approved)} approved drafts...[/bold blue]")
        for i, d in enumerate(approved):
            draft_slug = d["filename"].replace(".md", "")
            publish_draft(draft_slug)
            if i < len(approved) - 1:
                console.print("[dim]  Pausing 3s for rate limiting...[/dim]")
                time.sleep(3)
        return

    console.print(
        "[bold red]Error:[/bold red] Provide --slug, --approve-and-publish, or --all."
    )
    raise SystemExit(1)


@cli.command()
@click.option("--slug", type=str, required=True, help="Slug of the draft to preview.")
def preview(slug: str) -> None:
    """Render a draft to HTML and open in browser."""
    import re
    import webbrowser

    import markdown
    import yaml

    drafts_dir = Path(__file__).resolve().parent / "drafts"
    filepath = drafts_dir / f"{slug}.md"
    if not filepath.exists():
        console.print(f"[bold red]Error:[/bold red] No draft found for slug: {slug}")
        raise SystemExit(1)

    text = filepath.read_text(encoding="utf-8")
    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", text, re.DOTALL)
    if not fm_match:
        console.print("[bold red]Error:[/bold red] Could not parse frontmatter.")
        raise SystemExit(1)

    fm = yaml.safe_load(fm_match.group(1)) or {}
    raw_body = fm_match.group(2).strip()

    # Extract SEO notes from HTML comments
    seo_notes_parts: list[str] = []
    for match in re.finditer(r"<!--\s*(SEO NOTES|REVISION NOTES[^>]*)\s*\n?(.*?)-->", raw_body, re.DOTALL):
        seo_notes_parts.append(match.group(0))

    # Strip comments from body for rendering
    body_md = re.sub(r"<!--.*?-->", "", raw_body, flags=re.DOTALL).strip()

    md_converter = markdown.Markdown(extensions=["extra", "smarty"])
    body_html = md_converter.convert(body_md)

    title = fm.get("title", slug)
    status = fm.get("status", "UNKNOWN")
    seo_score = fm.get("seo_score", "")
    read_time = fm.get("estimated_read_time", "")
    keyword = fm.get("primary_keyword", "")
    date_gen = fm.get("date_generated", "")

    # Status badge color
    badge_colors = {
        "PENDING_REVIEW": ("#b7791f", "#fefcbf"),
        "APPROVED": ("#276749", "#c6f6d5"),
        "NEEDS_REVISION": ("#c53030", "#fed7d7"),
        "PUBLISHED": ("#2b6cb0", "#bee3f8"),
    }
    bg_color, text_color = badge_colors.get(status, ("#4a5568", "#e2e8f0"))

    # Build SEO notes panel
    seo_panel = ""
    if seo_notes_parts:
        notes_text = "\n".join(seo_notes_parts)
        # Clean up comment markers
        notes_text = notes_text.replace("<!--", "").replace("-->", "").strip()
        notes_html = notes_text.replace("\n", "<br>").replace("  - [ ]", "&nbsp;&nbsp;&#9744;")
        seo_panel = f"""<div class="seo-panel">
  <h3>Editor Notes</h3>
  <div class="seo-content">{notes_html}</div>
</div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} | Preview</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #f7f7f8; color: #1a1a2e; line-height: 1.8; margin: 0; font-size: 16px; }}
  .header {{ background: #fff; border-bottom: 2px solid #e2e8f0; padding: 1.5rem 2rem; }}
  .header-inner {{ max-width: 800px; margin: 0 auto; }}
  .header h1 {{ font-size: 1.8rem; margin: 0.5rem 0; color: #1a202c; }}
  .meta-bar {{ font-size: 0.82rem; color: #718096; display: flex; gap: 1.2rem; flex-wrap: wrap; align-items: center; margin-top: 0.5rem; }}
  .status-badge {{ display: inline-block; background: {text_color}; color: {bg_color}; padding: 0.25rem 0.7rem; border-radius: 4px; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }}
  .content {{ max-width: 800px; margin: 2rem auto; background: #fff; padding: 2.5rem; border-radius: 6px; border: 1px solid #e2e8f0; }}
  .content h2 {{ font-size: 1.4rem; color: #1a202c; margin: 2rem 0 0.8rem; padding-bottom: 0.4rem; border-bottom: 1px solid #e2e8f0; }}
  .content h3 {{ font-size: 1.1rem; color: #2d3748; margin: 1.5rem 0 0.5rem; }}
  .content p {{ color: #4a5568; margin-bottom: 1rem; }}
  .content li {{ color: #4a5568; margin-bottom: 0.3rem; }}
  .content a {{ color: #2b6cb0; }}
  .content strong {{ color: #1a202c; }}
  .content blockquote {{ border-left: 3px solid #cbd5e0; padding: 0.8rem 1.2rem; margin: 1.2rem 0; background: #f7fafc; color: #718096; font-style: italic; }}
  .seo-panel {{ max-width: 800px; margin: 0 auto 2rem; background: #fffff0; border: 1px solid #ecc94b; border-radius: 6px; padding: 1.5rem; }}
  .seo-panel h3 {{ font-size: 1rem; color: #b7791f; margin: 0 0 0.8rem; text-transform: uppercase; letter-spacing: 0.5px; }}
  .seo-content {{ font-size: 0.85rem; color: #744210; line-height: 1.7; }}
</style>
</head>
<body>
<div class="header"><div class="header-inner">
  <span class="status-badge">{status}</span>
  <h1>{title}</h1>
  <div class="meta-bar">
    <span>SEO: {seo_score}/100</span>
    <span>{read_time}</span>
    <span>{keyword}</span>
    <span>{date_gen}</span>
  </div>
</div></div>
<div class="content">{body_html}</div>
{seo_panel}
</body></html>"""

    preview_dir = drafts_dir / "preview"
    preview_dir.mkdir(exist_ok=True)
    out_path = preview_dir / f"{slug}.html"
    out_path.write_text(html, encoding="utf-8")
    webbrowser.open(f"file:///{out_path.resolve()}")
    console.print(f"[bold green]Preview opened:[/bold green] drafts/preview/{slug}.html")


if __name__ == "__main__":
    cli()
