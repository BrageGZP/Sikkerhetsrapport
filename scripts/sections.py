from datetime import datetime, timezone, timedelta
from scripts.models import Article

SECTION2_SOURCES = {"Kystverket.no", "Sjøfartsdirektoratet.no"}

SECTION3_KEYWORDS = [
    "rov", "uuv", "auv", "mine countermeasure", "mcm",
    "minerydding", "undervann",
]

MAX_AGE = {
    "nyheter": 30,
    "regelverk": 90,
    "rov_teknologi": 30,
}

MAX_COUNT = 10


def _matches_section3(article: Article) -> bool:
    text = f"{article.title} {article.summary}".lower()
    return any(kw in text for kw in SECTION3_KEYWORDS)


def assign_and_organize(
    articles: list[Article],
    now: datetime | None = None,
) -> dict[str, list[Article]]:
    if now is None:
        now = datetime.now(timezone.utc)

    sections: dict[str, list[Article]] = {
        "nyheter": [],
        "regelverk": [],
        "rov_teknologi": [],
    }

    for article in articles:
        # Assign section (priority: regelverk > rov_teknologi > nyheter)
        if article.source in SECTION2_SOURCES:
            article.section = "regelverk"
        elif _matches_section3(article):
            article.section = "rov_teknologi"
        else:
            article.section = "nyheter"
        sections[article.section].append(article)

    # Per-section: filter by age, sort newest first, cap at MAX_COUNT
    for name, items in sections.items():
        cutoff = now - timedelta(days=MAX_AGE[name])
        items = [a for a in items if a.published >= cutoff]
        items.sort(key=lambda a: a.published, reverse=True)
        sections[name] = items[:MAX_COUNT]

    return sections
