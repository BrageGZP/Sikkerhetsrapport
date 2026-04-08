# Maritim Sikkerhetsrapport Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a static GitHub Pages dashboard that fetches defense/maritime news twice daily via GitHub Actions and displays it in a bilingual, professionally styled HTML page.

**Architecture:** A Python script fetches from Norwegian government sites (via scraping) and international RSS feeds, filters by keywords, deduplicates, assigns articles to three sections, then renders a Jinja2 HTML template. GitHub Actions runs this twice daily and commits the result to `docs/` which GitHub Pages serves.

**Tech Stack:** Python 3.11, feedparser 6.0.11, requests 2.31.0, beautifulsoup4 4.12.3, jinja2 3.1.4, pytest, responses (HTTP mock), GitHub Actions, GitHub Pages

---

## File Map

| File | Responsibility |
|------|----------------|
| `requirements.txt` | Pinned Python dependencies |
| `requirements-dev.txt` | Test dependencies (pytest, responses) |
| `scripts/fetch_news.py` | Main entry point — orchestrates full pipeline |
| `scripts/models.py` | `Article` dataclass — shared data contract |
| `scripts/keywords.py` | Keyword lists and filter function |
| `scripts/dedup.py` | URL normalization and title-similarity deduplication |
| `scripts/sections.py` | Section assignment + age filter + sort + cap |
| `scripts/rss_fetcher.py` | Fetch and parse international RSS feeds |
| `scripts/scrapers.py` | Scrape Forsvaret.no, Kystverket, Sjøfartsdirektoratet |
| `scripts/renderer.py` | Render Jinja2 template → `docs/index.html` + `docs/data.json` |
| `templates/index.html.j2` | Full dashboard HTML template |
| `docs/index.html` | Generated output (committed by GitHub Actions) |
| `docs/data.json` | Generated JSON output (committed by GitHub Actions) |
| `.github/workflows/update.yml` | Cron workflow — runs twice daily |
| `tests/test_keywords.py` | Tests for keyword filter |
| `tests/test_dedup.py` | Tests for deduplication logic |
| `tests/test_sections.py` | Tests for section assignment, age filter, sort, cap |
| `tests/test_rss_fetcher.py` | Tests for RSS parsing (mocked HTTP) |
| `tests/test_scrapers.py` | Tests for Norwegian scrapers (mocked HTTP) |
| `tests/test_renderer.py` | Tests for HTML/JSON output |
| `tests/fixtures/` | Sample RSS XML and HTML for test mocks |

---

## Task 1: Project Scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `requirements-dev.txt`
- Create: `.gitignore`
- Create: `scripts/__init__.py`
- Create: `tests/__init__.py`
- Create: `docs/.gitkeep`

- [ ] **Step 1: Create requirements.txt**

```
feedparser==6.0.11
requests==2.31.0
beautifulsoup4==4.12.3
jinja2==3.1.4
```

- [ ] **Step 2: Create requirements-dev.txt**

```
pytest==8.1.1
responses==0.25.0
```

- [ ] **Step 3: Create .gitignore**

```
__pycache__/
*.py[cod]
.env
venv/
.venv/
```

- [ ] **Step 4: Create empty `__init__.py` files and `docs/.gitkeep`**

```bash
mkdir -p scripts tests tests/fixtures docs
touch scripts/__init__.py tests/__init__.py docs/.gitkeep
```

- [ ] **Step 5: Verify Python and install deps**

```bash
python3 --version   # should be 3.11+
pip install -r requirements.txt -r requirements-dev.txt
```

- [ ] **Step 6: Commit**

```bash
git init
git add requirements.txt requirements-dev.txt .gitignore scripts/__init__.py tests/__init__.py docs/.gitkeep
git commit -m "chore: initial project scaffold"
```

---

## Task 2: Article Data Model

**Files:**
- Create: `scripts/models.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_models.py`:

```python
from scripts.models import Article
from datetime import datetime, timezone

def test_article_fields():
    a = Article(
        title="Test Title",
        url="https://example.com/article",
        published=datetime(2026, 4, 3, 6, 0, tzinfo=timezone.utc),
        source="Example Source",
        language="no",
        summary="A short summary.",
    )
    assert a.title == "Test Title"
    assert a.language == "no"
    assert a.section is None  # not yet assigned

def test_article_to_dict():
    a = Article(
        title="Test",
        url="https://example.com",
        published=datetime(2026, 4, 3, 6, 0, tzinfo=timezone.utc),
        source="Src",
        language="en",
        summary="Summary",
    )
    d = a.to_dict()
    assert d["title"] == "Test"
    assert d["published"] == "2026-04-03T06:00:00Z"
    assert "section" not in d  # section omitted if None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_models.py -v
```
Expected: `ImportError` — `scripts.models` does not exist

- [ ] **Step 3: Implement `scripts/models.py`**

```python
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Article:
    title: str
    url: str
    published: datetime
    source: str
    language: str  # "no" or "en"
    summary: str
    section: Optional[str] = field(default=None)  # "nyheter", "regelverk", "rov_teknologi"

    def to_dict(self) -> dict:
        d = {
            "title": self.title,
            "url": self.url,
            "published": self.published.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source": self.source,
            "language": self.language,
            "summary": self.summary,
        }
        if self.section is not None:
            d["section"] = self.section
        return d
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_models.py -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/models.py tests/test_models.py
git commit -m "feat: add Article dataclass with to_dict"
```

---

## Task 3: Keyword Filtering

**Files:**
- Create: `scripts/keywords.py`
- Create: `tests/test_keywords.py`

- [ ] **Step 1: Write the failing test**

```python
from scripts.models import Article
from scripts.keywords import matches_keywords
from datetime import datetime, timezone

def _article(title="", summary="", language="en"):
    return Article(
        title=title, url="https://x.com", summary=summary,
        published=datetime(2026, 4, 3, tzinfo=timezone.utc),
        source="Test", language=language,
    )

def test_matches_english_keyword_in_title():
    assert matches_keywords(_article(title="New naval mine detected")) is True

def test_matches_norwegian_keyword_in_summary():
    assert matches_keywords(_article(summary="Øvelse fokuserte på minerydding i fjorden", language="no")) is True

def test_no_match_returns_false():
    assert matches_keywords(_article(title="Weather forecast for Oslo")) is False

def test_case_insensitive():
    assert matches_keywords(_article(title="UNDERWATER ROV test")) is True

def test_partial_word_does_not_match():
    # "mine" should not match "mineral" — use word-boundary matching
    assert matches_keywords(_article(title="Mineral resources in Norway")) is False
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_keywords.py -v
```

- [ ] **Step 3: Implement `scripts/keywords.py`**

```python
import re
from scripts.models import Article

KEYWORDS_NO = [
    "mine", "minerydding", "undervann", "rov", "havnesikkerhet",
    "maritim sikkerhet", "sjøforsvar", "ubåt", "mcm",
]

KEYWORDS_EN = [
    "naval mine", "underwater rov", "mine countermeasure", "mcm",
    "uuv", "auv", "underwater security", "port security",
    "subsea defense", "rov defense",
]

ALL_KEYWORDS = KEYWORDS_NO + KEYWORDS_EN

# Build word-boundary patterns for single-word keywords;
# multi-word phrases use simple substring match (already specific enough)
_PATTERNS = [
    re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE)
    if " " not in kw
    else re.compile(re.escape(kw), re.IGNORECASE)
    for kw in ALL_KEYWORDS
]


def matches_keywords(article: Article) -> bool:
    """Return True if article title or summary contains at least one keyword."""
    text = f"{article.title} {article.summary}"
    return any(p.search(text) for p in _PATTERNS)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_keywords.py -v
```
Expected: PASS (including the partial-word boundary test)

- [ ] **Step 5: Commit**

```bash
git add scripts/keywords.py tests/test_keywords.py
git commit -m "feat: add keyword filter with word-boundary matching"
```

---

## Task 4: Deduplication

**Files:**
- Create: `scripts/dedup.py`
- Create: `tests/test_dedup.py`

- [ ] **Step 1: Write the failing test**

```python
from scripts.models import Article
from scripts.dedup import deduplicate
from datetime import datetime, timezone

def _a(url, title="Title", published=None):
    return Article(
        title=title,
        url=url,
        published=published or datetime(2026, 4, 3, tzinfo=timezone.utc),
        source="Src", language="en", summary="",
    )

def test_exact_url_duplicate_removed():
    articles = [_a("https://x.com/article"), _a("https://x.com/article")]
    result = deduplicate(articles)
    assert len(result) == 1

def test_url_utm_parameters_stripped():
    a1 = _a("https://x.com/article?utm_source=feed&utm_medium=rss")
    a2 = _a("https://x.com/article")
    result = deduplicate([a1, a2])
    assert len(result) == 1

def test_url_trailing_slash_stripped():
    result = deduplicate([_a("https://x.com/article/"), _a("https://x.com/article")])
    assert len(result) == 1

def test_near_duplicate_title_removed():
    a1 = _a("https://x.com/a1", title="Navy deploys new ROV for mine clearance operations")
    a2 = _a("https://x.com/a2", title="Navy deploys new ROV for mine clearance operation")
    result = deduplicate([a1, a2])
    assert len(result) == 1

def test_distinct_articles_kept():
    a1 = _a("https://x.com/a", title="Article about ROV")
    a2 = _a("https://y.com/b", title="Completely different naval news story")
    result = deduplicate([a1, a2])
    assert len(result) == 2
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_dedup.py -v
```

- [ ] **Step 3: Implement `scripts/dedup.py`**

```python
from difflib import SequenceMatcher
from urllib.parse import urlparse, urlencode, parse_qsl
from scripts.models import Article


def _normalize_url(url: str) -> str:
    """Remove UTM parameters and trailing slashes."""
    parsed = urlparse(url)
    utm_free = {
        k: v for k, v in parse_qsl(parsed.query)
        if not k.startswith("utm_")
    }
    normalized = parsed._replace(
        query=urlencode(utm_free),
        path=parsed.path.rstrip("/"),
    )
    return normalized.geturl().rstrip("/")


def _title_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def deduplicate(articles: list[Article]) -> list[Article]:
    seen_urls: set[str] = set()
    seen_titles: list[str] = []
    result: list[Article] = []

    for article in articles:
        norm_url = _normalize_url(article.url)
        if norm_url in seen_urls:
            continue

        # Check title similarity against already-kept articles
        is_near_dup = any(
            _title_similarity(article.title, t) > 0.85
            for t in seen_titles
        )
        if is_near_dup:
            continue

        seen_urls.add(norm_url)
        seen_titles.append(article.title)
        result.append(article)

    return result
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_dedup.py -v
```

- [ ] **Step 5: Commit**

```bash
git add scripts/dedup.py tests/test_dedup.py
git commit -m "feat: add deduplication by URL normalization and title similarity"
```

---

## Task 5: Section Assignment, Age Filter, Sort, Cap

**Files:**
- Create: `scripts/sections.py`
- Create: `tests/test_sections.py`

- [ ] **Step 1: Write the failing test**

```python
from scripts.models import Article
from scripts.sections import assign_and_organize
from datetime import datetime, timezone, timedelta

NOW = datetime(2026, 4, 3, 12, 0, tzinfo=timezone.utc)

def _a(source, title="Title", days_old=1, language="en"):
    return Article(
        title=title,
        url=f"https://x.com/{title[:10]}",
        published=NOW - timedelta(days=days_old),
        source=source, language=language, summary="test summary",
    )

def test_kystverket_goes_to_regelverk():
    articles = [_a("Kystverket.no")]
    result = assign_and_organize(articles, now=NOW)
    assert result["regelverk"][0].source == "Kystverket.no"
    assert result["nyheter"] == []

def test_rov_keyword_goes_to_rov_teknologi():
    articles = [_a("USNI News", title="New UUV deployed for mine clearance")]
    result = assign_and_organize(articles, now=NOW)
    assert result["rov_teknologi"][0].title.startswith("New UUV")
    assert result["nyheter"] == []

def test_section2_priority_over_section3():
    # A Kystverket article with ROV keyword should go to regelverk, not rov_teknologi
    articles = [_a("Kystverket.no", title="ROV used in port security exercise")]
    result = assign_and_organize(articles, now=NOW)
    assert result["regelverk"] != []
    assert result["rov_teknologi"] == []

def test_old_regelverk_article_kept_within_90_days():
    articles = [_a("Kystverket.no", days_old=89)]
    result = assign_and_organize(articles, now=NOW)
    assert len(result["regelverk"]) == 1

def test_too_old_nyheter_article_filtered_out():
    articles = [_a("USNI News", days_old=31)]
    result = assign_and_organize(articles, now=NOW)
    assert result["nyheter"] == []
    assert result["rov_teknologi"] == []

def test_section_capped_at_10():
    articles = [_a("Forsvaret.no", title=f"News {i}", days_old=i) for i in range(15)]
    result = assign_and_organize(articles, now=NOW)
    assert len(result["nyheter"]) == 10

def test_sorted_newest_first():
    articles = [_a("Forsvaret.no", title=f"News {i}", days_old=i) for i in range(3)]
    result = assign_and_organize(articles, now=NOW)
    published_dates = [a.published for a in result["nyheter"]]
    assert published_dates == sorted(published_dates, reverse=True)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_sections.py -v
```

- [ ] **Step 3: Implement `scripts/sections.py`**

```python
from datetime import datetime, timezone, timedelta
from scripts.models import Article

SECTION2_SOURCES = {"Kystverket.no", "Sjøfartsdirektoratet.no"}

SECTION3_KEYWORDS = [
    "rov", "uuv", "auv", "mine countermeasure", "mcm",
    "minerydding", "undervann",
]

MAX_AGE = {
    "nyheter": 30,
    "regelverk": 90,
    "rov_teknologi": 30,
}

MAX_COUNT = 10


def _matches_section3(article: Article) -> bool:
    text = f"{article.title} {article.summary}".lower()
    return any(kw in text for kw in SECTION3_KEYWORDS)


def assign_and_organize(
    articles: list[Article],
    now: datetime | None = None,
) -> dict[str, list[Article]]:
    if now is None:
        now = datetime.now(timezone.utc)

    sections: dict[str, list[Article]] = {
        "nyheter": [],
        "regelverk": [],
        "rov_teknologi": [],
    }

    for article in articles:
        # Assign section (priority: regelverk > rov_teknologi > nyheter)
        if article.source in SECTION2_SOURCES:
            article.section = "regelverk"
        elif _matches_section3(article):
            article.section = "rov_teknologi"
        else:
            article.section = "nyheter"
        sections[article.section].append(article)

    # Per-section: filter by age, sort newest first, cap at MAX_COUNT
    for name, items in sections.items():
        cutoff = now - timedelta(days=MAX_AGE[name])
        items = [a for a in items if a.published >= cutoff]
        items.sort(key=lambda a: a.published, reverse=True)
        sections[name] = items[:MAX_COUNT]

    return sections
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_sections.py -v
```

- [ ] **Step 5: Commit**

```bash
git add scripts/sections.py tests/test_sections.py
git commit -m "feat: add section assignment with age filter, sort, and cap"
```

---

## Task 6: RSS Fetcher (International Sources)

**Files:**
- Create: `scripts/rss_fetcher.py`
- Create: `tests/test_rss_fetcher.py`
- Create: `tests/fixtures/sample_rss.xml`

- [ ] **Step 1: Create sample RSS fixture**

Create `tests/fixtures/sample_rss.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>USNI News</title>
    <item>
      <title>Navy tests new mine countermeasure UUV</title>
      <link>https://news.usni.org/2026/04/03/navy-tests-uuv</link>
      <description>The US Navy conducted tests of a new unmanned underwater vehicle designed for mine clearance operations.</description>
      <pubDate>Fri, 03 Apr 2026 05:00:00 +0000</pubDate>
    </item>
    <item>
      <title>Budget hearing for next year</title>
      <link>https://news.usni.org/2026/04/02/budget</link>
      <description>Senate holds hearing on defense budget.</description>
      <pubDate>Thu, 02 Apr 2026 10:00:00 +0000</pubDate>
    </item>
  </channel>
</rss>
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_rss_fetcher.py`:

```python
import responses as responses_mock
import pytest
from pathlib import Path
from scripts.rss_fetcher import fetch_rss

FIXTURE = Path(__file__).parent / "fixtures" / "sample_rss.xml"

@responses_mock.activate
def test_fetch_rss_returns_articles():
    responses_mock.add(
        responses_mock.GET,
        "https://news.usni.org/feed",
        body=FIXTURE.read_text(),
        content_type="application/rss+xml",
    )
    articles = fetch_rss("https://news.usni.org/feed", source="USNI News")
    assert len(articles) == 2
    assert articles[0].title == "Navy tests new mine countermeasure UUV"
    assert articles[0].language == "en"
    assert articles[0].source == "USNI News"

@responses_mock.activate
def test_fetch_rss_returns_empty_on_http_error(caplog):
    responses_mock.add(
        responses_mock.GET,
        "https://news.usni.org/feed",
        status=503,
    )
    articles = fetch_rss("https://news.usni.org/feed", source="USNI News")
    assert articles == []
    assert "ERROR" in caplog.text or "503" in caplog.text
```

- [ ] **Step 3: Run test to verify it fails**

```bash
pytest tests/test_rss_fetcher.py -v
```

- [ ] **Step 4: Implement `scripts/rss_fetcher.py`**

```python
import logging
import feedparser
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from scripts.models import Article

logger = logging.getLogger(__name__)

RSS_SOURCES = [
    ("https://news.usni.org/feed", "USNI News"),
    ("https://www.defensenews.com/arc/outboundfeeds/rss/", "Defense News"),
    ("https://www.navalnews.com/feed/", "Naval News"),
    ("https://breakingdefense.com/feed/", "Breaking Defense"),
    ("https://maritime-executive.com/rss/articles", "The Maritime Executive"),
]


def fetch_rss(url: str, source: str) -> list[Article]:
    """Fetch and parse a single RSS feed. Returns empty list on any error."""
    try:
        feed = feedparser.parse(url)
        if feed.bozo and feed.bozo_exception:
            raise feed.bozo_exception
        if getattr(feed, "status", 200) >= 400:
            raise ValueError(f"HTTP {feed.status}")
    except Exception as exc:
        logger.error("ERROR fetching RSS %s: %s", url, exc)
        return []

    articles = []
    for entry in feed.entries:
        try:
            published = _parse_date(entry)
            articles.append(Article(
                title=entry.get("title", "").strip(),
                url=entry.get("link", "").strip(),
                published=published,
                source=source,
                language="en",
                summary=_get_summary(entry),
            ))
        except Exception as exc:
            logger.warning("Skipping malformed RSS entry from %s: %s", source, exc)

    return articles


def fetch_all_rss() -> list[Article]:
    articles = []
    for url, source in RSS_SOURCES:
        articles.extend(fetch_rss(url, source))
    return articles


def _parse_date(entry) -> datetime:
    raw = entry.get("published") or entry.get("updated", "")
    if raw:
        try:
            return parsedate_to_datetime(raw).astimezone(timezone.utc)
        except Exception:
            pass
    return datetime.now(timezone.utc)


def _get_summary(entry) -> str:
    summary = entry.get("summary") or entry.get("description") or ""
    # Strip HTML tags if present
    import re
    return re.sub(r"<[^>]+>", "", summary).strip()[:500]
```

- [ ] **Step 5: Run test to verify it passes**

```bash
pytest tests/test_rss_fetcher.py -v
```

- [ ] **Step 6: Commit**

```bash
git add scripts/rss_fetcher.py tests/test_rss_fetcher.py tests/fixtures/sample_rss.xml
git commit -m "feat: add RSS fetcher for international sources"
```

---

## Task 7: Norwegian Scrapers

**Files:**
- Create: `scripts/scrapers.py`
- Create: `tests/test_scrapers.py`
- Create: `tests/fixtures/forsvaret_nyheter.html`
- Create: `tests/fixtures/kystverket_nyheter.html`
- Create: `tests/fixtures/sjofartsdir_nyheter.html`

- [ ] **Step 1: Create HTML fixtures**

**Note:** Before writing the scrapers, visit each site manually to confirm current HTML structure and CSS selectors. The selectors below are placeholders — update them after inspection.

Create `tests/fixtures/forsvaret_nyheter.html` — a minimal HTML snippet that mimics the article list structure on `https://www.forsvaret.no/aktuelt`. Example (update selectors after real inspection):

```html
<html><body>
<div class="article-list">
  <article class="article-list__item">
    <a href="/aktuelt/2026/april/ny-oevelse" class="article-list__link">
      <h2 class="article-list__title">Ny øvelse fokuserer på minerydding</h2>
      <p class="article-list__intro">Forsvaret gjennomfører stor øvelse i Nordsjøen.</p>
      <time datetime="2026-04-03T08:00:00">3. april 2026</time>
    </a>
  </article>
</div>
</body></html>
```

Create `tests/fixtures/kystverket_nyheter.html`:

```html
<html><body>
<ul class="news-list">
  <li class="news-list__item">
    <a href="/nyheter/2026/ny-forskrift" class="news-list__link">
      <h2 class="news-list__title">Ny forskrift for havnesikkerhet</h2>
      <p class="news-list__intro">Kystverket innfører nye regler for havner.</p>
      <time datetime="2026-04-03T07:00:00">3. april 2026</time>
    </a>
  </li>
</ul>
</body></html>
```

Create `tests/fixtures/sjofartsdir_nyheter.html`:

```html
<html><body>
<div class="news-list">
  <article class="news-item">
    <a href="/nyheter/2026/havnesikkerhet-MCM">
      <h2>Oppdaterte retningslinjer for MCM i norske havner</h2>
      <p>Sjøfartsdirektoratet publiserer oppdaterte retningslinjer.</p>
      <time datetime="2026-04-02T09:00:00">2. april 2026</time>
    </a>
  </article>
</div>
</body></html>
```

- [ ] **Step 2: Write the failing test**

```python
import responses as responses_mock
from pathlib import Path
from scripts.scrapers import scrape_forsvaret, scrape_kystverket, scrape_sjofartsdir

FIXTURES = Path(__file__).parent / "fixtures"

@responses_mock.activate
def test_scrape_forsvaret_returns_articles():
    responses_mock.add(
        responses_mock.GET,
        "https://www.forsvaret.no/aktuelt",
        body=(FIXTURES / "forsvaret_nyheter.html").read_text(),
        content_type="text/html",
    )
    articles = scrape_forsvaret()
    assert len(articles) >= 1
    assert articles[0].source == "Forsvaret.no"
    assert articles[0].language == "no"
    assert articles[0].url.startswith("https://www.forsvaret.no")

@responses_mock.activate
def test_scrape_forsvaret_returns_empty_on_http_error(caplog):
    responses_mock.add(
        responses_mock.GET,
        "https://www.forsvaret.no/aktuelt",
        status=404,
    )
    articles = scrape_forsvaret()
    assert articles == []
    assert "ERROR" in caplog.text or "404" in caplog.text

@responses_mock.activate
def test_scrape_forsvaret_warns_on_zero_results(caplog):
    responses_mock.add(
        responses_mock.GET,
        "https://www.forsvaret.no/aktuelt",
        body="<html><body><p>No articles here</p></body></html>",
        content_type="text/html",
    )
    articles = scrape_forsvaret()
    assert articles == []
    assert "0 articles" in caplog.text
```

- [ ] **Step 3: Run test to verify it fails**

```bash
pytest tests/test_scrapers.py -v
```

- [ ] **Step 4: Implement `scripts/scrapers.py`**

**Important:** The CSS selectors below MUST be verified by manually loading each URL before finalizing. Update selectors if they differ.

```python
import logging
import requests
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from scripts.models import Article

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; MaritimDashboard/1.0)"}
BASE_FORSVARET = "https://www.forsvaret.no"
BASE_KYSTVERKET = "https://www.kystverket.no"
BASE_SJOFARTSDIR = "https://www.sjofartsdir.no"


def _get_html(url: str) -> str | None:
    """Fetch URL, return HTML string or None on HTTP error."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return resp.text
    except requests.HTTPError as exc:
        logger.error("ERROR fetching %s: %s", url, exc)
        return None
    except requests.RequestException as exc:
        logger.error("ERROR fetching %s: %s", url, exc)
        return None


def _warn_if_empty(source: str, articles: list[Article]) -> list[Article]:
    if not articles:
        logger.warning(
            "WARNING: 0 articles scraped from %s — page structure may have changed",
            source,
        )
    return articles


def scrape_forsvaret() -> list[Article]:
    html = _get_html(f"{BASE_FORSVARET}/aktuelt")
    if html is None:
        return []

    soup = BeautifulSoup(html, "html.parser")
    articles = []

    # TODO: Verify selector after inspecting https://www.forsvaret.no/aktuelt
    for item in soup.select("article.article-list__item"):
        try:
            link = item.select_one("a.article-list__link")
            title = item.select_one(".article-list__title")
            intro = item.select_one(".article-list__intro")
            time_el = item.select_one("time[datetime]")

            if not link or not title:
                continue

            href = link.get("href", "")
            url = href if href.startswith("http") else f"{BASE_FORSVARET}{href}"
            published = _parse_datetime_attr(time_el)

            articles.append(Article(
                title=title.get_text(strip=True),
                url=url,
                published=published,
                source="Forsvaret.no",
                language="no",
                summary=intro.get_text(strip=True) if intro else "",
            ))
        except Exception as exc:
            logger.warning("Skipping malformed Forsvaret article: %s", exc)

    return _warn_if_empty("Forsvaret.no", articles)


def scrape_kystverket() -> list[Article]:
    html = _get_html(f"{BASE_KYSTVERKET}/nyheter/")
    if html is None:
        return []

    soup = BeautifulSoup(html, "html.parser")
    articles = []

    # TODO: Verify selector after inspecting https://www.kystverket.no/nyheter/
    for item in soup.select(".news-list__item, .article-item"):
        try:
            link = item.select_one("a")
            title_el = item.select_one("h2, h3, .news-list__title")
            summary_el = item.select_one("p, .news-list__intro")
            time_el = item.select_one("time[datetime]")

            if not link or not title_el:
                continue

            href = link.get("href", "")
            url = href if href.startswith("http") else f"{BASE_KYSTVERKET}{href}"

            articles.append(Article(
                title=title_el.get_text(strip=True),
                url=url,
                published=_parse_datetime_attr(time_el),
                source="Kystverket.no",
                language="no",
                summary=summary_el.get_text(strip=True) if summary_el else "",
            ))
        except Exception as exc:
            logger.warning("Skipping malformed Kystverket article: %s", exc)

    return _warn_if_empty("Kystverket.no", articles)


def scrape_sjofartsdir() -> list[Article]:
    html = _get_html(f"{BASE_SJOFARTSDIR}/nyheter/")
    if html is None:
        return []

    soup = BeautifulSoup(html, "html.parser")
    articles = []

    # TODO: Verify selector after inspecting https://www.sjofartsdir.no/nyheter/
    for item in soup.select(".news-item, article"):
        try:
            link = item.select_one("a")
            title_el = item.select_one("h2, h3")
            summary_el = item.select_one("p")
            time_el = item.select_one("time[datetime]")

            if not link or not title_el:
                continue

            href = link.get("href", "")
            url = href if href.startswith("http") else f"{BASE_SJOFARTSDIR}{href}"

            articles.append(Article(
                title=title_el.get_text(strip=True),
                url=url,
                published=_parse_datetime_attr(time_el),
                source="Sjøfartsdirektoratet.no",
                language="no",
                summary=summary_el.get_text(strip=True) if summary_el else "",
            ))
        except Exception as exc:
            logger.warning("Skipping malformed Sjøfartsdirektoratet article: %s", exc)

    return _warn_if_empty("Sjøfartsdirektoratet.no", articles)


def fetch_all_norwegian() -> list[Article]:
    articles = []
    for scraper in [scrape_forsvaret, scrape_kystverket, scrape_sjofartsdir]:
        articles.extend(scraper())
    return articles


def _parse_datetime_attr(time_el) -> datetime:
    if time_el and time_el.get("datetime"):
        try:
            dt = datetime.fromisoformat(time_el["datetime"].replace("Z", "+00:00"))
            return dt.astimezone(timezone.utc)
        except ValueError:
            pass
    return datetime.now(timezone.utc)
```

- [ ] **Step 5: Run test to verify it passes**

```bash
pytest tests/test_scrapers.py -v
```

- [ ] **Step 6: Commit**

```bash
git add scripts/scrapers.py tests/test_scrapers.py tests/fixtures/
git commit -m "feat: add Norwegian government site scrapers"
```

---

## Task 8: Renderer (HTML + JSON output)

**Files:**
- Create: `scripts/renderer.py`
- Create: `templates/index.html.j2`
- Create: `tests/test_renderer.py`

- [ ] **Step 1: Write the failing test**

```python
import json
from pathlib import Path
from datetime import datetime, timezone
from scripts.models import Article
from scripts.renderer import render

DOCS = Path("docs")

def _article(section, title="Test", lang="en", source="USNI News"):
    a = Article(
        title=title,
        url="https://example.com/article",
        published=datetime(2026, 4, 3, 6, 0, tzinfo=timezone.utc),
        source=source,
        language=lang,
        summary="A short summary.",
        section=section,
    )
    return a

def test_render_creates_index_html(tmp_path):
    sections = {
        "nyheter": [_article("nyheter", lang="no", source="Forsvaret.no")],
        "regelverk": [_article("regelverk", lang="no", source="Kystverket.no")],
        "rov_teknologi": [_article("rov_teknologi")],
    }
    render(sections, docs_dir=tmp_path, generated_at=datetime(2026, 4, 3, 6, 0, tzinfo=timezone.utc))
    assert (tmp_path / "index.html").exists()
    html = (tmp_path / "index.html").read_text()
    assert "Maritim Sikkerhetsrapport" in html
    assert "Forsvaret.no" in html

def test_render_creates_data_json(tmp_path):
    sections = {
        "nyheter": [_article("nyheter")],
        "regelverk": [],
        "rov_teknologi": [],
    }
    render(sections, docs_dir=tmp_path, generated_at=datetime(2026, 4, 3, 6, 0, tzinfo=timezone.utc))
    data = json.loads((tmp_path / "data.json").read_text())
    assert data["generated_at"] == "2026-04-03T06:00:00Z"
    assert "next_update_utc" in data
    assert len(data["sections"]["nyheter"]) == 1
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_renderer.py -v
```

- [ ] **Step 3: Create `templates/index.html.j2`**

```html
<!DOCTYPE html>
<html lang="no">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Maritim Sikkerhetsrapport</title>
  <style>
    :root {
      --navy: #0a1628;
      --navy-mid: #132040;
      --navy-light: #1e3060;
      --accent: #4a9edd;
      --text: #e8edf5;
      --text-muted: #8fa3c0;
      --border: #2a3f60;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { background: var(--navy); color: var(--text); font-family: 'Segoe UI', system-ui, sans-serif; line-height: 1.6; }
    header { background: var(--navy-mid); border-bottom: 2px solid var(--accent); padding: 1.5rem 2rem; }
    header h1 { font-size: 1.5rem; color: var(--accent); }
    header .meta { font-size: 0.85rem; color: var(--text-muted); margin-top: 0.25rem; }
    main { max-width: 1100px; margin: 0 auto; padding: 2rem; }
    section { margin-bottom: 3rem; }
    section h2 { font-size: 1.15rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--accent); border-bottom: 1px solid var(--border); padding-bottom: 0.5rem; margin-bottom: 1.25rem; }
    .article-grid { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); }
    .card { background: var(--navy-mid); border: 1px solid var(--border); border-radius: 6px; padding: 1rem; }
    .card:hover { border-color: var(--accent); }
    .card .source { font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }
    .card h3 { font-size: 0.95rem; margin: 0.35rem 0; }
    .card h3 a { color: var(--text); text-decoration: none; }
    .card h3 a:hover { color: var(--accent); }
    .card .date { font-size: 0.75rem; color: var(--text-muted); }
    .card .summary { font-size: 0.85rem; color: var(--text-muted); margin-top: 0.5rem; }
    .empty { color: var(--text-muted); font-style: italic; font-size: 0.9rem; }
    footer { text-align: center; padding: 2rem; font-size: 0.8rem; color: var(--text-muted); border-top: 1px solid var(--border); }
    footer a { color: var(--accent); }
    @media (max-width: 600px) { header { padding: 1rem; } main { padding: 1rem; } }
  </style>
</head>
<body>
<header>
  <h1>Maritim Sikkerhetsrapport — Miner &amp; Undervannssikkerhet</h1>
  <div class="meta">
    Sist oppdatert: {{ generated_at }} UTC &nbsp;|&nbsp;
    Neste oppdatering: {{ next_update_utc }}
  </div>
</header>
<main>

  <section>
    <h2>Aktuelle nyheter</h2>
    {% if sections.nyheter %}
    <div class="article-grid">
      {% for a in sections.nyheter %}
      <div class="card" {% if a.language == 'en' %}lang="en"{% endif %}>
        <div class="source">{{ a.source }}</div>
        <h3><a href="{{ a.url }}" target="_blank" rel="noopener">{{ a.title }}</a></h3>
        <div class="date">{{ a.published }}</div>
        {% if a.summary %}<div class="summary">{{ a.summary }}</div>{% endif %}
      </div>
      {% endfor %}
    </div>
    {% else %}
    <p class="empty">Ingen aktuelle nyheter funnet.</p>
    {% endif %}
  </section>

  <section>
    <h2>Regelverk &amp; Havnesikkerhet</h2>
    {% if sections.regelverk %}
    <div class="article-grid">
      {% for a in sections.regelverk %}
      <div class="card">
        <div class="source">{{ a.source }}</div>
        <h3><a href="{{ a.url }}" target="_blank" rel="noopener">{{ a.title }}</a></h3>
        <div class="date">{{ a.published }}</div>
        {% if a.summary %}<div class="summary">{{ a.summary }}</div>{% endif %}
      </div>
      {% endfor %}
    </div>
    {% else %}
    <p class="empty">Ingen regelverksoppdateringer funnet.</p>
    {% endif %}
  </section>

  <section lang="en">
    <h2>ROV &amp; Teknologi</h2>
    {% if sections.rov_teknologi %}
    <div class="article-grid">
      {% for a in sections.rov_teknologi %}
      <div class="card">
        <div class="source">{{ a.source }}</div>
        <h3><a href="{{ a.url }}" target="_blank" rel="noopener">{{ a.title }}</a></h3>
        <div class="date">{{ a.published }}</div>
        {% if a.summary %}<div class="summary">{{ a.summary }}</div>{% endif %}
      </div>
      {% endfor %}
    </div>
    {% else %}
    <p class="empty">No ROV/technology articles found.</p>
    {% endif %}
  </section>

</main>
<footer>
  Automatisk generert av GitHub Actions &nbsp;|&nbsp;
  <a href="{{ repo_url }}" target="_blank" rel="noopener">GitHub</a>
</footer>
</body>
</html>
```

- [ ] **Step 4: Implement `scripts/renderer.py`**

```python
import json
from datetime import datetime, timezone
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from scripts.models import Article

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
CRON_TIMES_UTC = ["04:00", "12:00"]


def _next_update(now: datetime) -> str:
    current_hhmm = now.strftime("%H:%M")
    for t in CRON_TIMES_UTC:
        if current_hhmm < t:
            return f"{t} UTC"
    return f"{CRON_TIMES_UTC[0]} UTC (tomorrow)"


def render(
    sections: dict[str, list[Article]],
    docs_dir: Path,
    generated_at: datetime | None = None,
    repo_url: str = "https://github.com",
) -> None:
    if generated_at is None:
        generated_at = datetime.now(timezone.utc)

    docs_dir.mkdir(parents=True, exist_ok=True)

    # Render article dates to readable strings for template
    def fmt_article(a: Article) -> dict:
        d = a.to_dict()
        d["published"] = a.published.strftime("%d.%m.%Y %H:%M UTC")
        d["url"] = a.url
        return d

    template_sections = {
        name: [fmt_article(a) for a in items]
        for name, items in sections.items()
    }

    # Build a lightweight namespace for the template
    class Ns:
        pass

    ns = Ns()
    for k, v in template_sections.items():
        # Convert list of dicts to simple objects for template dot-access
        setattr(ns, k, [_DotDict(d) for d in v])

    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)
    tmpl = env.get_template("index.html.j2")

    html = tmpl.render(
        generated_at=generated_at.strftime("%Y-%m-%d %H:%M"),
        next_update_utc=_next_update(generated_at),
        sections=ns,
        repo_url=repo_url,
    )

    (docs_dir / "index.html").write_text(html, encoding="utf-8")

    # Write data.json
    data = {
        "generated_at": generated_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "next_update_utc": _next_update(generated_at),
        "sections": {
            name: [a.to_dict() for a in items]
            for name, items in sections.items()
        },
    }
    (docs_dir / "data.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


class _DotDict:
    """Simple dot-access wrapper for template rendering."""
    def __init__(self, d: dict):
        self.__dict__.update(d)
```

- [ ] **Step 5: Run test to verify it passes**

```bash
pytest tests/test_renderer.py -v
```

- [ ] **Step 6: Commit**

```bash
git add scripts/renderer.py templates/index.html.j2 tests/test_renderer.py
git commit -m "feat: add Jinja2 renderer generating index.html and data.json"
```

---

## Task 9: Main Pipeline (`fetch_news.py`)

**Files:**
- Create: `scripts/fetch_news.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_fetch_news.py
# Integration-style test using mocked fetchers
from unittest.mock import patch
from datetime import datetime, timezone
from pathlib import Path
from scripts.models import Article
from scripts import fetch_news

def _article(title, source="USNI News", lang="en"):
    return Article(
        title=title,
        url=f"https://example.com/{title[:8]}",
        published=datetime(2026, 4, 3, 6, 0, tzinfo=timezone.utc),
        source=source, language=lang, summary="relevant MCM content",
    )

def test_pipeline_writes_output(tmp_path):
    mock_articles = [
        _article("Mine countermeasure ROV test"),
        _article("Ny øvelse MCM", source="Forsvaret.no", lang="no"),
    ]
    with patch("scripts.fetch_news.fetch_all_rss", return_value=mock_articles[:1]), \
         patch("scripts.fetch_news.fetch_all_norwegian", return_value=mock_articles[1:]), \
         patch("scripts.fetch_news.DOCS_DIR", tmp_path):
        fetch_news.run()
    assert (tmp_path / "index.html").exists()
    assert (tmp_path / "data.json").exists()

def test_pipeline_exits_nonzero_when_no_articles(tmp_path):
    import pytest
    with patch("scripts.fetch_news.fetch_all_rss", return_value=[]), \
         patch("scripts.fetch_news.fetch_all_norwegian", return_value=[]), \
         patch("scripts.fetch_news.DOCS_DIR", tmp_path):
        with pytest.raises(SystemExit) as exc_info:
            fetch_news.run()
        assert exc_info.value.code == 1
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_fetch_news.py -v
```

- [ ] **Step 3: Implement `scripts/fetch_news.py`**

```python
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from scripts.rss_fetcher import fetch_all_rss
from scripts.scrapers import fetch_all_norwegian
from scripts.keywords import matches_keywords
from scripts.dedup import deduplicate
from scripts.sections import assign_and_organize
from scripts.renderer import render

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(message)s",
)

DOCS_DIR = Path(__file__).parent.parent / "docs"
REPO_URL = "https://github.com"  # Update after repo is created


def run() -> None:
    now = datetime.now(timezone.utc)

    # 1. Fetch
    articles = fetch_all_rss() + fetch_all_norwegian()
    logging.info("Fetched %d articles total", len(articles))

    # 2. Filter by keywords
    articles = [a for a in articles if matches_keywords(a)]
    logging.info("%d articles after keyword filter", len(articles))

    # 3. Deduplicate
    articles = deduplicate(articles)
    logging.info("%d articles after deduplication", len(articles))

    # 4. Assign sections, filter age, sort, cap
    sections = assign_and_organize(articles, now=now)
    total = sum(len(v) for v in sections.values())
    logging.info("Sections: nyheter=%d, regelverk=%d, rov_teknologi=%d",
                 len(sections["nyheter"]), len(sections["regelverk"]), len(sections["rov_teknologi"]))

    # 5. Guard: exit 1 if nothing to show
    if total == 0:
        logging.error("0 articles after all processing — aborting to preserve existing output")
        sys.exit(1)

    # 6. Render
    render(sections, docs_dir=DOCS_DIR, generated_at=now, repo_url=REPO_URL)
    logging.info("Dashboard written to %s", DOCS_DIR)


if __name__ == "__main__":
    run()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_fetch_news.py -v
```

- [ ] **Step 5: Run full test suite**

```bash
pytest tests/ -v
```
Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
git add scripts/fetch_news.py tests/test_fetch_news.py
git commit -m "feat: add main pipeline orchestrating fetch → filter → dedup → render"
```

---

## Task 10: Verify CSS Selectors Against Live Sites

**This task requires manual browser inspection — do not skip.**

- [ ] **Step 1: Open each Norwegian source in a browser and inspect article list HTML**

- `https://www.forsvaret.no/aktuelt`
- `https://www.kystverket.no/nyheter/`
- `https://www.sjofartsdir.no/nyheter/`

For each site: right-click an article card → Inspect → find the CSS selectors for: article container, title, link, intro/summary, date (`<time datetime="...">` or similar).

- [ ] **Step 2: Update selectors in `scripts/scrapers.py`**

Replace the `# TODO: Verify selector` lines in each scraper function with the actual CSS selectors observed.

- [ ] **Step 3: Update HTML fixtures in `tests/fixtures/`**

Update each fixture HTML to match the actual structure found, so tests reflect reality.

- [ ] **Step 4: Run scraper tests**

```bash
pytest tests/test_scrapers.py -v
```
Expected: All tests pass with real selectors.

- [ ] **Step 5: Run the script manually to verify live output**

```bash
python -m scripts.fetch_news
```
Expected: `docs/index.html` and `docs/data.json` created with real articles.

- [ ] **Step 6: Open `docs/index.html` in a browser and verify it looks correct**

- [ ] **Step 7: Commit**

```bash
git add scripts/scrapers.py tests/fixtures/
git commit -m "fix: update scrapers with verified CSS selectors from live sites"
```

---

## Task 11: GitHub Actions Workflow

**Files:**
- Create: `.github/workflows/update.yml`

- [ ] **Step 1: Create `.github/workflows/update.yml`**

```yaml
name: Update Dashboard

on:
  schedule:
    - cron: "0 4 * * *"   # 04:00 UTC = 06:00 CEST / 05:00 CET
    - cron: "0 12 * * *"  # 12:00 UTC = 14:00 CEST / 13:00 CET
  workflow_dispatch:       # Allow manual trigger from GitHub UI

jobs:
  update:
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run fetch script
        run: python -m scripts.fetch_news

      - name: Commit and push if changed
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add docs/index.html docs/data.json
          git diff --quiet --cached || git commit -m "chore: update dashboard $(date -u '+%Y-%m-%d %H:%M UTC')"
          git push
```

- [ ] **Step 2: Verify YAML syntax**

```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/update.yml'))" && echo "Valid YAML"
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/update.yml
git commit -m "ci: add GitHub Actions workflow for twice-daily dashboard update"
```

---

## Task 12: GitHub Repository Setup and Deploy

- [ ] **Step 1: Create a new public GitHub repository**

Go to https://github.com/new and create a repository named `maritim-sikkerhetsrapport` (or similar). Make it **public** (required for free GitHub Pages).

- [ ] **Step 2: Add the remote and push**

```bash
git remote add origin https://github.com/YOUR_USERNAME/maritim-sikkerhetsrapport.git
git push -u origin main
```

- [ ] **Step 3: Run the workflow manually to generate initial `docs/` output**

On GitHub: go to **Actions → Update Dashboard → Run workflow**. Wait for it to complete.

- [ ] **Step 4: Enable GitHub Pages**

On GitHub: go to **Settings → Pages → Source → Deploy from a branch → Branch: main / docs → Save**

- [ ] **Step 5: Update `REPO_URL` in `scripts/fetch_news.py`**

Replace the placeholder with the actual GitHub URL:
```python
REPO_URL = "https://github.com/YOUR_USERNAME/maritim-sikkerhetsrapport"
```

Then commit:
```bash
git add scripts/fetch_news.py
git commit -m "chore: set repo URL in renderer"
git push
```

- [ ] **Step 6: Verify the live URL**

Open `https://YOUR_USERNAME.github.io/maritim-sikkerhetsrapport/` in a browser.

Verify:
- Dashboard loads correctly
- Articles are visible in all three sections (or empty-state messages)
- Links open correct source articles
- "Sist oppdatert" timestamp is correct

- [ ] **Step 7: Share URL with employer**

The permanent URL `https://YOUR_USERNAME.github.io/maritim-sikkerhetsrapport/` can be bookmarked or shared directly.
