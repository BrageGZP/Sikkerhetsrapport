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
