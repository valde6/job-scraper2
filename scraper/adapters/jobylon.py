"""Jobylon-widget – KPMG Sverige (se docs/KILDER.md).

Config: `company_id` (KPMG Sverige: 1532)
Embed-siden `https://cdn.jobylon.com/jobs/companies/{id}/embed/v2/?target=jobylon-jobs-widget&page_size=100` indeholder joblisten som JavaScript
(`JBL.embed_v2['jobs'] = [ { id: '…', url: '/jobs/…/', title: '…', … } ]`, ikke JSON): `id`, `url` og `title` hentes med regex pr. objekt.
Kun for titler, der matcher et søgeord, hentes jobsiden (https://emp.jobylon.com/jobs/…) for JSON-LD (`datePosted`, sted).
Alle KPMG Sverige-opslag er i Sverige: kan stedet ikke tolkes som et land i settings.yaml, bruges `["SE"]`.
Får vi 403/503 fra Cloudflare, fejler kilden med "blokeret af Cloudflare" – ingen omgåelse. /jobs/*/preview/ er forbudt og bruges ikke.
"""
from __future__ import annotations

import re

import requests

from scraper.adapters.successfactors import parse_jobpage
from scraper.common import clean, get
from scraper.match import countries_in, title_keywords
from scraper.model import RawJob

EMBED = "https://cdn.jobylon.com/jobs/companies/{company_id}/embed/v2/?target=jobylon-jobs-widget&page_size=100"
JOB_HOST = "https://emp.jobylon.com"
MAX_JOBPAGES = 30
_OBJ = re.compile(r"\bid:\s*'(\d+)',\s*url:\s*'((?:[^'\\]|\\.)*)',\s*title:\s*'((?:[^'\\]|\\.)*)'", re.S)


def js_string(s: str) -> str:
    """JavaScript-escapes i en streng: `\\u002D` → `-`, `\\x26` → `&`, `\\'` → `'`."""
    s = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), s)
    s = re.sub(r"\\x([0-9a-fA-F]{2})", lambda m: chr(int(m.group(1), 16)), s)
    return re.sub(r"\\(.)", r"\1", s)


def parse_embed(html: str) -> list[tuple[str, str, str]]:
    """[(id, url, titel)] fra `JBL.embed_v2['jobs']`. Rejser ValueError, hvis listen slet ikke findes (siden har ændret form)."""
    i = html.find("JBL.embed_v2['jobs']")
    if i < 0:
        raise ValueError("JBL.embed_v2['jobs'] findes ikke i embed-siden")
    j = html.find("];", i)
    block = html[i: j if j > 0 else len(html)]
    return [(jid, js_string(url), clean(js_string(title))) for jid, url, title in _OBJ.findall(block)]


def _blocked(e: requests.HTTPError) -> bool:
    r = e.response
    return r is not None and r.status_code in (403, 503) and (
        "cloudflare" in r.headers.get("server", "").lower() or "cf-ray" in r.headers or "cloudflare" in r.text.lower())


def fetch(source: dict) -> list[RawJob]:
    try:
        embed = get(EMBED.format(company_id=source["company_id"])).text
    except requests.HTTPError as e:
        if _blocked(e):
            raise RuntimeError(f"blokeret af Cloudflare (HTTP {e.response.status_code})") from e
        raise
    out: list[RawJob] = []
    pages = 0
    for jid, path, title in parse_embed(embed):
        url = path if path.startswith("http") else JOB_HOST + path
        posted, location = None, ""
        if title_keywords(title) and pages < MAX_JOBPAGES:
            pages += 1
            try:
                page = parse_jobpage(get(url).text)
                title, posted = page["title"] or title, page["posted"] or None
                location = " | ".join(dict.fromkeys(page["locations"]))
            except Exception:  # noqa: BLE001  – ét opslag, der fejler, vælter ikke kilden
                pass
        out.append(RawJob(title=title, url=url, location=location, countries=countries_in(location) or ["SE"],
                          posted=posted, external_id=jid))
    return out
