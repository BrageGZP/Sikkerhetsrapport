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

# Forsvaret.no changed to dynamic loading — articles are served via JSON API
FORSVARET_API = (
    "https://www.forsvaret.no/aktuelt-og-presse/aktuelt/_/service/"
    "no.bouvet.forsvaret/list-card-service?hasFilters=true&contentTypes=news%2Cfeature"
)


def _get_html(url: str, verify: bool = True) -> str | None:
    """Fetch URL, return HTML string or None on HTTP error."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15, verify=verify)
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


def _og_image(soup: BeautifulSoup) -> str:
    """Extract og:image URL from a BeautifulSoup page, or empty string."""
    meta = soup.find("meta", {"property": "og:image"})
    if meta and meta.get("content"):
        return meta["content"].strip()
    return ""


def _fetch_forsvaret_article(url: str) -> tuple[str, datetime | None, str]:
    """Fetch a Forsvaret.no article page.

    Returns (ingress, published_date, image_url).
    Date is parsed from JSON-LD datePublished; falls back to None if not found.
    """
    import json as _json
    html = _get_html(url)
    if not html:
        return "", None, ""
    soup = BeautifulSoup(html, "html.parser")

    # Ingress from og:description
    ingress = ""
    meta = soup.find("meta", {"property": "og:description"})
    if meta and meta.get("content"):
        ingress = meta["content"].strip()

    # Image
    image_url = _og_image(soup)

    # Date from JSON-LD
    published: datetime | None = None
    for script in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = _json.loads(script.string or "")
            raw = data.get("datePublished") or data.get("dateModified")
            if raw:
                raw = raw.strip().replace(" ", "T").replace("Z", "+00:00")
                if "T" not in raw:
                    raw += "T00:00:00+00:00"
                dt = datetime.fromisoformat(raw)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                published = dt.astimezone(timezone.utc)
                break
        except Exception:
            continue

    return ingress, published, image_url


def scrape_forsvaret() -> list[Article]:
    """Fetch news articles from Forsvaret.no via JSON API.

    The site changed to dynamic loading (2026-04-03); articles are no longer
    present in the static HTML but served from a list-card-service endpoint.
    Ingress is fetched from each article's og:description meta tag.
    """
    try:
        resp = requests.get(FORSVARET_API, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        logger.error("ERROR fetching Forsvaret.no API: %s", exc)
        return []
    except ValueError as exc:
        logger.error("ERROR parsing Forsvaret.no JSON: %s", exc)
        return []

    articles = []
    for hit in data.get("hits", []):
        try:
            title = hit.get("title") or hit.get("displayName", "")
            href = hit.get("url", "")
            if not title or not href:
                continue
            url = href if href.startswith("http") else f"{BASE_FORSVARET}{href}"
            ingress, published, image_url = _fetch_forsvaret_article(url)
            articles.append(Article(
                title=title,
                url=url,
                published=published or _parse_forsvaret_date(hit),
                source="Forsvaret.no",
                language="no",
                summary=ingress,
                image_url=image_url,
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

    # Selector verified 2026-04-03: article.card > a.card__headline-link + div.card__content > p + span.card__pubdate > time
    for item in soup.select("article.card"):
        try:
            link = item.select_one("a.card__headline-link")
            summary_el = item.select_one(".card__content p")
            time_el = item.select_one(".card__pubdate time[datetime]")

            if not link:
                continue

            href = link.get("href", "")
            url = href if href.startswith("http") else f"{BASE_KYSTVERKET}{href}"

            articles.append(Article(
                title=link.get_text(strip=True),
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
    # verify=False: sjofartsdir.no has an SSL handshake issue on GitHub Actions runners
    html = _get_html(f"{BASE_SJOFARTSDIR}/nyheter/", verify=False)
    if html is None:
        return []

    soup = BeautifulSoup(html, "html.parser")
    articles = []

    # Selector verified 2026-04-03: li.listing__listitem > div.teaser > div.teaser__content-wrap
    for item in soup.select("li.listing__listitem"):
        try:
            content = item.select_one(".teaser__content-wrap")
            if not content:
                continue

            link = content.select_one("a")
            title_el = content.select_one("h2.teaser__heading")
            time_el = content.select_one("time[datetime]")
            summary_el = content.select_one("p.teaser__ingress")

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


def _parse_forsvaret_date(hit: dict) -> datetime:
    """Try common date field names from Forsvaret JSON API; fall back to now."""
    for field in ("publishedDate", "published", "date", "updatedDate", "lastModified", "created"):
        raw = hit.get(field)
        if raw and isinstance(raw, str):
            raw = raw.strip().replace(" ", "T").replace("Z", "+00:00")
            try:
                dt = datetime.fromisoformat(raw)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except ValueError:
                continue
    logger.debug("No parseable date in Forsvaret hit: %s", list(hit.keys()))
    return datetime.now(timezone.utc)


def _parse_datetime_attr(time_el: Tag | None) -> datetime:
    """Parse datetime from a BeautifulSoup time element's datetime attribute.

    Handles ISO 8601 with T or space separator, date-only strings (YYYY-MM-DD),
    and Z suffix. Falls back to current UTC time if element is None or unparseable.
    """
    if time_el and time_el.get("datetime"):
        raw = time_el["datetime"].strip()
        # Normalize: space separator → T, Z suffix → +00:00
        raw = raw.replace(" ", "T").replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(raw)
            # If date-only (naive datetime with no time component), treat as UTC midnight
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            pass
    return datetime.now(timezone.utc)
