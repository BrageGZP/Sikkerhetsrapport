import re
from scripts.models import Article

KEYWORDS_NO = [
    "mine", "minerydding", "undervann", "rov", "havnesikkerhet",
    "maritim sikkerhet", "sjøforsvar", "ubåt", "mcm",
]

KEYWORDS_EN = [
    "naval mine", "underwater rov", "mine countermeasure", "mcm",
    "uuv", "auv", "underwater security", "port security",
    "subsea defense", "rov defense",
]

ALL_KEYWORDS = KEYWORDS_NO + KEYWORDS_EN

# Build word-boundary patterns for single-word keywords;
# multi-word phrases use simple substring match (already specific enough)
_PATTERNS = [
    re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE)
    if " " not in kw
    else re.compile(re.escape(kw), re.IGNORECASE)
    for kw in ALL_KEYWORDS
]


def matches_keywords(article: Article) -> bool:
    """Return True if article title or summary contains at least one keyword."""
    text = f"{article.title} {article.summary}"
    return any(p.search(text) for p in _PATTERNS)
