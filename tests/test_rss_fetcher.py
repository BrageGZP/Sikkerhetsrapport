import pytest
import feedparser
from unittest.mock import patch, MagicMock
from pathlib import Path
from scripts.rss_fetcher import fetch_rss

FIXTURE = Path(__file__).parent / "fixtures" / "sample_rss.xml"


def _make_feed(xml_text):
    return feedparser.parse(xml_text)


def test_fetch_rss_returns_articles():
    feed = _make_feed(FIXTURE.read_text())
    with patch("scripts.rss_fetcher.feedparser.parse", return_value=feed):
        articles = fetch_rss("https://news.usni.org/feed", source="USNI News")
    assert len(articles) == 2
    assert articles[0].title == "Navy tests new mine countermeasure UUV"
    assert articles[0].language == "en"
    assert articles[0].source == "USNI News"


def test_fetch_rss_returns_empty_on_http_error(caplog):
    mock_feed = MagicMock()
    mock_feed.bozo = False
    mock_feed.status = 503
    mock_feed.entries = []
    with patch("scripts.rss_fetcher.feedparser.parse", return_value=mock_feed):
        with caplog.at_level("ERROR"):
            articles = fetch_rss("https://news.usni.org/feed", source="USNI News")
    assert articles == []
    assert "ERROR" in caplog.text or "503" in caplog.text
