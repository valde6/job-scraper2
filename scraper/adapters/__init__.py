"""Register over adaptere: type (fra companies.yaml) → fetch(source: dict) -> list[RawJob].

Adaptere tilføjes her i senere opgaver, én pr. system (ikke pr. virksomhed)."""
from __future__ import annotations

from collections.abc import Callable

from scraper.model import RawJob

from scraper.adapters import eightfold, phenom, successfactors

ADAPTERS: dict[str, Callable[[dict], list[RawJob]]] = {
    "successfactors": successfactors.fetch,
    "phenom": phenom.fetch,
    "eightfold": eightfold.fetch,
}
