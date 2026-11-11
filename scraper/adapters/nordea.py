"""Nordea: eget JSON-API bag nordea.com/en/careers (se docs/KILDER.md).

Config: `url` = https://www.nordea.com/en/api/jobs-list
`GET {url}?_format=json&items_per_page=50&page={n}&search={ord}` pr. søgeord, side for side (fra 0) indtil en side med under 50.
`search` er en løs søgning (ikke kun titel); filtreringen på titlen sker i run.py. Opslagene ligger på careers.nordea.com
(`field_ad_url` er HTML-escaped to gange). `location_name` er en liste "Land, By, Land, By …" – countries_in() klarer den.
"""
from __future__ import annotations

import html

from scraper.common import clean, get
from scraper.match import settings
from scraper.model import RawJob

PAGE_SIZE = 50
MAX_PAGES = 10


def to_rawjob(p: dict) -> RawJob | None:
    url = html.unescape(html.unescape(p.get("field_ad_url") or ""))
    title = clean(html.unescape(p.get("title") or ""))
    if not url or not title:
        return None
    return RawJob(title=title, url=url, location=clean(html.unescape(p.get("location_name") or "")),
                  posted=p.get("created") or None, external_id=str(p.get("nid") or url))


def fetch(source: dict) -> list[RawJob]:
    api = source["url"]
    out: dict[str, RawJob] = {}
    for kw in (k["name"] for k in settings()["keywords"]):
        for page in range(MAX_PAGES):
            data = get(api, params={"_format": "json", "items_per_page": PAGE_SIZE, "page": page, "search": kw}).json()
            items = data.get("results") or []
            for p in items:
                job = to_rawjob(p)
                if job and job.external_id not in out:
                    out[job.external_id] = job
            if len(items) < PAGE_SIZE:
                break
    return list(out.values())
