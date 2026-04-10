from datetime import datetime, timezone, timedelta
from scripts.models import Article

SECTION2_SOURCES = {"Kystverket.no", "Sjøfartsdirektoratet.no"}
# Kystverket and Sjøfartsdirektoratet bypass keyword filter (regulatory sources).
# Forsvaret.no is intentionally excluded — it publishes too many irrelevant articles
# (HR, education, sports) and must pass the keyword filter like any other source.
NORWEGIAN_SOURCES = {"Kystverket.no", "Sjøfartsdirektoratet.no"}

SECTION3_KEYWORDS = [
    # ROV / UUV / AUV
    "rov", "uuv", "auv",
    "remotely operated vehicle", "autonomous underwater vehicle",
    "unmanned underwater", "underwater drone", "undervannsdroner",
    "undervanns", "undervann",
    # Mine warfare
    "mine countermeasure", "mcm", "minehunter", "mine hunting", "mine sweeping",
    "minesweeper", "minesveiper", "minejakting", "minerydding", "minekrig",
    "naval mine", "sea mine", "seafox", "double eagle",
    # Underwater sensors / systems
    "sonar", "anti-submarine", "subsea", "seabed", "underwater warfare",
    "hugin", "remus", "hydroid",
    # Broader underwater tech
    "underwater technology", "naval technology", "underwater security",
]

MAX_AGE = {
    "nyheter": 7,
    "regelverk": 60,
    "rov_teknologi": 7,
}

MAX_COUNT = 30


def _matches_section3(article: Article) -> bool:
    text = f"{article.title} {article.summary}".lower()
    return any(kw in text for kw in SECTION3_KEYWORDS)


def assign_and_organize(
    articles: list[Article],
    now: datetime | None = None,
) -> tuple[dict[str, list[Article]], set[str]]:
    """Return (sections, fallback_sections) where fallback_sections is the set
    of section names that fell back to older articles due to no recent content."""
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
    # If nothing passes the age filter, fall back to the most recent articles available
    fallback_sections: set[str] = set()
    for name, items in sections.items():
        cutoff = now - timedelta(days=MAX_AGE[name])
        recent = [a for a in items if a.published >= cutoff]
        if recent:
            pool = recent
        elif items:
            pool = items
            fallback_sections.add(name)
        else:
            pool = []
        pool.sort(key=lambda a: a.published, reverse=True)
        sections[name] = pool[:MAX_COUNT]

    return sections, fallback_sections
