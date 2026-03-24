"""Outline agent — generate structured blog post outlines via Claude API."""

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
    audience = clinic.get("target_audience", "")

    return f"""You are a content strategist for {name}, a boutique sports physical therapy clinic in {location}.

Clinic differentiators:
{differentiators}

Target audience: {audience}

When creating blog post outlines, follow these rules:

1. Target ONE primary keyword per post with 3-5 semantic variants as secondary keywords.
2. Structure for featured snippet capture where possible — use FAQ sections, how-to steps, or comparison tables.
3. The audience is Northern Virginia athletes and active adults, NOT academics. Write for smart patients, not researchers.
4. Look for angles that highlight Resurgent's proprietary frameworks where relevant:
   - MVI baseball movement analysis framework
   - 3-tier run analysis protocol
   - ACL prevention protocol with 52-85% injury reduction outcomes
5. Return VALID JSON ONLY. No markdown fencing, no preamble, no explanation — just the raw JSON object."""


_USER_TEMPLATE = """Create a detailed blog post outline for the following topic.

Topic title: {title}
Source URL: {url}
DOI: {doi}

Return a JSON object with this exact structure:
{{
  "title": "SEO-optimized post title",
  "slug": "url-slug",
  "meta_description": "under 160 chars",
  "primary_keyword": "main target keyword",
  "secondary_keywords": ["kw1", "kw2", "kw3"],
  "estimated_word_count": 1200,
  "featured_snippet_target": "faq|howto|table|paragraph",
  "h2_sections": [
    {{
      "heading": "Section heading",
      "intent": "what this section accomplishes",
      "word_count_target": 200,
      "include_cta": false
    }}
  ],
  "cta_section": "brief description of closing CTA",
  "internal_link_opportunities": ["page1", "page2"],
  "resurgent_angle": "how this post connects to Resurgent's specific differentiators"
}}"""


def generate_outline(topic: dict[str, Any]) -> dict[str, Any]:
    """Call Claude to generate a structured blog post outline.

    Returns the parsed JSON outline dict. Retries once on parse failure.
    """
    cfg = _load_config()
    system = _build_system_prompt(cfg)
    user_msg = _USER_TEMPLATE.format(
        title=topic.get("title", ""),
        url=topic.get("url", ""),
        doi=topic.get("doi", ""),
    )

    for attempt in range(2):
        prompt = user_msg
        if attempt == 1:
            prompt += (
                "\n\nIMPORTANT: Your previous response was not valid JSON. "
                "Return ONLY the raw JSON object — no markdown fencing, "
                "no backticks, no explanation text before or after."
            )

        text = call_claude(system=system, user_message=prompt, max_tokens=2000)

        # Strip markdown fencing if present despite instructions
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[: -3].rstrip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            if attempt == 0:
                continue
            raise ValueError(f"Failed to parse outline JSON after retry: {text[:200]}")
