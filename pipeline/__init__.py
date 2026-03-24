"""Pipeline package — orchestrate outline, draft, SEO, and export stages."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console

from db.published_history import add_to_history
from pipeline.api import call_claude, get_usage, reset_usage
from pipeline.draft_agent import generate_draft
from pipeline.outline_agent import generate_outline
from pipeline.scorer import _classify_category
from pipeline.seo_agent import optimize_seo
from review.export import export_draft

console = Console()

_LOGS_DIR = Path(__file__).resolve().parents[1] / "logs"

# Pricing per token (claude-sonnet-4-20250514)
_INPUT_COST_PER_TOKEN = 0.000003
_OUTPUT_COST_PER_TOKEN = 0.000015


# ---------------------------------------------------------------------------
# Token cost helpers
# ---------------------------------------------------------------------------


def _format_cost(input_tokens: int, output_tokens: int) -> float:
    return round(
        input_tokens * _INPUT_COST_PER_TOKEN + output_tokens * _OUTPUT_COST_PER_TOKEN,
        4,
    )


def _log_cost(slug: str, agent_usages: dict[str, tuple[int, int]]) -> None:
    """Write per-post token usage and cost to logs/pipeline.log."""
    _LOGS_DIR.mkdir(exist_ok=True)
    total_in = sum(u[0] for u in agent_usages.values())
    total_out = sum(u[1] for u in agent_usages.values())
    cost = _format_cost(total_in, total_out)
    line = (
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] POST — "
        f"slug: {slug} | "
        f"tokens_in: {total_in} tokens_out: {total_out} "
        f"cost: ${cost}\n"
    )
    log_path = _LOGS_DIR / "pipeline.log"
    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(line)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_pipeline(topic: dict[str, Any]) -> str | None:
    """Run the full generation pipeline for a single topic.

    Returns the exported filepath on success, or None on failure.
    Logs per-agent token breakdown and estimated cost.
    Records published topic for future duplicate detection.
    """
    reset_usage()
    agent_usages: dict[str, tuple[int, int]] = {}

    try:
        console.print("[bold blue]  Step 1/4:[/bold blue] Generating outline...")
        outline = generate_outline(topic)
        agent_usages["outline"] = call_claude.last_call_usage
        console.print("[green]  Outline complete[/green]")

        console.print("[bold blue]  Step 2/4:[/bold blue] Writing draft...")
        draft = generate_draft(topic, outline)
        agent_usages["draft"] = call_claude.last_call_usage
        console.print("[green]  Draft complete[/green]")

        console.print("[bold blue]  Step 3/4:[/bold blue] SEO analysis...")
        seo = optimize_seo(draft, outline)
        agent_usages["seo"] = call_claude.last_call_usage
        console.print("[green]  SEO analysis complete[/green]")

        console.print("[bold blue]  Step 4/4:[/bold blue] Exporting...")
        filepath = export_draft(topic, outline, draft, seo)
        console.print(f"[green]  Exported to {filepath}[/green]")

        # Record for future duplicate detection
        category = _classify_category(topic.get("title", ""))
        add_to_history(outline, category)

        # Print per-agent token breakdown
        total_in = sum(u[0] for u in agent_usages.values())
        total_out = sum(u[1] for u in agent_usages.values())
        total_cost = _format_cost(total_in, total_out)

        o = agent_usages.get("outline", (0, 0))
        d = agent_usages.get("draft", (0, 0))
        s = agent_usages.get("seo", (0, 0))
        console.print(f"[dim]  Outline:  {o[0]:,} in / {o[1]:,} out[/dim]")
        console.print(f"[dim]  Draft:    {d[0]:,} in / {d[1]:,} out[/dim]")
        console.print(f"[dim]  SEO:      {s[0]:,} in / {s[1]:,} out[/dim]")
        console.print(f"[dim]  {'─' * 35}[/dim]")
        console.print(f"[dim]  Total cost: ${total_cost}[/dim]")

        slug = outline.get("slug", "unknown")
        _log_cost(slug, agent_usages)

        return filepath

    except Exception as exc:
        console.print(f"[bold red]  Pipeline error:[/bold red] {exc}")
        _log_cost("FAILED", agent_usages)
        return None
