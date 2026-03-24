"""ContentEngine weekly pipeline runner.

Runs the full scrape -> score -> generate pipeline in sequence,
logs results, and handles errors gracefully.

Usage:
    python schedule.py
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

from rich.console import Console

console = Console()

_ROOT = Path(__file__).resolve().parent
_DB_DIR = _ROOT / "db"
_LOGS_DIR = _ROOT / "logs"


def main() -> None:
    start = time.time()
    now = datetime.now()

    console.print(
        f"\n[bold magenta]ContentEngine Weekly Run — "
        f"{now.strftime('%Y-%m-%d %H:%M:%S')}[/bold magenta]\n"
    )

    scraped_count = 0
    scored_count = 0
    generated_count = 0
    pending_count = 0

    # --- Step 1: Scrape ---
    console.print("[bold blue]Step 1/3: Scraping...[/bold blue]")
    try:
        from scrapers import run_all_scrapers

        topics = run_all_scrapers()
        scraped_count = len(topics)

        raw_path = _DB_DIR / "raw_topics.json"
        raw_path.write_text(
            json.dumps(topics, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        console.print(f"[green]  Scraped {scraped_count} topics[/green]\n")
    except Exception as exc:
        console.print(f"[bold red]  Scrape failed:[/bold red] {exc}\n")

    # --- Step 2: Score ---
    console.print("[bold blue]Step 2/3: Scoring...[/bold blue]")
    try:
        from pipeline.scorer import save_queue, score_topics

        raw_path = _DB_DIR / "raw_topics.json"
        if raw_path.exists():
            raw_topics = json.loads(raw_path.read_text(encoding="utf-8"))
            scored = score_topics(raw_topics)
            scored_count = len(scored)
            save_queue(scored)
            console.print(f"[green]  {scored_count} topics queued[/green]\n")
        else:
            console.print("[yellow]  No raw_topics.json — skipping score[/yellow]\n")
    except Exception as exc:
        console.print(f"[bold red]  Score failed:[/bold red] {exc}\n")

    # --- Step 3: Generate top 3 ---
    console.print("[bold blue]Step 3/3: Generating drafts...[/bold blue]")
    try:
        from pipeline import run_pipeline

        queue_path = _DB_DIR / "scored_queue.json"
        if queue_path.exists():
            queue_data = json.loads(queue_path.read_text(encoding="utf-8"))
            all_topics: list[dict] = queue_data.get("topics", [])

            ungenerated = [
                (i, t)
                for i, t in enumerate(all_topics)
                if t.get("status") != "generated"
                and t.get("status") != "approved"
                and t.get("status") != "published"
            ]

            for idx, topic in ungenerated[:3]:
                console.print(
                    f"\n  [cyan]Generating [{idx}]:[/cyan] {topic['title'][:60]}"
                )
                filepath = run_pipeline(topic)
                if filepath:
                    generated_count += 1
                    all_topics[idx]["status"] = "generated"
                    all_topics[idx]["draft_path"] = filepath
                    queue_data["topics"] = all_topics
                    queue_path.write_text(
                        json.dumps(queue_data, indent=2, ensure_ascii=False),
                        encoding="utf-8",
                    )

            console.print(f"\n[green]  Generated {generated_count} drafts[/green]\n")
        else:
            console.print(
                "[yellow]  No scored_queue.json — skipping generate[/yellow]\n"
            )
    except Exception as exc:
        console.print(f"[bold red]  Generate failed:[/bold red] {exc}\n")

    # --- Count pending ---
    try:
        from review.export import list_drafts

        drafts = list_drafts()
        pending_count = sum(1 for d in drafts if d["status"] == "PENDING_REVIEW")
    except Exception:
        pass

    # --- Summary ---
    elapsed = int(time.time() - start)
    console.print("[bold magenta]Pipeline Summary[/bold magenta]")
    console.print(f"  Topics scraped:          {scraped_count}")
    console.print(f"  Topics scored and queued: {scored_count}")
    console.print(f"  New drafts generated:    {generated_count}")
    console.print(f"  Drafts pending review:   {pending_count}")
    console.print(f"  Time elapsed:            {elapsed}s\n")

    # --- Log ---
    _LOGS_DIR.mkdir(exist_ok=True)
    log_line = (
        f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] RUN COMPLETE | "
        f"scraped={scraped_count} scored={scored_count} "
        f"generated={generated_count} pending={pending_count} "
        f"elapsed={elapsed}s\n"
    )
    log_path = _LOGS_DIR / "pipeline.log"
    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(log_line)

    console.print(f"[dim]Log written to {log_path}[/dim]")


if __name__ == "__main__":
    main()
