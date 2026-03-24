# ContentEngine

Automated blog content pipeline for a physical therapy practice.

## Project Overview

ContentEngine scrapes trending PT topics, scores them for relevance, generates SEO-optimized blog drafts using Claude, and exports review-ready Markdown files. **Posts are never auto-published.** All output goes to `/drafts/` as Markdown files with YAML frontmatter.

## Commands

```bash
# Activate virtualenv first
source .venv/Scripts/activate   # Windows
source .venv/bin/activate       # macOS/Linux

# CLI entrypoint
python run.py scrape      # Pull trends, PubMed abstracts, competitor posts
python run.py score       # Rank scraped topics by relevance and gap opportunity
python run.py generate    # Create outlines and drafts via Claude agents
python run.py review      # Export final drafts to /drafts/ with frontmatter
```

## Architecture

```
scrapers/       → Data collection (Google Trends, PubMed, competitor sitemaps)
pipeline/       → Scoring, outline generation, draft writing, SEO optimization
review/         → Human review queue and Markdown export
db/             → Local topic queue (SQLite-backed)
drafts/         → Output directory (Markdown with YAML frontmatter)
```

## Rules

- **Never auto-publish.** Every draft requires human review before publishing.
- All generated content is written to `/drafts/` as `.md` files with YAML frontmatter (title, date, author, keywords, status: draft).
- Use `config.yaml` for all configuration; never hardcode API keys or keywords.
- API keys live in `.env` (never committed). Copy `.env.example` to `.env` and fill in values.
- Keep scraper, pipeline, and review modules decoupled. Each stage reads from and writes to the topic queue in `db/`.
- Use type hints on all function signatures.
- Follow PEP 8. Imports grouped: stdlib / third-party / local.

## Tone Guidelines for PT Content

- **Authoritative but approachable.** Write like a licensed PT explaining something to a motivated patient.
- Use clinical terminology where appropriate, but always follow it with a plain-language explanation.
- Avoid hype, clickbait, and unsubstantiated claims. Cite PubMed sources when available.
- Prefer active voice. Keep sentences concise.
- Target audience: adults seeking physical therapy information — patients, caregivers, and fitness-minded readers.
- Every post should have a clear takeaway or actionable recommendation.

## Environment Setup

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env
# Fill in ANTHROPIC_API_KEY and COMPETITOR_SITEMAPS in .env
```

## Dependencies

See `requirements.txt`. Key libraries:
- `anthropic` — Claude API for content generation
- `pytrends` — Google Trends scraping
- `newspaper3k` — Article extraction from competitor sites
- `feedparser` — RSS/sitemap parsing
- `click` — CLI framework
- `rich` — Terminal output formatting
