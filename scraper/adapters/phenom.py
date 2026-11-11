"""Phenom People karrieresider – Ricoh Europe og Givaudan (se docs/KILDER.md).

Config: `url` = sidens rod inkl. sprogsti, fx https://careersatricoh.com/gb/en  (Givaudan: https://careers.givaudan.com/global/en –
        robots.txt forbyder */gb/en, */apply og */px-widgets, dem bruges ikke).

For hvert søgeord: `GET {url}/search-results?keywords={ord}&from={n}&s=1`. Siden indeholder `phApp.ddo = {...}` med
`eagerLoadRefineSearch.totalHits` og `.data.jobs[]`. Phenoms søgning er løs og kan give opslag uden ordet i titlen;
det afgør run.py (AGENTS.md regel 4).

Målt 11/11-2026: `keywords=` filtrerer slet ikke (Ricoh 119 og Givaudan 336 hits uanset ord, også for "zzzqqq"), så hele listen
gennemløbes side for side. Svarer et nyt søgeord med præcis samme første side som det forrige, springes resten af ordene over,
så vi ikke henter den samme liste igen; filtrerer serveren en dag, gennemløbes hvert ord for sig.
"""
from __future__ import annotations

import json
import re
from urllib.parse import quote

from scraper.common import clean, get
from scraper.match import countries_in, settings
from scraper.model import RawJob

MAX_HITS = 1000         # loft pr. søgeord (≈ 100 sider à 10; Givaudan har ca. 340 opslag)


def _ddo(html: str) -> dict:
    """JSON-objektet efter `phApp.ddo =` – tomt, hvis det ikke findes eller ikke kan læses."""
    m = re.search(r"phApp\.ddo\s*=\s*", html)
    if not m:
        return {}
    try:
        obj, _ = json.JSONDecoder().raw_decode(html[m.end():])
    except ValueError:
        return {}
    return obj if isinstance(obj, dict) else {}


def to_rawjob(base: str, p: dict) -> RawJob | None:
    jid = p.get("jobId") or p.get("jobSeqNo")
    title = clean(p.get("title"))
    if not jid or not title:
        return None
    city, country = clean(p.get("city")), clean(p.get("country"))
    location = ", ".join(x for x in (city, country) if x)
    where = " | ".join([location, *[clean(x) for x in (p.get("multi_location") or []) if isinstance(x, str)]])
    return RawJob(title=title, url=f"{base}/job/{jid}", location=location, countries=countries_in(where),
                  posted=p.get("postedDate") or None, external_id=str(jid))


def fetch(source: dict) -> list[RawJob]:
    base = source["url"].rstrip("/")
    out: dict[str, RawJob] = {}
    first_page: list | None = None
    for kw in (k["name"] for k in settings()["keywords"]):
        start = 0
        while start < MAX_HITS:
            res = _ddo(get(f"{base}/search-results?keywords={quote(kw)}&from={start}&s=1").text).get("eagerLoadRefineSearch") or {}
            items = (res.get("data") or {}).get("jobs") or []
            if start == 0:
                ids = [p.get("jobId") for p in items]
                if first_page is not None and ids == first_page:
                    break                      # ordet filtrerer ikke – listen er allerede hentet
                first_page = ids
            for p in items:
                job = to_rawjob(base, p)
                if job and job.external_id not in out:
                    out[job.external_id] = job
            start += len(items)
            if not items or start >= (res.get("totalHits") or 0):
                break
    return list(out.values())
