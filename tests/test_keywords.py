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
