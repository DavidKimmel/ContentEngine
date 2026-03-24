"""Draft agent — generate full blog post drafts via Claude API."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from pipeline.api import call_claude

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.yaml"


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
{differentiators}

Every post must end with this exact disclaimer as a Markdown blockquote, after the CTA section and before the SOURCES:

> **Medical disclaimer:** This content is for informational purposes only and does not constitute medical advice, diagnosis, or treatment. Always consult a licensed physical therapist or qualified healthcare provider before beginning any exercise or rehabilitation program. If you are experiencing pain or injury, seek professional evaluation promptly.

Do not paraphrase or shorten the disclaimer. Use it verbatim every time."""


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

    return call_claude(system=system, user_message=user_msg, max_tokens=4096)
