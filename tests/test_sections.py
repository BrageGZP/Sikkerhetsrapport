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
