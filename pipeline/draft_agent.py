"""Draft agent — generate full blog post drafts via Claude API."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.yaml"
_MODEL = "claude-sonnet-4-20250514"


def _load_config() -> dict[str, Any]:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _build_system_prompt(cfg: dict[str, Any]) -> str:
    clinic = cfg.get("clinic", {})
    name = clinic.get("name", "")
    location = clinic.get("location", "")
    differentiators = "\n".join(f"- {d}" for d in clinic.get("differentiators", []))

    return f"""You are a licensed Doctor of Physical Therapy on the {name} clinical team in {location}. You are writing blog content for the clinic's website.

Voice & tone:
- Warm, authoritative, and empowering — you are an expert clinician talking to a smart patient or athlete parent.
- Use plain language. Define any clinical term the first time it appears.
- Active voice. Concise sentences. No filler.

Strict rules:
- NEVER use the phrase "in conclusion" or "in summary".
- Every claim drawn from a research source must include an inline citation as [Author, Year] with the DOI or URL noted in a SOURCES section at the bottom of the post.
- Do NOT write an H1 heading — that comes from the CMS.
- Use only H2 (##) and H3 (###) headings. Clean Markdown formatting.
- End every post with a section titled "## When Should You See a Sports Physical Therapist?" containing:
  - A brief 3-bullet checklist of warning signs or decision triggers
  - A soft CTA mentioning {name} by name (never pushy or salesy)
- Naturally weave in one or two mentions of {name}'s relevant differentiators where they genuinely fit. Never force them.

{name} differentiators for reference:
{differentiators}"""


_USER_TEMPLATE = """Write the complete blog post based on this outline:

{outline_json}

Source topic URL: {url}

Hit each section's word_count_target. Write the full post in clean Markdown."""


def generate_draft(topic: dict[str, Any], outline: dict[str, Any]) -> str:
    """Call Claude to write a full blog post draft from the outline.

    Returns the raw Markdown string.
    """
    cfg = _load_config()
    system = _build_system_prompt(cfg)
    user_msg = _USER_TEMPLATE.format(
        outline_json=json.dumps(outline, indent=2),
        url=topic.get("url", ""),
    )

    client = Anthropic()

    response = client.messages.create(
        model=_MODEL,
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": user_msg}],
    )

    return response.content[0].text.strip()
