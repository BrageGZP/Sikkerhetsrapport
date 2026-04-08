import re
from scripts.models import Article

KEYWORDS_NO = [
    "mine", "minerydding", "undervann", "rov", "havnesikkerhet",
    "maritim sikkerhet", "sjøforsvar", "ubåt", "mcm",
    "kongsberg", "minesveiper", "minejakting", "minekrig",
    "undervannsdroner", "autonomt undervannsfartøy",
    "marinen", "fregatt", "korvet", "sjøforsvar", "kystberedskap",
    "sjøvern", "forsvarsindustri",
    # Forsvarskontakter / anskaffelser
    "forsvarskontrakt", "forsvarsanskaffelse", "forsvarsdepartementet",
    "forsvarsmateriell", "militærkontrakt", "forsvarsbudsjett",
    "forsvarsinnkjøp", "militæranskaffelse", "rammeavtale forsvar",
]

KEYWORDS_EN = [
    # Specific mine/underwater terms
    "naval mine", "underwater rov", "mine countermeasure", "mcm",
    "uuv", "auv", "underwater security", "port security",
    "subsea defense", "rov defense",
    "mine hunting", "mine sweeping", "mine warfare", "minehunter",
    "sea mine", "minefield", "mine field",
    "underwater drone", "autonomous underwater vehicle",
    "unmanned underwater", "underwater warfare",
    # Broader naval/maritime terms (lets general defense news into nyheter)
    "navy", "naval", "submarine", "frigate", "destroyer", "corvette",
    "maritime", "coast guard", "amphibious", "warship", "seabed",
    "underwater threat", "naval exercise", "naval defense",
    "maritime patrol", "anti-submarine", "sonar",
    # Industry / competitor tracking
    "kongsberg maritime", "saab kockums", "eca group", "atlas elektronik",
    "teledyne marine", "hydroid", "remus", "double eagle", "seafox",
    "hugin", "l3harris", "thales underwater",
    "defense industry", "naval technology", "underwater technology",
    # Defence contracts & procurement
    "defense contract", "defence contract",
    "defense procurement", "defence procurement",
    "military contract", "naval contract", "shipbuilding contract",
    "arms deal", "weapons contract",
    "defense spending", "defence spending",
    "defense budget", "defence budget",
    "defense tender", "defence tender",
    "contract award", "awarded contract",
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
