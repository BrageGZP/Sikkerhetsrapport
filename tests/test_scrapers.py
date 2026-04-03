import responses as responses_mock
from scripts.scrapers import scrape_forsvaret, scrape_kystverket, scrape_sjofartsdir
from scripts.scrapers import FORSVARET_API
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"

FORSVARET_JSON = {
    "total": 2,
    "start": 0,
    "hits": [
        {
            "title": "Ny øvelse fokuserer på minerydding",
            "displayName": "Ny øvelse fokuserer på minerydding",
            "url": "/aktuelt-og-presse/aktuelt/ny-oevelse-minerydding",
            "type": "no.bouvet.forsvaret:news",
        },
        {
            "title": "Forsvaret styrker beredskapen",
            "displayName": "Forsvaret styrker beredskapen",
            "url": "/aktuelt-og-presse/aktuelt/styrker-beredskapen",
            "type": "no.bouvet.forsvaret:news",
        },
    ],
}

ARTICLE_HTML = """<html><head>
<meta property="og:description" content="Ny øvelse tester minerydding i Oslofjorden.">
</head><body></body></html>"""

@responses_mock.activate
def test_scrape_forsvaret_returns_articles():
    responses_mock.add(responses_mock.GET, FORSVARET_API, json=FORSVARET_JSON)
    # Mock individual article page requests for ingress fetching
    responses_mock.add(
        responses_mock.GET,
        "https://www.forsvaret.no/aktuelt-og-presse/aktuelt/ny-oevelse-minerydding",
        body=ARTICLE_HTML.encode("utf-8"), content_type="text/html; charset=utf-8",
    )
    responses_mock.add(
        responses_mock.GET,
        "https://www.forsvaret.no/aktuelt-og-presse/aktuelt/styrker-beredskapen",
        body=ARTICLE_HTML.encode("utf-8"), content_type="text/html; charset=utf-8",
    )
    articles = scrape_forsvaret()
    assert len(articles) >= 1
    assert articles[0].source == "Forsvaret.no"
    assert articles[0].language == "no"
    assert articles[0].url.startswith("https://www.forsvaret.no")
    assert articles[0].summary == "Ny øvelse tester minerydding i Oslofjorden."

@responses_mock.activate
def test_scrape_forsvaret_returns_empty_on_http_error(caplog):
    responses_mock.add(
        responses_mock.GET,
        FORSVARET_API,
        status=404,
    )
    articles = scrape_forsvaret()
    assert articles == []
    assert "ERROR" in caplog.text or "404" in caplog.text

@responses_mock.activate
def test_scrape_forsvaret_warns_on_zero_results(caplog):
    responses_mock.add(
        responses_mock.GET,
        FORSVARET_API,
        json={"total": 0, "start": 0, "hits": []},
    )
    articles = scrape_forsvaret()
    assert articles == []
    assert "0 articles" in caplog.text
