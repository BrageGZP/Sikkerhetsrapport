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
