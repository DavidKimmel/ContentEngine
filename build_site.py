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
@import url('https://fonts.googleapis.com/css2?family=Bitter:wght@400;700&family=Raleway:wght@400;500;600;700&family=Source+Sans+3:wght@400;500;600;700&display=swap');

:root {
  --navy: #042b4e;
  --navy-light: #0a3d6b;
  --orange: #eb5e28;
  --orange-hover: #d4511f;
  --blue: #096fc3;
  --bg: #f8f9fb;
  --bg-off: #eef1f5;
  --card-bg: #ffffff;
  --text: #1a1a2e;
  --text-mid: #3d4555;
  --text-light: #5a6478;
  --border: #d8dde6;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: 'Source Sans 3', 'Raleway', sans-serif;
  font-weight: 500;
  background: var(--bg);
  color: var(--text);
  line-height: 1.75;
  -webkit-font-smoothing: antialiased;
  font-size: 16px;
}

/* ---- Header ---- */
.site-header {
  background: #fff;
  border-bottom: 2px solid var(--border);
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: 0 1px 4px rgba(4,43,78,0.06);
}

.header-inner {
  max-width: 1120px;
  margin: 0 auto;
  padding: 1rem 2rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.logo {
  font-family: 'Bitter', serif;
  font-size: 1.35rem;
  font-weight: 700;
  color: var(--navy);
  text-decoration: none;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.logo span { color: var(--orange); }

nav { display: flex; align-items: center; gap: 0.5rem; }

nav a {
  color: var(--navy);
  text-decoration: none;
  font-size: 0.85rem;
  font-weight: 600;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  transition: background 0.2s, color 0.2s;
}

nav a:hover { background: var(--bg-off); color: var(--blue); }

nav .cta-btn {
  background: var(--orange);
  color: #fff;
  padding: 0.55rem 1.2rem;
  border-radius: 5px;
  font-weight: 700;
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

nav .cta-btn:hover { background: var(--orange-hover); color: #fff; }

/* ---- Hero ---- */
.hero {
  background: var(--navy);
  color: white;
  padding: 4.5rem 2rem 4rem;
  text-align: center;
}

.hero h1 {
  font-family: 'Bitter', serif;
  font-size: 2.6rem;
  font-weight: 700;
  margin-bottom: 1rem;
}

.hero p {
  font-size: 1.05rem;
  color: rgba(255,255,255,0.8);
  max-width: 620px;
  margin: 0 auto 2rem;
  line-height: 1.75;
}

.hero .location-tag {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--orange);
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 1rem;
}

/* ---- Content ---- */
.container {
  max-width: 1120px;
  margin: 0 auto;
  padding: 3.5rem 2rem;
}

.section-label {
  font-family: 'Raleway', sans-serif;
  font-size: 0.78rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 2px;
  color: var(--blue);
  margin-bottom: 0.5rem;
}

.section-title {
  font-family: 'Bitter', serif;
  font-size: 1.8rem;
  font-weight: 700;
  color: var(--navy);
  margin-bottom: 2.5rem;
}

/* ---- Posts Grid ---- */
.posts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 1.8rem;
}

.post-card {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 6px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(4,43,78,0.04);
  transition: box-shadow 0.25s, transform 0.25s;
}

.post-card:hover {
  box-shadow: 0 8px 30px rgba(4,43,78,0.12);
  transform: translateY(-2px);
}

.card-top {
  background: var(--navy);
  padding: 1.2rem 1.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-top .tag {
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  color: var(--orange);
}

.card-top .date {
  font-size: 0.75rem;
  color: rgba(255,255,255,0.6);
}

.card-body {
  padding: 1.5rem;
}

.card-body h2 {
  font-family: 'Bitter', serif;
  font-size: 1.15rem;
  font-weight: 700;
  line-height: 1.4;
  margin-bottom: 0.7rem;
  color: var(--navy);
}

.card-body h2 a {
  color: var(--navy);
  text-decoration: none;
  transition: color 0.2s;
}

.card-body h2 a:hover { color: var(--blue); }

.card-body p {
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--text-mid);
  line-height: 1.65;
  margin-bottom: 1.2rem;
}

.card-footer {
  padding: 0 1.5rem 1.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.read-more {
  font-size: 0.82rem;
  font-weight: 700;
  color: var(--blue);
  text-decoration: none;
  transition: color 0.2s;
}

.read-more:hover { color: var(--orange); }

.read-time {
  font-size: 0.75rem;
  color: var(--text-light);
}

/* ---- Article ---- */
.article-header {
  background: var(--navy);
  color: white;
  padding: 3.5rem 2rem 3rem;
}

.article-header-inner {
  max-width: 760px;
  margin: 0 auto;
}

.article-header .breadcrumb {
  font-size: 0.8rem;
  color: rgba(255,255,255,0.5);
  margin-bottom: 1.5rem;
}

.article-header .breadcrumb a {
  color: rgba(255,255,255,0.7);
  text-decoration: none;
}

.article-header .breadcrumb a:hover { color: var(--orange); }

.article-header h1 {
  font-family: 'Bitter', serif;
  font-size: 2.1rem;
  font-weight: 700;
  line-height: 1.3;
  margin-bottom: 1rem;
}

.article-meta {
  font-size: 0.85rem;
  color: rgba(255,255,255,0.6);
  display: flex;
  gap: 1.5rem;
  flex-wrap: wrap;
}

.article-meta span { display: flex; align-items: center; gap: 0.3rem; }

.article-body {
  max-width: 720px;
  margin: 0 auto;
  padding: 2.5rem 2rem 4rem;
  background: var(--card-bg);
  margin-top: -1.5rem;
  border-radius: 8px 8px 0 0;
  position: relative;
  box-shadow: 0 0 20px rgba(4,43,78,0.05);
}

.article-body h2 {
  font-family: 'Bitter', serif;
  font-size: 1.45rem;
  font-weight: 700;
  color: var(--navy);
  margin: 2.5rem 0 0.8rem;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid var(--bg-off);
}

.article-body h3 {
  font-family: 'Bitter', serif;
  font-size: 1.12rem;
  font-weight: 700;
  color: var(--navy-light);
  margin: 1.8rem 0 0.6rem;
}

.article-body p {
  margin-bottom: 1.2rem;
  font-size: 1.05rem;
  font-weight: 500;
  color: var(--text-mid);
  line-height: 1.85;
}

.article-body ul, .article-body ol {
  margin: 0.8rem 0 1.3rem 1.5rem;
}

.article-body li {
  margin-bottom: 0.5rem;
  font-size: 1.05rem;
  font-weight: 500;
  line-height: 1.75;
  color: var(--text-mid);
}

.article-body strong { color: var(--navy); font-weight: 700; }

.article-body blockquote {
  border-left: 3px solid var(--orange);
  padding: 1rem 1.4rem;
  margin: 1.5rem 0;
  background: var(--bg-off);
  font-style: italic;
  color: var(--text-mid);
  border-radius: 0 4px 4px 0;
}

/* ---- Footer ---- */
.cta-bar {
  background: var(--orange);
  color: #fff;
  text-align: center;
  padding: 2.5rem 2rem;
}

.cta-bar p {
  font-family: 'Bitter', serif;
  font-size: 1.3rem;
  font-weight: 700;
  margin-bottom: 0.4rem;
}

.cta-bar small {
  font-size: 0.88rem;
  opacity: 0.9;
}

.site-footer {
  background: var(--navy);
  color: rgba(255,255,255,0.5);
  text-align: center;
  padding: 2rem;
  font-size: 0.82rem;
}

.site-footer strong { color: #fff; }

.site-footer .demo-note {
  margin-top: 0.6rem;
  font-size: 0.72rem;
  opacity: 0.5;
  font-style: italic;
}

@media (max-width: 700px) {
  .hero h1 { font-size: 1.9rem; }
  .posts-grid { grid-template-columns: 1fr; }
  .header-inner { flex-direction: column; gap: 0.8rem; }
  .article-header h1 { font-size: 1.6rem; }
  .section-title { font-size: 1.4rem; }
}
"""

_HEADER_HTML = """<header class="site-header">
  <div class="header-inner">
    <a href="index.html" class="logo">Re<span>surgent</span> Sports Rehab</a>
    <nav>
      <a href="index.html">Blog</a>
      <a href="#">About</a>
      <a href="#">Services</a>
      <a href="#" class="cta-btn">Schedule Free Consult</a>
    </nav>
  </div>
</header>"""

_FOOTER_HTML = """<div class="cta-bar">
  <p>Ready to move better, perform better, and stay in the game?</p>
  <small>Schedule your free consultation &mdash; Fairfax &amp; Chantilly, Virginia</small>
</div>
<footer class="site-footer">
  <p><strong>Resurgent Sports Rehab</strong> &mdash; Northern Virginia&rsquo;s boutique sports physical therapy clinic</p>
  <p class="demo-note">Demo site &mdash; content is for editorial review purposes only</p>
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
  <div class="article-header-inner">
    <div class="breadcrumb"><a href="index.html">Blog</a> &nbsp;/&nbsp; {post["primary_keyword"]}</div>
    <h1>{post["title"]}</h1>
    <div class="article-meta">
      <span>{post["date"]}</span>
      <span>{post["read_time"]}</span>
      <span>{post["primary_keyword"]}</span>
    </div>
  </div>
</div>
<div class="article-body">
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
  <div class="card-top">
    <span class="tag">{post["primary_keyword"]}</span>
    <span class="date">{post["date"]}</span>
  </div>
  <div class="card-body">
    <h2><a href="{post["slug"]}.html">{post["title"]}</a></h2>
    <p>{desc}</p>
  </div>
  <div class="card-footer">
    <a href="{post["slug"]}.html" class="read-more">Read article &rarr;</a>
    <span class="read-time">{post["read_time"]}</span>
  </div>
</div>"""

    index_body = f"""
<div class="hero">
  <div class="location-tag">&#9679; Fairfax &amp; Chantilly, Virginia</div>
  <h1>The Resurgent Blog</h1>
  <p>Evidence-based insights on sports rehabilitation, injury prevention, and athletic performance from our team of board-certified Doctors of Physical Therapy.</p>
</div>
<div class="container">
  <div class="section-label">Resources</div>
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
