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
