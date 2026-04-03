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
