"""ZF Lifetec: Strapi-API bag Nuxt-siden careers.zf-lifetec.com (se docs/KILDER.md).

Config: `url` = https://careers-strapi.zf-lifetec.com/api/jobs   `job_base` = https://careers.zf-lifetec.com/jobs

Ét kald (side for side) med `$containsi`-filtre på Title for alle søgeord, `populate[0]=Countries`, `pagination[pageSize]=100`.
`locale=all` er afprøvet 11/11-2026 og giver 0 opslag (også uden filtre); standardsproget (en) bruges, de øvrige sprog (de, zh) gav 0.
Strapi/robots: robots.txt findes ikke (404 = tilladt).
"""
from __future__ import annotations

from scraper.common import clean, get
from scraper.match import countries_in, settings
from scraper.model import RawJob

PAGE_SIZE = 100
MAX_PAGES = 10


def to_rawjob(job_base: str, item: dict) -> RawJob | None:
    title, slug = clean(item.get("Title")), item.get("Slug")
    if not title or not slug:
        return None
    countries = [clean(c.get("Title")) for c in item.get("Countries") or [] if isinstance(c, dict) and c.get("Title")]
    city = clean(item.get("City"))
    location = ", ".join(x for x in (city, countries[0] if countries else "") if x)
    return RawJob(title=title, url=f"{job_base}/{slug}", location=location,
                  countries=countries_in(", ".join(countries)), posted=item.get("publishedAt") or None,
                  external_id=str(item.get("SapID") or item.get("id") or slug))


def fetch(source: dict) -> list[RawJob]:
    api, job_base = source["url"], source["job_base"].rstrip("/")
    params: dict = {"pagination[pageSize]": PAGE_SIZE, "populate[0]": "Countries"}
    for i, k in enumerate(k["name"] for k in settings()["keywords"]):
        params[f"filters[$or][{i}][Title][$containsi]"] = k
    out: dict[str, RawJob] = {}
    for page in range(1, MAX_PAGES + 1):
        data = get(api, params={**params, "pagination[page]": page}).json()
        for item in data.get("data") or []:
            job = to_rawjob(job_base, item)
            if job and job.url not in out:
                out[job.url] = job
        if page >= ((data.get("meta") or {}).get("pagination") or {}).get("pageCount", 0):
            break
    return list(out.values())
