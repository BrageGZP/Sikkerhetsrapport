import logging
import requests
from datetime import datetime, timezone
from bs4 import BeautifulSoup, Tag
from scripts.models import Article

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; MaritimDashboard/1.0)"}
BASE_FORSVARET = "https://www.forsvaret.no"
BASE_KYSTVERKET = "https://www.kystverket.no"
BASE_SJOFARTSDIR = "https://www.sjofartsdir.no"


def _get_html(url: str) -> str | None:
    """Fetch URL, return HTML string or None on HTTP error."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return resp.text
    except requests.HTTPError as exc:
        logger.error("ERROR fetching %s: %s", url, exc)
        return None
    except requests.RequestException as exc:
        logger.error("ERROR fetching %s: %s", url, exc)
        return None


def _warn_if_empty(source: str, articles: list[Article]) -> list[Article]:
    if not articles:
        logger.warning(
            "WARNING: 0 articles scraped from %s — page structure may have changed",
            source,
        )
    return articles


def scrape_forsvaret() -> list[Article]:
    """Scrape news articles from https://www.forsvaret.no/aktuelt."""
    html = _get_html(f"{BASE_FORSVARET}/aktuelt")
    if html is None:
        return []

    soup = BeautifulSoup(html, "html.parser")
    articles = []

    for item in soup.select("article.article-list__item"):
        try:
            link = item.select_one("a.article-list__link")
            title = item.select_one(".article-list__title")
            intro = item.select_one(".article-list__intro")
            time_el = item.select_one("time[datetime]")

            if not link or not title:
                continue

            href = link.get("href", "")
            url = href if href.startswith("http") else f"{BASE_FORSVARET}{href}"
            published = _parse_datetime_attr(time_el)

            articles.append(Article(
                title=title.get_text(strip=True),
                url=url,
                published=published,
                source="Forsvaret.no",
                language="no",
                summary=intro.get_text(strip=True) if intro else "",
            ))
        except Exception as exc:
            logger.warning("Skipping malformed Forsvaret article: %s", exc)

    return _warn_if_empty("Forsvaret.no", articles)


def scrape_kystverket() -> list[Article]:
    """Scrape news articles from https://www.kystverket.no/nyheter/."""
    html = _get_html(f"{BASE_KYSTVERKET}/nyheter/")
    if html is None:
        return []

    soup = BeautifulSoup(html, "html.parser")
    articles = []

    for item in soup.select("li.news-list__item"):
        try:
            link = item.select_one("a")
            title_el = item.select_one(".news-list__title")
            summary_el = item.select_one(".news-list__intro")
            time_el = item.select_one("time[datetime]")

            if not link or not title_el:
                continue

            href = link.get("href", "")
            url = href if href.startswith("http") else f"{BASE_KYSTVERKET}{href}"

            articles.append(Article(
                title=title_el.get_text(strip=True),
                url=url,
                published=_parse_datetime_attr(time_el),
                source="Kystverket.no",
                language="no",
                summary=summary_el.get_text(strip=True) if summary_el else "",
            ))
        except Exception as exc:
            logger.warning("Skipping malformed Kystverket article: %s", exc)

    return _warn_if_empty("Kystverket.no", articles)


def scrape_sjofartsdir() -> list[Article]:
    """Scrape news articles from https://www.sjofartsdir.no/nyheter/."""
    html = _get_html(f"{BASE_SJOFARTSDIR}/nyheter/")
    if html is None:
        return []

    soup = BeautifulSoup(html, "html.parser")
    articles = []

    for item in soup.select("article.news-item"):
        try:
            link = item.select_one("a")
            title_el = item.select_one("h2")
            summary_el = item.select_one("p")
            time_el = item.select_one("time[datetime]")

            if not link or not title_el:
                continue

            href = link.get("href", "")
            url = href if href.startswith("http") else f"{BASE_SJOFARTSDIR}{href}"

            articles.append(Article(
                title=title_el.get_text(strip=True),
                url=url,
                published=_parse_datetime_attr(time_el),
                source="Sjøfartsdirektoratet.no",
                language="no",
                summary=summary_el.get_text(strip=True) if summary_el else "",
            ))
        except Exception as exc:
            logger.warning("Skipping malformed Sjøfartsdirektoratet article: %s", exc)

    return _warn_if_empty("Sjøfartsdirektoratet.no", articles)


def fetch_all_norwegian() -> list[Article]:
    """Fetch articles from all three Norwegian government sources."""
    articles = []
    for scraper in [scrape_forsvaret, scrape_kystverket, scrape_sjofartsdir]:
        articles.extend(scraper())
    return articles


def _parse_datetime_attr(time_el: Tag | None) -> datetime:
    """Parse ISO 8601 datetime from a BeautifulSoup time element's datetime attribute.
    Falls back to current UTC time if element is None or unparseable.
    """
    if time_el and time_el.get("datetime"):
        try:
            dt = datetime.fromisoformat(time_el["datetime"].replace("Z", "+00:00"))
            return dt.astimezone(timezone.utc)
        except ValueError:
            pass
    return datetime.now(timezone.utc)
