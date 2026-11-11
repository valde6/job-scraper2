"""SAP SuccessFactors Career Site Builder (CSB) – 13 kilder (se docs/KILDER.md).

Config: `url` = CSB-domænet, fx https://careers.wartsila.com
        `country` (valgfri, ISO-kode) = landet for sider, hvor jobbene slet ikke oplyser et sted (se to_rawjob)

1. Primært søgesiden `/search/?q=<ord>` (server-renderet HTML), ét gennemløb pr. søgeord i settings.
2. Fallback `/sitemap.xml`, hvis søgesiden svarer med fejl eller ikke kan parses (ikke ved 0 resultater). Sitemap'en findes i to
   varianter: RSS/Google Base (`<item>`) og almindelig `<urlset>`.
3. For job, hvis TITEL matcher, hentes jobsiden (højst MAX_JOBPAGES pr. kilde), når datoen mangler, lokationen siger `+N more…`
   eller ikke nævner et land. Jobsiden har JSON-LD eller schema.org-microdata med `datePosted` og alle `jobLocation`.

Adapteren afgør ikke, om et job er et match (AGENTS.md regel 4): titlen bruges kun til at spare jobside-kald.
"Unify"-sider (Ambu, Novo Nordisk m.fl. – søgesiden er et skelet, jobsiderne tomme) har hverken dato eller lokation uden
JavaScript; der bruges sitemap'ens by i adressen, titlen fra <title> og ingen dato.
/services/ (RSS-feeds) er forbudt i robots.txt og bruges ikke.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import quote, unquote, urljoin, urlsplit

from lxml import etree

from scraper.common import clean, get, jsonld_jobposting, parse_date, soup
from scraper.match import countries_in, settings, title_keywords
from scraper.model import RawJob

MAX_START = 300          # loft for `startrow`
MAX_JOBPAGES = 30        # jobsider pr. kilde


@dataclass
class Posting:
    """Ét opslag, som det står i søgeresultatet eller sitemap'en."""
    job_id: str
    title: str
    url: str
    location: str = ""
    date: str = ""                       # rå tekst, fx "11 Nov 2026"
    more_locations: bool = False         # "+10 more…"
    countries: list[str] = field(default_factory=list)


# ---------------------------------------------------------------- små parsere (hver for sig testbare)
def job_id_from_url(url: str) -> str:
    """Job-id = det lange tal i adressen (`/job/<slug>/1446584133/`)."""
    m = re.search(r"/(\d{5,})/?(?:[?#].*)?$", url)
    return m.group(1) if m else ""


def parse_search_rows(html: str, base: str) -> list[Posting]:
    """Rækkerne (`tr.data-row`) på en søgeside. Uden rækker: alle `a[href*='/job/']` (kun titel og adresse)."""
    s = soup(html)
    out: list[Posting] = []
    rows = s.select("tr.data-row")
    for row in rows:
        a = row.select_one("a.jobTitle-link") or row.select_one("a[href*='/job/']")
        if not a or not a.get("href"):
            continue
        loc_el = row.select_one("td.colLocation .jobLocation") or row.select_one(".jobLocation")
        more, loc = False, ""
        if loc_el:
            txt = clean(loc_el.get_text(" "))
            more = bool(re.search(r"\+\s*\d+\s*more", txt, re.I))
            loc = clean(re.sub(r"\+\s*\d+\s*more\W*", "", txt, flags=re.I))
        date_el = row.select_one("td.colDate .jobDate") or row.select_one(".jobDate")
        url = urljoin(base + "/", a["href"])
        out.append(Posting(job_id_from_url(url), clean(a.get_text(" ")), url, loc,
                           clean(date_el.get_text(" ")) if date_el else "", more))
    if not rows:
        for a in s.select("a[href*='/job/']"):
            url = urljoin(base + "/", a["href"])
            if clean(a.get_text(" ")):
                out.append(Posting(job_id_from_url(url), clean(a.get_text(" ")), url))
    return out


def search_page_parsable(html: str) -> bool:
    """Ser det ud som en søgeside med resultater (eller med ægte 0 resultater)? Ellers bruges sitemap'en.

    Nogle CSB-sider (Ambu, Novo Nordisk, Søstrene Grene, KPMG Tyskland …) er "unify": søgesiden er et tomt skelet, og
    resultaterne hentes af JavaScript fra /services/ (forbudt i robots.txt). Det er ikke "0 resultater" – brug sitemap'en.
    Fejlsider og bot-mure mangler søgefeltet `#search-wrapper` og falder også igennem til sitemap'en."""
    s = soup(html)
    if s.select_one("#searchresults, .paginationLabel, tr.data-row, a[href*='/job/']"):
        return True
    return bool(s.select_one("#search-wrapper")) and "SearchResultsUnify" not in html


def search_total(html: str) -> int | None:
    """N i "Results 1 – 10 of 138"."""
    m = re.search(r'class="paginationLabel"[^>]*>.*?\bof\s*(?:<b>)?\s*(\d+)', html, re.S)
    return int(m.group(1)) if m else None


def _xml_root(content: str):
    parser = etree.XMLParser(recover=True, huge_tree=True, resolve_entities=False)
    return etree.fromstring(content.encode("utf-8"), parser)


def _local(el) -> str:
    return etree.QName(el).localname if isinstance(el.tag, str) else ""


def parse_sitemap(xml: str) -> list[Posting]:
    """RSS/Google Base-varianten (`<item>`) og `<urlset>`-varianten."""
    root = _xml_root(xml)
    if root is None:
        raise ValueError("sitemap kunne ikke læses")
    out: list[Posting] = []
    for el in root.iter():
        name = _local(el)
        if name == "item":
            f = {_local(c): clean(c.text) for c in el if isinstance(c.tag, str)}
            url = f.get("link", "")
            if not url:
                continue
            loc = f.get("location", "")
            out.append(Posting(f.get("id") or job_id_from_url(url), _title_without_location(f.get("title", ""), loc),
                               url, loc))
        elif name == "url":
            loc_el = next((c for c in el if _local(c) == "loc"), None)
            url = clean(loc_el.text) if loc_el is not None else ""
            if "/job/" in url:
                out.append(Posting(job_id_from_url(url), title_from_slug(url), url))
    return out


def _title_without_location(title: str, location: str) -> str:
    """RSS-titlen er "Titel (By, Region, CC)": fjern den sidste parentes, når den er lokationen (eller ligner en)."""
    m = re.match(r"^(.*\S)\s*\(([^()]*)\)\s*$", title)
    if m and (clean(m.group(2)) == location or ("," in m.group(2) and location)):
        return m.group(1)
    return title


def title_from_slug(url: str) -> str:
    """`/job/München-Manager-Sales-(mwd)/1433825433/` → "München Manager Sales (mwd)" (byen står først i sluggen)."""
    parts = [unquote(p) for p in urlsplit(url).path.split("/") if p]
    i = parts.index("job") if "job" in parts else -1
    return clean(parts[i + 1].replace("-", " ")) if 0 <= i < len(parts) - 1 else ""


def parse_jobpage(html: str) -> dict:
    """Jobside → {"title", "posted", "locations": [...]}. JSON-LD først, ellers schema.org-microdata (CSB bruger oftest dem)."""
    res: dict = {"title": "", "posted": "", "locations": []}
    jp = jsonld_jobposting(html)
    if jp:
        res["title"] = clean(jp.get("title"))
        res["posted"] = str(jp.get("datePosted") or "")
        locs = jp.get("jobLocation") or []
        for l in [locs] if isinstance(locs, dict) else locs:
            addr = (l or {}).get("address") or {}
            if isinstance(addr, dict):
                bits = [clean(str(addr.get(k, ""))) for k in ("addressLocality", "addressRegion", "addressCountry")
                        if isinstance(addr.get(k), str) and addr.get(k)]
                bits += [clean(str((addr.get("addressCountry") or {}).get("name", "")))] if isinstance(
                    addr.get("addressCountry"), dict) else []
                if bits:
                    res["locations"].append(", ".join(b for b in bits if b))
            elif isinstance(addr, str) and addr:
                res["locations"].append(clean(addr))
    s = soup(html)
    if not res["posted"]:
        el = s.select_one("[itemprop=datePosted]")
        res["posted"] = (el.get("content") or el.get_text(" ")) if el else ""
    if not res["locations"]:
        for addr in s.select("[itemprop=jobLocation] [itemprop=address]"):
            bits = [clean(m.get("content") or m.get_text(" ")) for m in
                    addr.select("[itemprop=streetAddress],[itemprop=addressLocality],[itemprop=addressRegion],"
                                "[itemprop=addressCountry]")]
            if any(bits):
                res["locations"].append(", ".join(b for b in bits if b))
    if not res["title"]:
        el = s.select_one("[itemprop=title]") or s.find("h1")
        res["title"] = clean(el.get_text(" ")) if el else ""
    if not res["title"] and s.title and s.title.string:
        # "unify"-jobsider (KPMG Tyskland) er tomme skeletter; kun <title> har data: "Titel Stellendetails | Firma"
        res["title"] = re.sub(r"\s+(?:Stellendetails|Job\s*Details?|Stellenangebot)\s*$", "",
                              clean(s.title.string).split(" | ")[0], flags=re.I)
    return res


# ---------------------------------------------------------------- hentning
def _search(base: str, keywords: list[str]) -> list[Posting]:
    """Alle rækker for alle søgeord. Rejser en fejl, hvis siden ikke kan hentes eller parses."""
    seen: dict[str, Posting] = {}
    for kw in keywords:
        start = 0
        while start < MAX_START:
            url = (f"{base}/search/?q={quote(kw)}&locationsearch=&sortColumn=referencedate&sortDirection=desc"
                   f"&startrow={start}")
            html = get(url).text
            if not search_page_parsable(html):
                raise ValueError(f"søgesiden kunne ikke parses ({url})")
            rows = parse_search_rows(html, base)
            new = [r for r in rows if (r.job_id or r.url) not in seen]
            for r in new:
                seen[r.job_id or r.url] = r
            total = search_total(html)
            start += len(rows)
            if not new or not rows or (total is not None and start >= total):
                break
    return list(seen.values())


def _from_sitemap(base: str) -> list[Posting]:
    return parse_sitemap(get(f"{base}/sitemap.xml").text)


def _enrich(postings: list[Posting]) -> dict[str, dict]:
    """Henter jobsider for titel-match, der mangler dato eller land. Returnerer {job_id eller url: parse_jobpage-resultat}."""
    pages: dict[str, dict] = {}
    for p in postings:
        if len(pages) >= MAX_JOBPAGES:
            break
        if not title_keywords(p.title):
            continue
        if parse_date(p.date) and not p.more_locations and countries_in(p.location):
            continue
        try:
            pages[p.job_id or p.url] = parse_jobpage(get(p.url).text)
        except Exception:  # noqa: BLE001  – ét opslag, der fejler, vælter ikke kilden
            continue
    return pages


def to_rawjob(p: Posting, page: dict | None, default_country: str | None = None) -> RawJob:
    title, location, posted, countries = p.title, p.location, p.date or None, list(p.countries)
    if page:
        title = page["title"] or title
        posted = page["posted"] or posted
        locs = list(dict.fromkeys(page["locations"]))
        if locs:
            if p.more_locations or not location:
                location = " | ".join(locs)
            countries = countries_in(" | ".join(locs + [p.location]))
    if not countries and not location and default_country:
        countries = [default_country]      # kun når kilden slet ikke oplyser et sted (unify-sider, sitemap uden lokation)
    return RawJob(title=title, url=p.url, location=location, countries=countries, posted=posted,
                  external_id=p.job_id or None)


def fetch(source: dict) -> list[RawJob]:
    base = source["url"].rstrip("/")
    keywords = [k["name"] for k in settings()["keywords"]]
    try:
        postings = _search(base, keywords)
    except Exception as search_error:  # noqa: BLE001  – søgesiden fejlede/kan ikke parses → sitemap
        try:
            postings = _from_sitemap(base)
        except Exception as sitemap_error:  # noqa: BLE001
            raise RuntimeError(f"søgesiden: {search_error}; sitemap: {sitemap_error}") from sitemap_error
    pages = _enrich(postings)
    default_country = source.get("country")
    return [to_rawjob(p, pages.get(p.job_id or p.url), default_country) for p in postings]
