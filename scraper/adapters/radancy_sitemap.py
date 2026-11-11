"""Munich Re (Radancy): sitemap + jobsider (se docs/KILDER.md).

Config: `url` = https://careers.munichre.com   `sitemap` (valgfri) = https://careers.munichre.com/en/sitemap.xml (ellers `{url}/sitemap.xml`)

robots.txt forbyder /search-jobs/ for alle undtagen Indeed – den bruges ikke, heller ikke som fallback.
1. Sitemap'en (ca. 4.000 adresser, ca. 1.600 job). Behold `<loc>` med `/job/`, hvis titel-slug (`/job/{by}/{titel-slug}/{x}/{id}`,
   `-` → mellemrum) matcher et søgeord. Adapteren afgør ikke selv, om det er et match (regel 4): det bruges til at spare kald.
2. Hent hver (højst MAX_JOBPAGES) og læs JSON-LD: titel, `datePosted`, `jobLocation` → location + lande.
   `<lastmod>` fra sitemap'en er reserve for datoen, hvis JSON-LD mangler `datePosted`.
"""
from __future__ import annotations

from urllib.parse import unquote, urlsplit

from lxml import etree

from scraper.adapters.successfactors import parse_jobpage
from scraper.common import clean, get
from scraper.match import countries_in, title_keywords
from scraper.model import RawJob

MAX_JOBPAGES = 30


def _local(el) -> str:
    return etree.QName(el).localname if isinstance(el.tag, str) else ""


def parse_sitemap(xml: str) -> list[tuple[str, str]]:
    """[(url, lastmod)] for alle `<url>` i en urlset."""
    # Svaret har en UTF-8-BOM uden charset i headeren, så requests læser den som "ï»¿": spring alt før første "<" over
    xml = xml[xml.find("<"):] if "<" in xml else ""
    root = etree.fromstring(xml.encode("utf-8"), etree.XMLParser(recover=True, huge_tree=True, resolve_entities=False))
    if root is None:
        raise ValueError("sitemap kunne ikke læses")
    out = []
    for el in root.iter():
        if _local(el) == "url":
            f = {_local(c): clean(c.text) for c in el if isinstance(c.tag, str)}
            if f.get("loc"):
                out.append((f["loc"], f.get("lastmod", "")))
    return out


def title_from_url(url: str) -> str:
    """`/en/job/munich/sap-successfactors-analyst/3342/4682` → "sap successfactors analyst" (ellers "")."""
    parts = [unquote(p) for p in urlsplit(url).path.split("/") if p]
    if "job" not in parts:
        return ""
    rest = parts[parts.index("job") + 1:]          # [by, titel-slug, x, id]
    return clean(rest[1].replace("-", " ")) if len(rest) >= 2 else ""


def fetch(source: dict) -> list[RawJob]:
    base = source["url"].rstrip("/")
    entries = parse_sitemap(get(source.get("sitemap") or f"{base}/sitemap.xml").text)
    candidates = [(u, lm) for u, lm in entries if "/job/" in u and title_keywords(title_from_url(u))]
    out: list[RawJob] = []
    for url, lastmod in candidates[:MAX_JOBPAGES]:
        try:
            page = parse_jobpage(get(url).text)
        except Exception:  # noqa: BLE001  – ét opslag, der fejler, vælter ikke kilden
            continue
        locs = list(dict.fromkeys(page["locations"]))
        location = " | ".join(locs)
        out.append(RawJob(title=page["title"] or title_from_url(url), url=url, location=location,
                          countries=countries_in(location), posted=page["posted"] or lastmod or None,
                          external_id=url.rstrip("/").rsplit("/", 1)[-1]))
    return out
