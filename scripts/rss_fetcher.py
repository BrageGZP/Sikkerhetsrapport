import logging
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


def fetch_rss(url: str, source: str) -> list[Article]:
    """Fetch and parse a single RSS feed. Returns empty list on any error."""
    try:
        feed = feedparser.parse(url)
        if feed.bozo and feed.bozo_exception:
            raise feed.bozo_exception
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
    # Strip HTML tags if present
    import re
    return re.sub(r"<[^>]+>", "", summary).strip()[:500]
