"""SEO agent — review and optimize blog post drafts via Claude API."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from pipeline.api import call_claude

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


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

    for attempt in range(2):
        prompt = user_msg
        if attempt == 1:
            prompt += (
                "\n\nIMPORTANT: Your previous response was not valid JSON. "
                "Return ONLY the raw JSON object — no markdown fencing, "
                "no backticks, no explanation text before or after."
            )

        text = call_claude(
            system=_SYSTEM_PROMPT, user_message=prompt, max_tokens=1500
        )

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
