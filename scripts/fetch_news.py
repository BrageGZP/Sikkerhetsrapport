import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from scripts.rss_fetcher import fetch_all_rss
from scripts.scrapers import fetch_all_norwegian
from scripts.keywords import matches_keywords
from scripts.dedup import deduplicate
from scripts.sections import assign_and_organize, SECTION2_SOURCES
from scripts.renderer import render

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(message)s",
)

DOCS_DIR = Path(__file__).parent.parent / "docs"
REPO_URL = "https://github.com/BrageGZP/Sikkerhetsrapport"


def run() -> None:
    now = datetime.now(timezone.utc)

    # 1. Fetch
    articles = fetch_all_rss() + fetch_all_norwegian()
    logging.info("Fetched %d articles total", len(articles))

    # 2. Filter by keywords — regulatory sources (Kystverket, Sjøfartsdirektoratet)
    # are pre-selected as relevant and bypass the keyword filter
    articles = [a for a in articles if a.source in SECTION2_SOURCES or matches_keywords(a)]
    logging.info("%d articles after keyword filter", len(articles))

    # 3. Deduplicate
    articles = deduplicate(articles)
    logging.info("%d articles after deduplication", len(articles))

    # 4. Assign sections, filter age, sort, cap
    sections, fallback_sections = assign_and_organize(articles, now=now)
    total = sum(len(v) for v in sections.values())
    logging.info("Sections: nyheter=%d, regelverk=%d, rov_teknologi=%d",
                 len(sections["nyheter"]), len(sections["regelverk"]), len(sections["rov_teknologi"]))
    if fallback_sections:
        logging.info("Fallback (showing older articles) for: %s", ", ".join(sorted(fallback_sections)))

    # 5. Guard: exit 1 if nothing to show
    if total == 0:
        logging.error("0 articles after all processing — aborting to preserve existing output")
        sys.exit(1)

    # 6. Render
    render(sections, docs_dir=DOCS_DIR, generated_at=now, repo_url=REPO_URL,
           fallback_sections=fallback_sections)
    logging.info("Dashboard written to %s", DOCS_DIR)


if __name__ == "__main__":
    run()
