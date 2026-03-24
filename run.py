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


if __name__ == "__main__":
    cli()
