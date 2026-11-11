"""HR-Manager (Talentech) – KPMG Danmark (se docs/KILDER.md).

Config: `customer` = kundenavnet i API'et (KPMG: `kpmg`).
`GET https://api.hr-manager.net/jobportal.svc/{customer}/positionlist/json/?incads=1&take=200&skip=…` giver alle kundens opslag
(uden `take` kun 25), så alle sider hentes. Der søges ikke på ord – filtreringen på titlen sker i run.py.
Land: `Department.Country` / `DepartmentTree.Country` ("Danmark"), hvis stedet ikke selv nævner et.
"""
from __future__ import annotations

import re

from scraper.common import clean, get
from scraper.model import RawJob

API = "https://api.hr-manager.net/jobportal.svc/{customer}/positionlist/json/"
PAGE = 200
MAX_PAGES = 15


def _date_ms(value) -> int | None:
    """`/Date(1793354171000+0100)/` → millisekunder siden 1970 (parse_date forstår dem)."""
    m = re.search(r"/Date\((-?\d+)", str(value or ""))
    return int(m.group(1)) if m and int(m.group(1)) > 0 else None


def _title(p: dict) -> str:
    for k in ("Name", "Title", "PositionTitle", "JobTitle", "Headline"):
        if isinstance(p.get(k), str) and p[k].strip():
            return clean(p[k])
    adv = (p.get("Advertisements") or [{}])[0]
    return clean(adv.get("Title") or adv.get("Name") or "")


def _country(p: dict) -> str:
    for k in ("Department", "DepartmentTree"):
        node = p.get(k)
        if isinstance(node, dict) and clean(node.get("Country")):
            return clean(node["Country"])
    return ""


def _place(p: dict) -> str:
    loc = p.get("PositionLocation")
    parts = [clean(loc["Name"])] if isinstance(loc, dict) and loc.get("Name") else []
    if p.get("WorkPlace"):
        parts.append(clean(str(p["WorkPlace"])))
    if not parts and isinstance(p.get("Department"), dict):
        parts.append(clean(p["Department"].get("City")))
    return ", ".join(x for x in parts if x)


def to_rawjob(p: dict) -> RawJob | None:
    title = _title(p)
    url = p.get("AdvertisementUrlSecure") or p.get("AdvertisementUrl") or (
        f"https://candidate.hr-manager.net/ApplicationInit.aspx?cid={p.get('CustomerId', '')}&ProjectId={p.get('Id')}" if p.get("Id") else "")
    if not title or not url:
        return None
    place, country = _place(p), _country(p)
    return RawJob(title=title, url=url, location=", ".join(x for x in (place, country) if x),
                  posted=_date_ms(p.get("Published")) or _date_ms(p.get("Created")), external_id=str(p.get("Id") or url))


def fetch(source: dict) -> list[RawJob]:
    api = API.format(customer=source["customer"])
    out: dict[str, RawJob] = {}
    for page in range(MAX_PAGES):
        data = get(api, params={"incads": 1, "take": PAGE, "skip": page * PAGE}).json()
        items = data if isinstance(data, list) else (data.get("Items") or data.get("items") or [])
        for p in items:
            job = to_rawjob(p)
            if job and job.external_id not in out:
                out[job.external_id] = job
        total = 0 if isinstance(data, list) else (data.get("PositionCountCustomer") or data.get("PositionCountSearch") or 0)
        if isinstance(data, list) or len(items) < PAGE or (total and len(out) >= total):
            break
    return list(out.values())
