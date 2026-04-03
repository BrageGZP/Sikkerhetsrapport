from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Article:
    title: str
    url: str
    published: datetime
    source: str
    language: str  # "no" or "en"
    summary: str
    section: Optional[str] = field(default=None)  # "nyheter", "regelverk", "rov_teknologi"

    def to_dict(self) -> dict:
        d = {
            "title": self.title,
            "url": self.url,
            "published": self.published.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source": self.source,
            "language": self.language,
            "summary": self.summary,
        }
        if self.section is not None:
            d["section"] = self.section
        return d
