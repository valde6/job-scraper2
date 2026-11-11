"""Eightfold PCS – Ericsson (se docs/KILDER.md).

Config: `url` = https://jobs.ericsson.com, `domain` = ericsson.com
robots.txt forbyder alt undtagen bl.a. /careers og /api/pcsx: der bruges KUN `/api/pcsx/search` (robots_allows() tjekkes af get()).
"""
from __future__ import annotations

from scraper.common import clean, get
from scraper.match import countries_in, settings
from scraper.model import RawJob

MAX_HITS = 300          # loft pr. søgeord


def _country_code(standardized: str) -> str:
    """Landekoden sidst i `"Bucharest, Bucharest, RO"` (`"Jakarta,ID"` virker også)."""
    return clean(standardized.rsplit(",", 1)[-1]).upper()


def to_rawjob(base: str, p: dict) -> RawJob | None:
    title, pid = clean(p.get("name")), p.get("id")
    if not title or not pid:
        return None
    std = [clean(x) for x in (p.get("standardizedLocations") or []) if isinstance(x, str)]
    location = " | ".join(dict.fromkeys(std)) or " | ".join(clean(x) for x in (p.get("locations") or []) if isinstance(x, str))
    codes = [c for c in dict.fromkeys(_country_code(x) for x in std) if len(c) == 2]
    # ukendte koder (US, ID …) ignoreres af run.py; "UK" tolkes dér som GB
    return RawJob(title=title, url=f"{base}/careers/job/{pid}", location=location,
                  countries=codes or countries_in(location), posted=p.get("postedTs"), external_id=str(pid))


def fetch(source: dict) -> list[RawJob]:
    base, domain = source["url"].rstrip("/"), source["domain"]
    out: dict[str, RawJob] = {}
    for kw in (k["name"] for k in settings()["keywords"]):
        start = 0
        while start < MAX_HITS:
            data = get(f"{base}/api/pcsx/search", params={"domain": domain, "query": kw, "location": "", "start": start,
                                                          "sort_by": "timestamp"}).json()
            items = (data.get("data") or {}).get("positions") or []
            for p in items:
                job = to_rawjob(base, p)
                if job and job.external_id not in out:
                    out[job.external_id] = job
            start += len(items)
            if not items or start >= ((data.get("data") or {}).get("count") or 0):
                break
    return list(out.values())
