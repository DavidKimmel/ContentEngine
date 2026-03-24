"""SEO agent — review and optimize blog post drafts via Claude API."""

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


_SYSTEM_PROMPT = """You are an SEO specialist reviewing a physical therapy blog post for a boutique sports PT clinic in Northern Virginia (Resurgent Sports Rehab).

Analyze the draft against the provided outline and return a JSON evaluation.

Return VALID JSON ONLY. No markdown fencing, no preamble, no explanation — just the raw JSON object."""


_USER_TEMPLATE = """Review this blog post draft for SEO quality.

OUTLINE:
{outline_json}

DRAFT:
{draft}

Return a JSON object with this exact structure:
{{
  "seo_score": 0-100,
  "primary_keyword_density": "X%",
  "issues": ["issue1", "issue2"],
  "suggestions": ["suggestion1", "suggestion2"],
  "schema_type": "Article|FAQPage|HowTo",
  "optimized_meta_description": "final meta under 160 chars",
  "optimized_title": "final SEO title under 60 chars",
  "internal_links_to_add": ["page1", "page2"],
  "estimated_read_time": "X min read"
}}"""


def optimize_seo(draft: str, outline: dict[str, Any]) -> dict[str, Any]:
    """Call Claude to perform SEO analysis on a blog draft.

    Returns the parsed JSON evaluation dict. Retries once on parse failure.
    """
    user_msg = _USER_TEMPLATE.format(
        outline_json=json.dumps(outline, indent=2),
        draft=draft,
    )

    client = Anthropic()

    for attempt in range(2):
        prompt = user_msg
        if attempt == 1:
            prompt += (
                "\n\nIMPORTANT: Your previous response was not valid JSON. "
                "Return ONLY the raw JSON object — no markdown fencing, "
                "no backticks, no explanation text before or after."
            )

        response = client.messages.create(
            model=_MODEL,
            max_tokens=1500,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.content[0].text.strip()

        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[: -3].rstrip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            if attempt == 0:
                continue
            raise ValueError(f"Failed to parse SEO JSON after retry: {text[:200]}")
