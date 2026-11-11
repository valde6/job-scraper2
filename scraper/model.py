"""Det, en adapter leverer: ét opslag, som kilden skriver det. Filtrering og id'er sker i run.py."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RawJob:
    title: str
    url: str
    location: str = ""
    countries: list[str] = field(default_factory=list)   # tom = afgøres af match.countries_in(location)
    posted: str | None = None                            # kildens dato i en vilkårlig form; run.py kører parse_date
    external_id: str | None = None
