"""Oracle Recruiting Cloud (HCM Candidate Experience) – KPMG Finland (se docs/KILDER.md).

Config: `url` = https://iabdgs.fa.ocs.oraclecloud.com   `site` = CX_1002
`GET {url}/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true&expand=requisitionList.secondaryLocations
 &finder=findReqs;siteNumber={site},keyword={ord},limit=25,offset={n},sortBy=POSTING_DATES_DESC` pr. søgeord, side for side.
Opslag: `{url}/hcmUI/CandidateExperience/en/sites/{site}/job/{Id}`. Filtreringen på titlen sker i run.py.
robots.txt findes ikke (404 = tilladt).
"""
from __future__ import annotations

from scraper.common import clean, get
from scraper.match import countries_in, settings
from scraper.model import RawJob

LIMIT = 25
MAX_OFFSET = 300


def to_rawjob(base: str, site: str, p: dict) -> RawJob | None:
    title, rid = clean(p.get("Title")), p.get("Id")
    if not title or not rid:
        return None
    primary = clean(p.get("PrimaryLocation"))
    names = [primary] + [clean(s.get("Name")) for s in p.get("secondaryLocations") or [] if isinstance(s, dict)]
    location = " | ".join(dict.fromkeys(n for n in names if n))
    code = clean(p.get("PrimaryLocationCountry")).upper()
    countries = list(dict.fromkeys(([code] if code else []) + countries_in(location)))
    return RawJob(title=title, url=f"{base}/hcmUI/CandidateExperience/en/sites/{site}/job/{rid}", location=location,
                  countries=countries, posted=p.get("PostedDate") or None, external_id=str(rid))


def fetch(source: dict) -> list[RawJob]:
    base, site = source["url"].rstrip("/"), source["site"]
    api = f"{base}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
    out: dict[str, RawJob] = {}
    for kw in (k["name"] for k in settings()["keywords"]):
        offset = 0
        while offset < MAX_OFFSET:
            finder = f"findReqs;siteNumber={site},keyword={kw},limit={LIMIT},offset={offset},sortBy=POSTING_DATES_DESC"
            data = get(api, params={"onlyData": "true", "expand": "requisitionList.secondaryLocations", "finder": finder}).json()
            block = (data.get("items") or [{}])[0]
            items = block.get("requisitionList") or []
            for p in items:
                job = to_rawjob(base, site, p)
                if job and job.external_id not in out:
                    out[job.external_id] = job
            offset += len(items)
            if len(items) < LIMIT or offset >= (block.get("TotalJobsCount") or 0):
                break
    return list(out.values())
