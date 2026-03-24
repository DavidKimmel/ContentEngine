"""Pipeline package — orchestrate outline, draft, SEO, and export stages."""

from __future__ import annotations

from typing import Any

from rich.console import Console

from pipeline.draft_agent import generate_draft
from pipeline.outline_agent import generate_outline
from pipeline.seo_agent import optimize_seo
from review.export import export_draft

console = Console()


def run_pipeline(topic: dict[str, Any]) -> str | None:
    """Run the full generation pipeline for a single topic.

    Returns the exported filepath on success, or None on failure.
    """
    try:
        console.print("[bold blue]  Step 1/4:[/bold blue] Generating outline...")
        outline = generate_outline(topic)
        console.print("[green]  Outline complete[/green]")

        console.print("[bold blue]  Step 2/4:[/bold blue] Writing draft...")
        draft = generate_draft(topic, outline)
        console.print("[green]  Draft complete[/green]")

        console.print("[bold blue]  Step 3/4:[/bold blue] SEO analysis...")
        seo = optimize_seo(draft, outline)
        console.print("[green]  SEO analysis complete[/green]")

        console.print("[bold blue]  Step 4/4:[/bold blue] Exporting...")
        filepath = export_draft(topic, outline, draft, seo)
        console.print(f"[green]  Exported to {filepath}[/green]")

        return filepath

    except Exception as exc:
        console.print(f"[bold red]  Pipeline error:[/bold red] {exc}")
        return None
