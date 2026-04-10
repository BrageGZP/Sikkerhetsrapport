import json
from datetime import datetime, timezone
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from scripts.models import Article

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
CRON_TIMES_UTC = ["04:00", "12:00"]


def _next_update(now: datetime) -> str:
    current_hhmm = now.strftime("%H:%M")
    for t in CRON_TIMES_UTC:
        if current_hhmm < t:
            return f"{t} UTC"
    return f"{CRON_TIMES_UTC[0]} UTC (tomorrow)"


def render(
    sections: dict[str, list[Article]],
    docs_dir: Path,
    generated_at: datetime | None = None,
    repo_url: str = "https://github.com",
    fallback_sections: set[str] | None = None,
) -> None:
    if generated_at is None:
        generated_at = datetime.now(timezone.utc)
    if fallback_sections is None:
        fallback_sections = set()

    docs_dir.mkdir(parents=True, exist_ok=True)

    def fmt_article(a: Article) -> dict:
        d = a.to_dict()
        d["published"] = a.published.strftime("%d.%m.%Y %H:%M UTC")
        d["url"] = a.url
        d["image_url"] = a.image_url
        return d

    template_sections = {
        name: [fmt_article(a) for a in items]
        for name, items in sections.items()
    }

    # Build namespace for template dot-access
    class Ns:
        pass

    ns = Ns()
    for k, v in template_sections.items():
        setattr(ns, k, [_DotDict(d) for d in v])

    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)
    tmpl = env.get_template("index.html.j2")

    html = tmpl.render(
        generated_at=generated_at.strftime("%Y-%m-%d %H:%M"),
        next_update_utc=_next_update(generated_at),
        sections=ns,
        repo_url=repo_url,
        fallback_sections=fallback_sections,
    )

    (docs_dir / "index.html").write_text(html, encoding="utf-8")

    # Write data.json
    data = {
        "generated_at": generated_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "next_update_utc": _next_update(generated_at),
        "sections": {
            name: [a.to_dict() for a in items]
            for name, items in sections.items()
        },
    }
    (docs_dir / "data.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


class _DotDict:
    """Simple dot-access wrapper for Jinja2 template rendering."""
    def __init__(self, d: dict):
        self.__dict__.update(d)
