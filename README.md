# ContentEngine

Automated blog content pipeline for **Resurgent Sports Rehab**, a boutique sports physical therapy clinic in Northern Virginia (Fairfax & Chantilly).

ContentEngine scrapes trending PT topics from Google Trends, PubMed research, and competitor blogs, scores them for relevance to Resurgent's content strategy, generates SEO-optimized blog drafts using Claude AI, and exports review-ready Markdown files. An editor reviews every draft before anything is published — posts are **never auto-published**.

## Setup

```bash
# 1. Clone or create the project
cd ContentEngine

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/Scripts/activate   # Windows
source .venv/bin/activate       # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit .env and fill in:
#   ANTHROPIC_API_KEY  — from console.anthropic.com
#   CMS_TYPE           — wordpress, webflow, or generic
#   CMS credentials    — see "CMS Setup" section below

# 5. Review config.yaml
# - pt_keywords are pre-configured for Resurgent
# - competitor_sitemaps has three competitors pre-loaded
# - Adjust settings as needed (see "Adjusting Content Settings")

# 6. Test the pipeline
python run.py scrape
```

## Weekly Workflow

The intended human process for a content team:

| Day | Action | Command |
|-----|--------|---------|
| **Monday** | Run the full pipeline automatically | `python schedule.py` |
| **Tue-Wed** | Editors open `drafts/` folder, review `.md` files, edit directly in any text editor. Check the `<!-- SEO NOTES -->` block for optimization checklist. | Manual review |
| **Thursday** | Approve each reviewed post | `python run.py review --approve [slug]` |
| **Friday** | Push approved posts to CMS as drafts | `python run.py publish --all` |

The `schedule.py` script runs scrape, score, and generate in sequence and logs results to `logs/pipeline.log`.

## CLI Commands

| Command | Flags | Description |
|---------|-------|-------------|
| `python run.py scrape` | | Scrape Google Trends, PubMed, and competitor blogs. Saves to `db/raw_topics.json`. |
| `python run.py score` | | Score and rank scraped topics. Saves to `db/scored_queue.json`. |
| `python run.py generate` | | Generate a draft for the top ungenerated topic. |
| | `--auto` | Generate drafts for the top 3 ungenerated topics. |
| | `--topic-id N` | Generate a draft for a specific topic by queue index. |
| `python run.py review` | | List all drafts with status, SEO score, and read time. |
| | `--approve [slug]` | Mark a draft as APPROVED. |
| | `--revise [slug] --notes "..."` | Mark a draft as NEEDS_REVISION with editor notes. |
| `python run.py publish` | `--slug [slug]` | Publish a specific APPROVED draft to CMS. |
| | `--approve-and-publish [slug]` | Approve then immediately publish a draft. |
| | `--all` | Publish all APPROVED drafts (3s pause between each). |
| `python schedule.py` | | Run the full weekly pipeline (scrape + score + generate top 3). |

## Adding Competitor Sites

Edit `config.yaml` and add sitemap URLs to the `competitor_sitemaps` list:

```yaml
competitor_sitemaps:
  - https://rehab2perform.com/sitemap.xml
  - https://thejacksonclinics.com/sitemap.xml
  - https://www.ace-pt.org/sitemap.xml
  - https://newcompetitor.com/sitemap.xml    # add new ones here
```

The scraper filters sitemap URLs for blog-like paths (`/blog/`, `/post/`, `/article/`, `/news/`, `/resources/`). For sites where the sitemap doesn't contain blog paths (like Rehab2Perform), the scraper automatically falls back to scraping their `/blog` and `/resources` index pages for article links.

## Adjusting Content Settings

All content tuning is in `config.yaml` under the `settings` block:

```yaml
settings:
  max_results_per_source: 20       # results fetched per scraper source
  output_dir: drafts               # where generated .md files land
  min_score_to_generate: 60.0      # minimum score (0-100) to queue for generation
  posts_per_run: 3                 # max posts generated per --auto run
```

- **Lowering `min_score_to_generate`** (e.g., to 40) lets more topics through for generation but may include less relevant ones.
- **Raising it** (e.g., to 75) produces fewer but more targeted posts.
- **`pt_keywords`** drive both scraping and scoring. Add keywords to match your current content strategy focus.
- **`content_gaps`** are topics you want to cover but haven't yet. Topics matching a gap score higher.

## CMS Setup

### WordPress

1. In your WordPress admin, go to **Users > Profile > Application Passwords**.
2. Create a new application password (name it "ContentEngine").
3. Set these in `.env`:
   ```
   CMS_TYPE=wordpress
   WP_URL=https://yoursite.com
   WP_USER=your_username
   WP_APP_PASSWORD=xxxx xxxx xxxx xxxx xxxx xxxx
   ```
4. Posts are pushed as **drafts** — final publish happens in the WordPress dashboard.

### Webflow

1. Go to **Webflow Dashboard > Site Settings > Apps & Integrations > API Access**.
2. Generate an API token.
3. Find your blog collection ID in the CMS panel URL.
4. Set these in `.env`:
   ```
   CMS_TYPE=webflow
   WEBFLOW_API_KEY=your_api_token
   WEBFLOW_COLLECTION_ID=your_collection_id
   ```
5. Items are pushed as **drafts** (`isDraft: true`).

### Generic CMS

For any CMS with a REST API:

1. Set these in `.env`:
   ```
   CMS_TYPE=generic
   GENERIC_CMS_URL=https://your-cms.com/api/posts
   GENERIC_CMS_KEY=your_bearer_token
   ```
2. ContentEngine sends a JSON POST with fields: `title`, `slug`, `body`, `meta_description`, `tags`, `status`.

## Troubleshooting

### PubMed returning irrelevant results

The PubMed queries are hardcoded in `scrapers/pubmed.py` in the `_QUERIES` list. Edit them to match your current content focus. Each query should be specific (e.g., "ACL reconstruction rehabilitation return to sport" not just "physical therapy").

### Competitor sitemap 403 errors

Some sites block automated requests. The scraper uses browser-like headers, but some sites may still reject requests. Try:
- Checking if the site has a `robots.txt` that blocks the sitemap
- Using a different sitemap URL (some sites have `/post-sitemap.xml` or `/blog-sitemap.xml`)
- The scraper automatically falls back to scraping HTML index pages for Rehab2Perform-style sites

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
