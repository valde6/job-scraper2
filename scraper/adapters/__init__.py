"""Register over adaptere: type (fra companies.yaml) → fetch(source: dict) -> list[RawJob].

Adaptere tilføjes her i senere opgaver, én pr. system (ikke pr. virksomhed)."""
from __future__ import annotations

from collections.abc import Callable

from scraper.model import RawJob

ADAPTERS: dict[str, Callable[[dict], list[RawJob]]] = {}
