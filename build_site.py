"""Build a static GitHub Pages blog site from ContentEngine drafts."""

from __future__ import annotations

import re
import shutil
from datetime import date
from pathlib import Path
from typing import Any

import markdown
import yaml

_ROOT = Path(__file__).resolve().parent
_DRAFTS_DIR = _ROOT / "drafts"
_DOCS_DIR = _ROOT / "docs"
_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)", re.DOTALL)

# ---------------------------------------------------------------------------
# HTML Templates
# ---------------------------------------------------------------------------

_BASE_CSS = """
:root {
  --primary: #1a5632;
  --primary-light: #2a7a4a;
  --accent: #c8a951;
  --bg: #fafaf7;
  --card-bg: #ffffff;
  --text: #2d2d2d;
  --text-light: #6b6b6b;
  --border: #e8e5de;
  --shadow: 0 2px 12px rgba(0,0,0,0.06);
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: 'Georgia', 'Times New Roman', serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.7;
}

.site-header {
  background: var(--primary);
  color: white;
  padding: 0;
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}

.header-inner {
  max-width: 1100px;
  margin: 0 auto;
  padding: 1.2rem 2rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.logo {
  font-family: 'Helvetica Neue', Arial, sans-serif;
  font-size: 1.6rem;
  font-weight: 700;
  color: white;
  text-decoration: none;
  letter-spacing: -0.5px;
}

.logo span { color: var(--accent); }

nav a {
  color: rgba(255,255,255,0.85);
  text-decoration: none;
  margin-left: 2rem;
  font-family: 'Helvetica Neue', Arial, sans-serif;
  font-size: 0.9rem;
  font-weight: 500;
  letter-spacing: 0.3px;
  transition: color 0.2s;
}

nav a:hover { color: var(--accent); }

.hero {
  background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
  color: white;
  padding: 5rem 2rem;
  text-align: center;
}

.hero h1 {
  font-family: 'Helvetica Neue', Arial, sans-serif;
  font-size: 2.8rem;
  font-weight: 700;
  margin-bottom: 1rem;
  letter-spacing: -1px;
}

.hero p {
  font-size: 1.15rem;
  opacity: 0.9;
  max-width: 650px;
  margin: 0 auto;
  line-height: 1.8;
}

.hero .badge {
  display: inline-block;
  background: var(--accent);
  color: var(--primary);
  padding: 0.4rem 1.2rem;
  border-radius: 20px;
  font-family: 'Helvetica Neue', Arial, sans-serif;
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.5px;
  margin-bottom: 1.5rem;
  text-transform: uppercase;
}

.container {
  max-width: 1100px;
  margin: 0 auto;
  padding: 3rem 2rem;
}

.section-title {
  font-family: 'Helvetica Neue', Arial, sans-serif;
  font-size: 1.1rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1.5px;
  color: var(--primary);
  margin-bottom: 2rem;
  padding-bottom: 0.8rem;
  border-bottom: 2px solid var(--accent);
}

.posts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 2rem;
}

.post-card {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
  box-shadow: var(--shadow);
  transition: transform 0.2s, box-shadow 0.2s;
}

.post-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 6px 24px rgba(0,0,0,0.1);
}

.card-accent {
  height: 4px;
  background: linear-gradient(90deg, var(--primary), var(--accent));
}

.card-body {
  padding: 1.8rem;
}

.card-meta {
  font-family: 'Helvetica Neue', Arial, sans-serif;
  font-size: 0.78rem;
  color: var(--text-light);
  margin-bottom: 0.8rem;
  display: flex;
  gap: 1rem;
  align-items: center;
}

.card-meta .tag {
  background: rgba(26,86,50,0.08);
  color: var(--primary);
  padding: 0.2rem 0.6rem;
  border-radius: 4px;
  font-weight: 600;
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.card-body h2 {
  font-family: 'Helvetica Neue', Arial, sans-serif;
  font-size: 1.25rem;
  font-weight: 700;
  line-height: 1.35;
  margin-bottom: 0.8rem;
  letter-spacing: -0.3px;
}

.card-body h2 a {
  color: var(--text);
  text-decoration: none;
  transition: color 0.2s;
}

.card-body h2 a:hover { color: var(--primary); }

.card-body p {
  font-size: 0.95rem;
  color: var(--text-light);
  line-height: 1.65;
  margin-bottom: 1.2rem;
}

.read-more {
  font-family: 'Helvetica Neue', Arial, sans-serif;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--primary);
  text-decoration: none;
  letter-spacing: 0.3px;
  transition: color 0.2s;
}

.read-more:hover { color: var(--accent); }

/* Article page */
.article-header {
  background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
  color: white;
  padding: 4rem 2rem 3rem;
  text-align: center;
}

.article-header h1 {
  font-family: 'Helvetica Neue', Arial, sans-serif;
  font-size: 2.2rem;
  font-weight: 700;
  max-width: 800px;
  margin: 0 auto 1rem;
  letter-spacing: -0.5px;
  line-height: 1.25;
}

.article-meta {
  font-family: 'Helvetica Neue', Arial, sans-serif;
  font-size: 0.9rem;
  opacity: 0.85;
}

.article-body {
  max-width: 760px;
  margin: 0 auto;
  padding: 3rem 2rem 5rem;
}

.article-body h2 {
  font-family: 'Helvetica Neue', Arial, sans-serif;
  font-size: 1.6rem;
  font-weight: 700;
  color: var(--primary);
  margin: 2.5rem 0 1rem;
  letter-spacing: -0.3px;
}

.article-body h3 {
  font-family: 'Helvetica Neue', Arial, sans-serif;
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--text);
  margin: 2rem 0 0.8rem;
}

.article-body p {
  margin-bottom: 1.2rem;
  font-size: 1.05rem;
}

.article-body ul, .article-body ol {
  margin: 1rem 0 1.5rem 1.5rem;
}

.article-body li {
  margin-bottom: 0.5rem;
  font-size: 1.05rem;
}

.article-body strong { color: var(--text); }

.article-body blockquote {
  border-left: 4px solid var(--accent);
  padding: 1rem 1.5rem;
  margin: 1.5rem 0;
  background: rgba(200,169,81,0.06);
  font-style: italic;
}

.back-link {
  display: inline-block;
  margin-bottom: 2rem;
  font-family: 'Helvetica Neue', Arial, sans-serif;
  font-size: 0.9rem;
  color: var(--primary);
  text-decoration: none;
  font-weight: 600;
}

.back-link:hover { color: var(--accent); }

.site-footer {
  background: var(--primary);
  color: rgba(255,255,255,0.7);
  text-align: center;
  padding: 2.5rem 2rem;
  font-family: 'Helvetica Neue', Arial, sans-serif;
  font-size: 0.85rem;
}

.site-footer strong { color: white; }

.cta-bar {
  background: var(--accent);
  color: var(--primary);
  text-align: center;
  padding: 2rem;
  font-family: 'Helvetica Neue', Arial, sans-serif;
}

.cta-bar p {
  font-size: 1.1rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
}

.cta-bar small {
  font-size: 0.85rem;
  opacity: 0.8;
}

@media (max-width: 700px) {
  .hero h1 { font-size: 2rem; }
  .posts-grid { grid-template-columns: 1fr; }
  .header-inner { flex-direction: column; gap: 0.8rem; }
  nav a { margin-left: 1rem; }
  .article-header h1 { font-size: 1.7rem; }
}
"""

_HEADER_HTML = """<header class="site-header">
  <div class="header-inner">
    <a href="index.html" class="logo">Resurgent <span>Sports Rehab</span></a>
    <nav>
      <a href="index.html">Blog</a>
      <a href="#">About</a>
      <a href="#">Services</a>
      <a href="#">Contact</a>
    </nav>
  </div>
</header>"""

_FOOTER_HTML = """<div class="cta-bar">
  <p>Ready to move better, perform better, and stay in the game?</p>
  <small>Resurgent Sports Rehab &mdash; Fairfax &amp; Chantilly, Virginia &mdash; 1-on-1 sessions with board-certified sports PTs</small>
</div>
<footer class="site-footer">
  <p><strong>Resurgent Sports Rehab</strong> &mdash; Northern Virginia&rsquo;s boutique sports physical therapy clinic</p>
  <p style="margin-top: 0.5rem; font-size: 0.78rem; opacity: 0.6;">Demo site generated by ContentEngine &mdash; content is for review purposes only</p>
</footer>"""


def _page_wrap(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} | Resurgent Sports Rehab</title>
  <style>{_BASE_CSS}</style>
</head>
<body>
{_HEADER_HTML}
{body}
{_FOOTER_HTML}
</body>
</html>"""


# ---------------------------------------------------------------------------
# Parse drafts
# ---------------------------------------------------------------------------


def _parse_draft(filepath: Path) -> dict[str, Any] | None:
    text = filepath.read_text(encoding="utf-8")
    match = _FM_RE.match(text)
    if not match:
        return None

    fm = yaml.safe_load(match.group(1)) or {}
    body_md = match.group(2).strip()

    # Strip HTML comments (SEO notes, revision notes)
    body_md = re.sub(r"<!--.*?-->", "", body_md, flags=re.DOTALL).strip()

    return {
        "filename": filepath.stem,
        "title": fm.get("title", filepath.stem),
        "slug": fm.get("slug", filepath.stem),
        "meta_description": fm.get("meta_description", ""),
        "primary_keyword": fm.get("primary_keyword", ""),
        "seo_score": fm.get("seo_score", ""),
        "read_time": fm.get("estimated_read_time", ""),
        "date": fm.get("date_generated", str(date.today())),
        "schema_type": fm.get("schema_type", "Article"),
        "body_md": body_md,
    }


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------


def build() -> None:
    # Clean and create docs/
    if _DOCS_DIR.exists():
        shutil.rmtree(_DOCS_DIR)
    _DOCS_DIR.mkdir()

    md_converter = markdown.Markdown(extensions=["extra", "smarty"])

    # Parse all drafts
    posts: list[dict[str, Any]] = []
    for fp in sorted(_DRAFTS_DIR.glob("*.md")):
        parsed = _parse_draft(fp)
        if parsed:
            posts.append(parsed)

    # Sort by date descending
    posts.sort(key=lambda p: p["date"], reverse=True)

    # --- Build article pages ---
    for post in posts:
        md_converter.reset()
        body_html = md_converter.convert(post["body_md"])

        article_body = f"""
<div class="article-header">
  <h1>{post["title"]}</h1>
  <div class="article-meta">
    {post["date"]} &nbsp;&bull;&nbsp; {post["read_time"]} &nbsp;&bull;&nbsp; {post["primary_keyword"]}
  </div>
</div>
<div class="article-body">
  <a href="index.html" class="back-link">&larr; Back to all articles</a>
  {body_html}
</div>"""

        html = _page_wrap(post["title"], article_body)
        out_path = _DOCS_DIR / f"{post['slug']}.html"
        out_path.write_text(html, encoding="utf-8")

    # --- Build index page ---
    cards_html = ""
    for post in posts:
        desc = post["meta_description"][:160] if post["meta_description"] else ""
        cards_html += f"""
<div class="post-card">
  <div class="card-accent"></div>
  <div class="card-body">
    <div class="card-meta">
      <span class="tag">{post["schema_type"]}</span>
      <span>{post["date"]}</span>
      <span>{post["read_time"]}</span>
    </div>
    <h2><a href="{post["slug"]}.html">{post["title"]}</a></h2>
    <p>{desc}</p>
    <a href="{post["slug"]}.html" class="read-more">Read article &rarr;</a>
  </div>
</div>"""

    index_body = f"""
<div class="hero">
  <div class="badge">Northern Virginia&rsquo;s Sports PT Experts</div>
  <h1>The Resurgent Blog</h1>
  <p>Evidence-based insights on sports rehabilitation, injury prevention, and athletic performance from our team of board-certified Doctors of Physical Therapy.</p>
</div>
<div class="container">
  <div class="section-title">Latest Articles</div>
  <div class="posts-grid">
    {cards_html}
  </div>
</div>"""

    index_html = _page_wrap("Blog", index_body)
    (_DOCS_DIR / "index.html").write_text(index_html, encoding="utf-8")

    print(f"Built {len(posts)} article pages + index to docs/")


if __name__ == "__main__":
    build()
