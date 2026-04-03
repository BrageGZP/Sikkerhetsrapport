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
