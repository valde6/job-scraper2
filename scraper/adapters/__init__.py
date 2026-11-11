"""Register over adaptere: type (fra companies.yaml) → fetch(source: dict) -> list[RawJob].

Adaptere tilføjes her i senere opgaver, én pr. system (ikke pr. virksomhed)."""
from __future__ import annotations

from collections.abc import Callable

from scraper.model import RawJob

from scraper.adapters import (eightfold, hrmanager, jobylon, nordea, oracle, phenom, radancy_sitemap, strapi_zf,
                              successfactors)

ADAPTERS: dict[str, Callable[[dict], list[RawJob]]] = {
    "successfactors": successfactors.fetch,
    "phenom": phenom.fetch,
    "eightfold": eightfold.fetch,
    "nordea": nordea.fetch,
    "strapi_zf": strapi_zf.fetch,
    "radancy_sitemap": radancy_sitemap.fetch,
    "hrmanager": hrmanager.fetch,
    "oracle": oracle.fetch,
    "jobylon": jobylon.fetch,
}
