import logging
import ssl
import urllib.request
import feedparser
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from scripts.models import Article

logger = logging.getLogger(__name__)

RSS_SOURCES = [
    ("https://news.usni.org/feed", "USNI News"),
    ("https://www.defensenews.com/arc/outboundfeeds/rss/", "Defense News"),
    ("https://www.navalnews.com/feed/", "Naval News"),
    ("https://breakingdefense.com/feed/", "Breaking Defense"),
    ("https://maritime-executive.com/rss/articles", "The Maritime Executive"),
    ("https://www.clariondefence.com/feed/", "Clarion Defence"),  # TODO: verify RSS URL
]


def _fetch_feed(url: str) -> feedparser.FeedParserDict:
    """Fetch RSS feed, falling back to SSL-unverified on certificate errors."""
    feed = feedparser.parse(url)
    if feed.bozo and isinstance(feed.bozo_exception, Exception):
        exc_str = str(feed.bozo_exception).lower()
        if "ssl" in exc_str or "certificate" in exc_str:
            # SSL issue — retry without verification
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            handler = urllib.request.HTTPSHandler(context=ctx)
            feed = feedparser.parse(url, handlers=[handler])
    return feed


def fetch_rss(url: str, source: str) -> list[Article]:
    """Fetch and parse a single RSS feed. Returns empty list on any error."""
    try:
        feed = _fetch_feed(url)
        # Bozo just means malformed XML — still try to use entries if present
        if feed.bozo and not feed.entries:
            logger.error("ERROR fetching RSS %s: %s", url, feed.bozo_exception)
            return []
        if getattr(feed, "status", 200) >= 400:
            raise ValueError(f"HTTP {feed.status}")
    except Exception as exc:
        logger.error("ERROR fetching RSS %s: %s", url, exc)
        return []

    articles = []
    for entry in feed.entries:
        try:
            published = _parse_date(entry)
            articles.append(Article(
                title=entry.get("title", "").strip(),
                url=entry.get("link", "").strip(),
                published=published,
                source=source,
                language="en",
                summary=_get_summary(entry),
                image_url=_get_image(entry),
            ))
        except Exception as exc:
            logger.warning("Skipping malformed RSS entry from %s: %s", source, exc)

    return articles


def fetch_all_rss() -> list[Article]:
    articles = []
    for url, source in RSS_SOURCES:
        articles.extend(fetch_rss(url, source))
    return articles


def _parse_date(entry) -> datetime:
    raw = entry.get("published") or entry.get("updated", "")
    if raw:
        try:
            return parsedate_to_datetime(raw).astimezone(timezone.utc)
        except Exception:
            pass
    return datetime.now(timezone.utc)


def _get_summary(entry) -> str:
    summary = entry.get("summary") or entry.get("description") or ""
    import re
    return re.sub(r"<[^>]+>", "", summary).strip()[:500]


def _get_image(entry) -> str:
    """Extract the best available image URL from an RSS entry."""
    # media:content (most common in defence/news feeds)
    for m in entry.get("media_content", []):
        url = m.get("url", "")
        if url:
            return url
    # media:thumbnail
    for m in entry.get("media_thumbnail", []):
        url = m.get("url", "")
        if url:
            return url
    # enclosures (image/*)
    for enc in entry.get("enclosures", []):
        if enc.get("type", "").startswith("image"):
            return enc.get("href") or enc.get("url", "")
    # og:image embedded in summary/content HTML
    import re
    html = entry.get("content", [{}])[0].get("value", "") if entry.get("content") else ""
    if not html:
        html = entry.get("summary", "")
    m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', html)
    if m:
        return m.group(1)
    return ""
