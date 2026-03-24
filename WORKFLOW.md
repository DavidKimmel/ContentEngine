# ContentEngine — Reusable Build Playbook

## What This Builds

ContentEngine is a fully automated content pipeline that scrapes trending topics from Google Trends, PubMed research, and competitor blogs, scores them on a 4-dimension relevance matrix, generates SEO-optimized blog drafts using Claude AI (outline, draft, SEO review), and manages an editorial review and CMS publishing workflow. It was originally built for Resurgent Sports Rehab (a boutique sports physical therapy clinic in Northern Virginia) but is designed to be niche-agnostic — swap the config, tune the prompts, and rebuild for any industry.

## How To Use This Playbook

1. Create a new empty project folder (e.g., `ContentEngine-YourNiche/`)
2. Open Claude Code inside it
3. Fill in every `[BRACKETED PLACEHOLDER]` in the prompts below with your niche-specific details from the Niche Configuration Worksheet
4. Paste each prompt into Claude Code in order, waiting for each to finish before running the next
5. Test after each prompt using the Testing Checklist — do not skip ahead
6. **Prompt 4 may need tuning** — the PubMed queries and scorer relevance thresholds depend on what your specific scrapers actually return. Run `python pipeline/scorer.py` standalone to see the full scoring breakdown and adjust.

## Required API Keys & Accounts

| Service | Required? | Where to Get It |
|---------|-----------|----------------|
| Anthropic API key | **Yes** — powers all content generation | console.anthropic.com > API Keys |
| CMS credentials | Yes — for publishing | WordPress: Users > Application Passwords; Webflow: Site Settings > API Access; Generic: your CMS docs |
| PubMed (NCBI E-utilities) | No key needed | Free public API at eutils.ncbi.nlm.nih.gov |
| Google Trends (pytrends) | No key needed | Free, no account required |
| Competitor sitemaps | No key needed | Public XML sitemaps |

## Niche Configuration Worksheet

Complete this **before** starting. Your answers fill the `[BRACKETED PLACEHOLDERS]` in every prompt below. Resurgent answers shown as examples in parentheses.

```
CLINIC/BUSINESS NAME: _________________ (Resurgent Sports Rehab)
LOCATION: _________________ (Northern Virginia — Fairfax & Chantilly)
BUSINESS MODEL: _________________ (Out-of-network boutique sports PT)
TARGET AUDIENCE: _________________ (Athletes and active adults in NoVA)
TONE: _________________ (Warm, authoritative, empowering — expert clinician talking to a smart patient)

DIFFERENTIATORS (3-5 things that make this business unique):
  1. _________________ (MVI baseball movement analysis framework)
  2. _________________ (3-tier run analysis protocol)
  3. _________________ (ACL prevention program with 52-85% injury reduction outcomes)
  4. _________________ (8 board-certified DPTs — SCS/OCS/ATC/CSCS)
  5. _________________ (1-on-1 sessions only, never PTAs or rotating staff)

PRIMARY KEYWORDS (8-12 search terms your audience actually uses):
  1. _________________ (physical therapy Northern Virginia)
  2. _________________ (sports physical therapy Fairfax VA)
  3. _________________ (ACL rehabilitation Fairfax)
  4. _________________ (running injury physical therapy NoVA)
  5. _________________ (dry needling Northern Virginia)
  6. _________________ (return to sport testing)
  7. _________________ (baseball physical therapy Fairfax)
  8. _________________ (out of network physical therapy)
  9. _________________ (sports rehab Chantilly VA)
  10. _________________ (movement analysis physical therapy)
  11. _________________ (ACL prevention program)
  12. _________________ (Precision Athlete program PT)

CONTENT GAPS (8-10 topics competitors have not covered well):
  1. _________________ (ACL injury prevention and rehabilitation)
  2. _________________ (Running injury diagnosis and treatment)
  3. _________________ (Baseball-specific injury prevention — MVI framework)
  4. _________________ (Return-to-sport testing protocols)
  5. _________________ (Out-of-network PT value explanation)
  6. _________________ (Sports PT vs general PT differences)
  7. _________________ (In-network vs out-of-network PT explainer)
  8. _________________ (Precision Athlete performance program)
  9. _________________ (Dry needling for athletes)
  10. _________________ (Video gait and movement analysis)

COMPETITOR SITEMAP URLS (2-5 direct competitors):
  1. _________________ (https://rehab2perform.com/sitemap.xml)
  2. _________________ (https://thejacksonclinics.com/sitemap.xml)
  3. _________________ (https://www.ace-pt.org/sitemap.xml)

PUBMED SEARCH QUERIES (5 research queries specific to your niche):
  1. _________________ (ACL reconstruction rehabilitation return to sport)
  2. _________________ (running injury physical therapy biomechanics)
  3. _________________ (dry needling sports physical therapy outcomes)
  4. _________________ (anterior cruciate ligament injury prevention program)
  5. _________________ (sports rehabilitation manual therapy outcomes)

PRIORITY PAGES (5-7 high-value pages the site needs):
  1. _________________ (Baseball Physical Therapy & Injury Prevention | Fairfax VA)
  2. _________________ (Running Injury Physical Therapy | Northern Virginia)
  3. _________________ (ACL Injury Prevention & Rehab | Fairfax & Chantilly)
  4. _________________ (What is Return-to-Sport Testing?)
  5. _________________ (Sports PT vs General PT — Why It Matters)
  6. _________________ (In-Network vs Out-of-Network PT — What Athletes Should Know)
  7. _________________ (How to Choose a Sports Physical Therapist in Northern Virginia)

CMS TYPE: _________________ (wordpress | webflow | generic)
MIN SCORE TO GENERATE: _________________ (60)
POSTS PER RUN: _________________ (3)
```

## The Build Prompts

---

### Prompt 1 — Project Scaffold

**What this builds:** The complete folder structure, config files, CLAUDE.md, requirements.txt, and a Click CLI shell with stub commands.

**Paste this into Claude Code:**

~~~text
Initialize a Python project called ContentEngine for an automated [BUSINESS_MODEL] blog content pipeline.

Create this exact folder structure:
ContentEngine/
├── CLAUDE.md
├── .env.example
├── config.yaml
├── run.py
├── requirements.txt
├── scrapers/
│   ├── __init__.py
│   ├── trends.py
│   ├── pubmed.py
│   └── competitors.py
├── pipeline/
│   ├── __init__.py
│   ├── scorer.py
│   ├── outline_agent.py
│   ├── draft_agent.py
│   └── seo_agent.py
├── review/
│   ├── __init__.py
│   └── export.py
├── drafts/
│   └── .gitkeep
└── db/
    ├── __init__.py
    └── queue.py

Then do the following:

1. Write CLAUDE.md with full instructions for this project — commands, rules, tone guidelines for [BUSINESS_MODEL] content, and a note that posts are never auto-published, all output goes to /drafts/ as Markdown files with frontmatter.

2. Write .env.example with placeholder keys for ANTHROPIC_API_KEY and a COMPETITOR_SITEMAPS variable (comma-separated URLs).

3. Write config.yaml with a keywords list (at least 10 [BUSINESS_MODEL] related search terms), a competitor_sitemaps list (leave as empty array for now), and a settings block with max_results_per_source: 20 and output_dir: drafts.

4. Write requirements.txt with: anthropic, pytrends, newspaper3k, feedparser, requests, pyyaml, python-dotenv, rich, click.

5. Write run.py as a Click CLI with four subcommands as stubs: scrape, score, generate, review. Each should print a "Running [command]..." message for now.

Do not write any scraper or pipeline logic yet. Just the scaffold, config files, and CLI shell.
~~~

---

### Prompt 2 — Build the Scrapers

**What this builds:** Three independent scrapers (Google Trends, PubMed, competitors) and an aggregator function, plus wires the scrape CLI command.

**Paste this into Claude Code:**

~~~text
Now build out the three scrapers in ContentEngine/scrapers/.
Each scraper should work independently and return a standardized list of topic dictionaries.

The standard topic dict format for all scrapers is:
{
  "title": str,
  "source": str,        # "google_trends" | "pubmed" | "competitor"
  "url": str,
  "date": str,          # ISO format where available, empty string if not
  "score": float,       # raw signal strength 0.0-100.0
  "summary": str,       # 1-2 sentence description, empty string if not available
  "doi": str            # DOI string if from PubMed, empty string otherwise
}

--- scrapers/trends.py ---
Use the pytrends library. Load keywords from config.yaml (pt_keywords list).
For each keyword fetch related rising queries from the past 7 days, US only.
Cap at 5 rising queries per keyword.
Return a deduplicated list of topic dicts with source="google_trends".
Add a __main__ block that prints results as a formatted table using the rich library.

--- scrapers/pubmed.py ---
Use the NCBI E-utilities REST API (no API key required).
Run three searches against the keywords from config.yaml, picking 3 representative ones automatically.
Fetch the 20 most recent results per search, sorted by publication date.
Deduplicate by DOI.
Return topic dicts with source="pubmed". Populate doi field where available.
Summary should be the article title cleaned up — do not fetch abstracts.
Add a __main__ block that prints results as a formatted table using rich.

--- scrapers/competitors.py ---
Load competitor sitemap URLs from config.yaml (competitor_sitemaps list).
If the list is empty, print a warning using rich and return an empty list.
For each sitemap URL:
  - Fetch and parse the XML
  - Extract all <loc> URLs
  - Filter to URLs that look like blog posts (contain /blog/, /post/, /article/, or /news/ in the path)
  - For each URL fetch the page title and first 300 chars of body text using newspaper3k
  - Cap at 15 articles per sitemap
Return topic dicts with source="competitor".
Add a __main__ block that prints results as a formatted table using rich.
Wrap all network calls in try/except and skip failed URLs gracefully.

--- scrapers/__init__.py ---
Export a single function run_all_scrapers() that calls all three scrapers, combines results, prints a summary using rich (X from trends, X from pubmed, X from competitors), and returns the combined list.

--- run.py ---
Update the scrape subcommand to call run_all_scrapers() and print the total topics found. Save raw results to db/raw_topics.json (overwrite each run).

Do not touch any other files.
~~~

---

### Prompt 3 — Update Config + Build Scorer

**What this builds:** The full niche-specific config.yaml and the 4-dimension topic scorer.

**Paste this into Claude Code:**

~~~text
Do two things:

--- PART 1: Replace config.yaml entirely ---

Write this exact content to config.yaml:

clinic:
  name: [BUSINESS_NAME]
  location: [LOCATION]
  model: [BUSINESS_MODEL]
  differentiators:
    - [DIFFERENTIATOR_1]
    - [DIFFERENTIATOR_2]
    - [DIFFERENTIATOR_3]
    - [DIFFERENTIATOR_4]
    - [DIFFERENTIATOR_5]
  target_audience: [TARGET_AUDIENCE]
  tone: [TONE]

pt_keywords:
  - [KEYWORD_1]
  - [KEYWORD_2]
  - [KEYWORD_3]
  - [KEYWORD_4]
  - [KEYWORD_5]
  - [KEYWORD_6]
  - [KEYWORD_7]
  - [KEYWORD_8]
  - [KEYWORD_9]
  - [KEYWORD_10]
  - [KEYWORD_11]
  - [KEYWORD_12]

competitor_sitemaps:
  - [COMPETITOR_SITEMAP_1]
  - [COMPETITOR_SITEMAP_2]
  - [COMPETITOR_SITEMAP_3]

content_gaps:
  - [CONTENT_GAP_1]
  - [CONTENT_GAP_2]
  - [CONTENT_GAP_3]
  - [CONTENT_GAP_4]
  - [CONTENT_GAP_5]
  - [CONTENT_GAP_6]
  - [CONTENT_GAP_7]
  - [CONTENT_GAP_8]
  - [CONTENT_GAP_9]
  - [CONTENT_GAP_10]

priority_pages:
  - [PRIORITY_PAGE_1]
  - [PRIORITY_PAGE_2]
  - [PRIORITY_PAGE_3]
  - [PRIORITY_PAGE_4]
  - [PRIORITY_PAGE_5]
  - [PRIORITY_PAGE_6]
  - [PRIORITY_PAGE_7]

settings:
  max_results_per_source: 20
  output_dir: drafts
  min_score_to_generate: [MIN_SCORE]
  posts_per_run: [POSTS_PER_RUN]

--- PART 2: Write pipeline/scorer.py ---

This module takes the raw list of topic dicts from db/raw_topics.json and scores, deduplicates, and prioritizes them into a ranked queue.

Write a score_topics(topics: list) function that:
1. Loads config.yaml to access content_gaps, differentiators, and pt_keywords
2. Scores each topic on four dimensions (0-25 each, max 100):
   a. RELEVANCE (0-25): Title matches keywords/gaps? Exact=25, partial=15, none=5.
   b. SOURCE AUTHORITY (0-25): pubmed=25, competitor=20, google_trends=15
   c. RECENCY (0-25): 30 days=25, 90 days=18, 180 days=10, older=5
   d. OPPORTUNITY (0-25): Title covers a content_gap? Match=25, none=0.
3. Adds total_score field
4. Deduplicates by >70% word overlap, keeps higher score
5. Filters below min_score_to_generate
6. Returns sorted by total_score descending

Also write save_queue(topics) to save to db/scored_queue.json with timestamp.

Add __main__ block: load raw_topics.json, score, print top 10 as rich table, save queue.

Update run.py score subcommand to call both functions.

Do not touch any other files.
~~~

---

### Prompt 4 — Fix PubMed Queries + Scorer Relevance

**What this builds:** Niche-specific PubMed queries and a tighter opportunity scoring function that prevents false positives.

**Paste this into Claude Code:**

~~~text
Fix two issues before we build the generation layer.

--- FIX 1: scrapers/pubmed.py ---

Replace the automatic keyword selection logic with these five hardcoded PubMed search queries specifically designed to return [BUSINESS_MODEL] research:

queries = [
    "[PUBMED_QUERY_1]",
    "[PUBMED_QUERY_2]",
    "[PUBMED_QUERY_3]",
    "[PUBMED_QUERY_4]",
    "[PUBMED_QUERY_5]"
]

Run each query separately, fetch 10 results each (50 total before dedup), sorted by publication date descending. Keep all existing dedup and formatting logic unchanged.

--- FIX 2: pipeline/scorer.py ---

The opportunity_score dimension is incorrectly awarding 25 points to completely unrelated articles. Fix the opportunity scoring logic:

Instead of a simple keyword presence check, require that BOTH of these are true to award 25 points:
  - The title matches a content_gap keyword
  - The title also contains at least one word from this niche-specific domain word list: [LIST 15-20 WORDS CENTRAL TO YOUR NICHE]

If only the content_gap matches but none of the domain words match, award 10 instead of 25. If neither matches, award 0.

After making both fixes run the full pipeline:
  python run.py scrape
  python run.py score

Print the top 5 scored topics as a rich table to verify results are niche-specific.
~~~

---

### Prompt 5 — Build Generation Pipeline

**What this builds:** Three Claude agents (outline, draft, SEO), the pipeline orchestrator, export module, and the generate CLI command.

**Paste this into Claude Code:**

~~~text
Build the full three-agent content generation pipeline for [BUSINESS_NAME]. All three agents call the Anthropic API using the model claude-sonnet-4-20250514.

Load ANTHROPIC_API_KEY from .env using python-dotenv.
Load clinic context from config.yaml at the top of each agent.

--- pipeline/outline_agent.py ---
Write generate_outline(topic: dict) -> dict
System prompt: business name, location, differentiators, target audience from config. One primary keyword with 3-5 variants. Featured snippet structure. Audience is [TARGET_AUDIENCE] not academics. Angles highlighting proprietary frameworks. Return valid JSON only.
User prompt: topic title, URL, DOI. Returns JSON: title, slug, meta_description, primary_keyword, secondary_keywords, estimated_word_count, featured_snippet_target, h2_sections, cta_section, internal_link_opportunities, resurgent_angle.
Retry once on JSON parse failure.

--- pipeline/draft_agent.py ---
Write generate_draft(topic: dict, outline: dict) -> str
System prompt: Claude writes as [PROFESSIONAL_ROLE] on [BUSINESS_NAME] team in [LOCATION]. [TONE] voice. Plain language. No "in conclusion". Inline citations [Author, Year]. No H1. Closing section with 3-bullet checklist and soft CTA. Natural differentiator mentions. H2/H3 Markdown only.
Returns raw markdown.

--- pipeline/seo_agent.py ---
Write optimize_seo(draft: str, outline: dict) -> dict
SEO specialist review. Returns JSON: seo_score, primary_keyword_density, issues, suggestions, schema_type, optimized_meta_description, optimized_title, internal_links_to_add, estimated_read_time.
Retry once on parse failure.

--- review/export.py ---
Write export_draft(topic, outline, draft, seo) -> str
YAML frontmatter + <!-- SEO NOTES --> + draft + SOURCES. Writes to drafts/{slug}.md.

--- pipeline/__init__.py ---
run_pipeline(topic): all four steps, progress output, returns filepath or None.

--- run.py ---
Update generate: no flags=top 1, --auto=top 3, --topic-id N=specific. Marks as "generated" in scored_queue.json.

Do not touch any other files.
~~~

---

### Prompt 6 — Fix Competitor Scrapers + Review Workflow

**What this builds:** Resilient competitor scraping and the full review/approve/revise workflow.

**Paste this into Claude Code:**

~~~text
Fix two things and build one new feature.

--- FIX 1: scrapers/competitors.py ---
Add browser-like User-Agent headers to all requests.get() calls.
Replace ElementTree with resilient parser: try lxml recover=True, fall back to ElementTree.
For sitemaps returning 0 blog URLs, scrape /blog, /resources, /news fallback pages for links. Cap at 15 per sitemap.

--- FIX 2: requirements.txt ---
Add lxml and lxml_html_clean.

--- NEW: review/export.py ---
Add list_drafts(): scan drafts/*.md, read YAML frontmatter, return summary dicts.
Add mark_approved(slug): update status APPROVED in .md and scored_queue.json.
Add mark_revision(slug, notes): update status NEEDS_REVISION, insert revision notes comment.

Update run.py review: no flags=list table, --approve [slug], --revise [slug] --notes "...".

Do not touch any other files.
~~~

---

### Prompt 7 — CMS Publisher + Scheduler + README

**What this builds:** The publish module, weekly scheduler, and complete README.

**Paste this into Claude Code:**

~~~text
Build the final three pieces to complete the ContentEngine.

--- review/publish.py ---
publish_draft(slug) -> bool: check APPROVED status, route by CMS_TYPE in .env.
publish_wordpress: POST WP REST API as draft. publish_webflow: POST Webflow CMS v2 isDraft=true. publish_generic: POST JSON to endpoint.
On success: status=PUBLISHED, add published_date. On failure: print error, no status change.
Update .env.example with all CMS vars.

Update run.py publish: --slug, --approve-and-publish, --all (3s pause).

--- schedule.py ---
Weekly runner: scrape + score + generate top 3. Catch per-step exceptions. Summary + logs/pipeline.log.

--- README.md ---
Overview, setup, weekly workflow, CLI reference, adding competitors, adjusting settings, CMS setup (3 types), troubleshooting.

Do not touch any other files.
~~~

---

### Prompt 8 — Generate the Playbook

**What this builds:** This WORKFLOW.md playbook and the standalone NICHE_WORKSHEET.md.

~~~text
Create WORKFLOW.md in the project root — a reusable master playbook documenting the exact methodology used to build this ContentEngine, written so I can hand it to Claude Code in any new folder and rebuild the entire system for a completely different niche from scratch.

Also create NICHE_WORKSHEET.md as a standalone fill-in-the-blank document for the niche configuration.
~~~

### Prompt 9 — Production Hardening

**What this builds:** Six production improvements: topic diversity cap, duplicate detection, medical disclaimer, API retry with backoff, token cost logging, and a draft preview command.

**Paste this into Claude Code:**

~~~text
Add six production-hardening improvements to ContentEngine:

1. Topic diversity cap — modify pipeline/scorer.py to group topics by condition category (ACL, running, shoulder, knee, dry needling, back, return to sport, general) and cap at 2 per category. Add a "category" field to each topic dict and print a diversity summary.

2. Duplicate detection — create db/published_history.py with load_history(), is_duplicate() (>60% title word overlap OR exact primary_keyword match), and add_to_history(). Wire into scorer to filter before scoring, and into pipeline to record after generation.

3. Medical disclaimer — add to draft_agent.py system prompt requiring this exact blockquote at the end of every post: "Medical disclaimer: This content is for informational purposes only..."

4. API retry with backoff — create pipeline/api.py with a shared call_claude() function wrapping all three agents. Retry up to 3 times on RateLimitError (5s base), APITimeoutError (3s base), and APIError (2s base) with exponential backoff.

5. Token cost logging — track input/output tokens per agent call, print per-agent breakdown after each generation, log to pipeline.log with slug and cost. Update schedule.py to sum total API cost across the run.

6. Preview command — add `python run.py preview --slug [slug]` that renders a draft to HTML at drafts/preview/[slug].html with status badge (color-coded), metadata bar, full post, and SEO notes as a visible yellow "Editor Notes" panel. Opens in browser.

Run syntax checks on all modified files.
~~~

---

## Testing Checklist

Run these in order after completing all prompts:

- [ ] `python scrapers/pubmed.py` — verify niche-specific research articles
- [ ] `python scrapers/trends.py` — verify trending queries (may be 0 for hyper-local niches)
- [ ] `python scrapers/competitors.py` — verify competitor blog posts scraped
- [ ] `python run.py scrape` — full scrape, check total count
- [ ] `python run.py score` — verify topics pass the minimum score threshold
- [ ] `python run.py generate` — generate one draft, verify output in drafts/
- [ ] `python run.py review` — list drafts, verify status table
- [ ] `python run.py review --approve [slug]` — approve a draft, verify status change
- [ ] `python run.py publish --slug [slug]` — publish to CMS (requires CMS credentials)
- [ ] `python schedule.py` — full weekly pipeline, verify logs/pipeline.log

## Weekly Operating Rhythm

| Day | Action | Command | Time |
|-----|--------|---------|------|
| **Monday** | Run the full automated pipeline | `python schedule.py` | ~5 min |
| **Tue-Wed** | Editors review `drafts/` folder, edit .md files, check `<!-- SEO NOTES -->` checklist | Manual | Variable |
| **Thursday** | Approve each reviewed post | `python run.py review --approve [slug]` | ~2 min |
| **Friday** | Push approved posts to CMS as drafts | `python run.py publish --all` | ~1 min |

Posts land in the CMS as **drafts** — the editor does final publish in the CMS dashboard. ContentEngine never auto-publishes.

## Adapting For a New Niche

### Always Changes

- **config.yaml** — complete replacement via Prompt 3 (business profile, keywords, gaps, competitors)
- **PubMed search queries** — hardcoded in `scrapers/pubmed.py` via Prompt 4
- **Claude system prompts** — tone, voice, professional role, differentiators (Prompt 5)
- **Competitor sitemap URLs** — in config.yaml
- **Opportunity scorer domain words** — the domain word list in `pipeline/scorer.py` (Prompt 4)

### Stays the Same

- All folder structure and file names
- The entire scoring architecture (4 dimensions, dedup, threshold filtering)
- The three-agent generation pattern (outline > draft > SEO)
- The review and publish workflow (PENDING_REVIEW > APPROVED > PUBLISHED)
- `schedule.py` and `run.py` CLI structure
- The export format (YAML frontmatter + SEO notes + Markdown + sources)

### Niche-Specific Tips

- **For e-commerce niches:** Add a `scrapers/amazon.py` using the Product Advertising API for trending product searches. Weight competitor scraping higher since product blogs are the primary content source.
- **For local service businesses:** Add Google My Business category as a keyword modifier on all PubMed/Trends queries (e.g., "plumber" + "water heater repair" + "[city]").
- **For B2B / tech niches:** Replace PubMed with arXiv or Semantic Scholar API — same E-utilities REST pattern, different endpoint. Add a `scrapers/arxiv.py` alongside PubMed.
- **For news-driven niches:** Increase Google Trends timeframe from `now 7-d` to `today 1-m` and lower `min_score_to_generate` to 45. Trends will be your primary source instead of PubMed.
- **For highly local niches:** Google Trends will almost always return 0 results for hyper-local terms — this is expected. Weight PubMed and competitor scraping higher by adjusting authority scores in `pipeline/scorer.py` (e.g., competitor=25, pubmed=20, trends=10).
- **For niches without research (e.g., restaurants, retail):** Remove PubMed entirely and add a `scrapers/news.py` using Google News RSS feeds or a news API. Adjust the draft agent to cite news sources instead of academic papers.

## Troubleshooting

### PubMed returning irrelevant results

The PubMed queries are hardcoded in `scrapers/pubmed.py` in the `_QUERIES` list. Edit them to match your current content focus. Each query should be specific (e.g., "ACL reconstruction rehabilitation return to sport" not just "physical therapy").

### Competitor sitemap 403 errors

Some sites block automated requests. The scraper uses browser-like headers, but some sites may still reject requests. Try:
- Checking if the site has a `robots.txt` that blocks the sitemap
- Using a different sitemap URL (some sites have `/post-sitemap.xml` or `/blog-sitemap.xml`)
- The scraper automatically falls back to scraping HTML index pages for sites where the sitemap yields 0 blog URLs

### Claude API rate limits

If you hit rate limits during `--auto` generation (3 posts = 9 API calls):
- Wait a few minutes and re-run — the pipeline skips already-generated topics
- Reduce `posts_per_run` in `config.yaml` to 1 or 2
- Check your Anthropic usage tier at console.anthropic.com

### Drafts scoring too low and not generating

If `python run.py score` shows 0 topics making the cut:
- Lower `min_score_to_generate` in `config.yaml` (try 45-50)
- Run `python pipeline/scorer.py` standalone to see the full scoring breakdown
- Add more specific terms to `content_gaps` that match your PubMed results
- Check that `pt_keywords` reflect your actual target topics

### How to reset the pipeline

Delete the runtime state files and re-run from scratch:

```bash
rm db/raw_topics.json db/scored_queue.json
python run.py scrape
python run.py score
```

This gives you a fresh topic queue without affecting any existing drafts in `drafts/`.

### How to regenerate a specific draft

Use the `--topic-id` flag to target a specific topic by its index in the scored queue:

```bash
python run.py generate --topic-id 5
```

Run `python pipeline/scorer.py` standalone to see all topic indices and their scores.
