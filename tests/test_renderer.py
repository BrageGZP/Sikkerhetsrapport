import json
from pathlib import Path
from datetime import datetime, timezone
from scripts.models import Article
from scripts.renderer import render

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
