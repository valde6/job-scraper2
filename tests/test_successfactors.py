"""SuccessFactors-adapteren. Formaterne er dokumenteret af de små håndskrevne eksempler øverst;
fixtures (tests/fixtures/<navn>/, optaget med `python -m scraper.record`) kører hele adapteren uden netværk."""
from pathlib import Path

import pytest
import requests

from scraper import run
from scraper.adapters import ADAPTERS, successfactors as sf

FIXTURES = Path(__file__).parent / "fixtures"
BASE = "https://careers.example.com"

# En række i søgeresultatet. Titlen står to gange (desktop + telefon); lokationen kan ende på "+N more…".
ROW_HTML = """
<table id="searchresults"><tbody>
<tr class="data-row">
  <td class="colTitle"><span class="jobTitle hidden-phone">
    <a href="/job/Toyama-HRIS-Specialist/1446584133/" class="jobTitle-link">HRIS Specialist</a></span>
    <div class="visible-phone"><span class="jobLocation visible-phone">Toyama, JP</span></div></td>
  <td class="colLocation hidden-phone"><span class="jobLocation">
    Toyama, JP <small class="nobr">+2 more…</small></span></td>
  <td class="colDate hidden-phone"><span class="jobDate">11 Nov 2026 </span></td>
</tr>
</tbody></table>
<span class="paginationLabel">Results <b>1 – 1</b> of <b>1</b></span>
"""

# Sitemap, variant 1: RSS / Google Base (alle opslag, ingen opslagsdato)
RSS = """<?xml version="1.0" encoding="UTF-8" ?><rss version="2.0" xmlns:g="http://base.google.com/ns/1.0"><channel>
<item><title>HRIS Specialist (Helsinki, Uusimaa, FI)</title><description><![CDATA[&lt;p&gt;tekst&lt;/p&gt;]]></description>
<link>https://careers.example.com/job/Helsinki-HRIS-Specialist/1450503233/</link><guid isPermaLink="false">1450503233</guid>
<g:id>1450503233</g:id><g:expiration_date>2026-12-11</g:expiration_date><g:location>Helsinki, Uusimaa, FI</g:location></item>
<item><title>Sales Manager (m/f/d)</title><link>https://careers.example.com/job/Berlin-Sales-Manager/1450503299/</link>
<g:id>1450503299</g:id><g:location>Berlin, DE</g:location></item>
</channel></rss>"""

# Sitemap, variant 2: almindelig urlset (titel og by står kun i adressen)
URLSET = """<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.google.com/schemas/sitemap/0.9">
<url><loc>https://careers.example.com/DEU/job/M%C3%BCnchen-SAP-SuccessFactors-Consultant-%28mwd%29/1433825433/</loc><lastmod>2026-11-07</lastmod></url>
<url><loc>https://careers.example.com/</loc><lastmod>2026-11-07</lastmod></url></urlset>"""

JOBPAGE_MICRODATA = """<div itemscope itemtype="http://schema.org/JobPosting">
<span itemprop="jobLocation" itemscope itemtype="http://schema.org/Place">
<span itemprop="address" itemscope><meta itemprop="streetAddress" content="Kobe, JP"></span>
<span itemprop="address" itemscope><meta itemprop="streetAddress" content="Helsinki, FI"></span></span>
<meta itemprop="datePosted" content="Wed Nov 11 02:00:00 UTC 2026">
<span itemprop="title">HRIS Specialist</span></div>"""

JOBPAGE_JSONLD = """<script type="application/ld+json">{"@type": "JobPosting", "title": "HRIS Analyst",
"datePosted": "2026-11-09", "jobLocation": [{"address": {"addressLocality": "Stockholm", "addressCountry": "SE"}},
{"address": {"addressLocality": "Berlin", "addressCountry": "DE"}}]}</script>"""


# ---------------------------------------------------------------- de små parsere
def test_job_id_er_tallet_i_adressen():
    assert sf.job_id_from_url("https://x/job/Toyama-HRIS/1446584133/") == "1446584133"
    assert sf.job_id_from_url("https://x/DEU/job/A-B-%28mwd%29/1433825433/?x=1") == "1433825433"
    assert sf.job_id_from_url("https://x/") == ""


def test_parse_search_rows():
    [p] = sf.parse_search_rows(ROW_HTML, BASE)
    assert p.title == "HRIS Specialist"
    assert p.url == f"{BASE}/job/Toyama-HRIS-Specialist/1446584133/"
    assert (p.job_id, p.location, p.more_locations, p.date) == ("1446584133", "Toyama, JP", True, "11 Nov 2026")
    assert sf.search_total(ROW_HTML) == 1


def test_parse_search_rows_fallback_til_job_links():
    html = '<div><a href="/job/Aarhus-HRIS-Lead/1400000001/">HRIS Lead</a><a href="/about/">Om os</a></div>'
    [p] = sf.parse_search_rows(html, BASE)
    assert (p.title, p.job_id, p.location, p.date) == ("HRIS Lead", "1400000001", "", "")


def test_search_page_parsable():
    assert sf.search_page_parsable('<div id="search-wrapper"></div>')            # 0 resultater er stadig en søgeside
    assert sf.search_page_parsable(ROW_HTML)
    assert not sf.search_page_parsable("<html><body>Access denied</body></html>")
    # "unify"-sider: tomt skelet, resultaterne hentes af JavaScript fra /services/ → ikke parsbar
    assert not sf.search_page_parsable('<div id="search-wrapper"></div><script src="j2w.SearchResultsUnify.min.js"></script>')


def test_parse_sitemap_rss():
    a, b = sf.parse_sitemap(RSS)
    assert (a.title, a.location, a.job_id) == ("HRIS Specialist", "Helsinki, Uusimaa, FI", "1450503233")
    assert a.url == "https://careers.example.com/job/Helsinki-HRIS-Specialist/1450503233/"
    assert b.title == "Sales Manager (m/f/d)"                                    # parentesen er ikke en lokation


def test_parse_sitemap_urlset():
    [p] = sf.parse_sitemap(URLSET)
    assert p.job_id == "1433825433"
    assert p.title == "München SAP SuccessFactors Consultant (mwd)"


def test_parse_jobpage_microdata_og_jsonld():
    m = sf.parse_jobpage(JOBPAGE_MICRODATA)
    assert m == {"title": "HRIS Specialist", "posted": "Wed Nov 11 02:00:00 UTC 2026",
                 "locations": ["Kobe, JP", "Helsinki, FI"]}
    j = sf.parse_jobpage(JOBPAGE_JSONLD)
    assert j == {"title": "HRIS Analyst", "posted": "2026-11-09", "locations": ["Stockholm, SE", "Berlin, DE"]}


# ---------------------------------------------------------------- hele adapteren med falske svar
class FakeWeb:
    """Erstatter `get` i adapteren: {url-del: tekst | Exception}."""
    def __init__(self, monkeypatch, routes):
        self.routes, self.calls = routes, []
        monkeypatch.setattr(sf, "get", self)

    def __call__(self, url, **kw):
        self.calls.append(url)
        for part, answer in self.routes.items():
            if part in url:
                if isinstance(answer, Exception):
                    raise answer
                r = requests.Response()
                r.status_code, r._content = 200, answer.encode()
                return r
        raise requests.HTTPError(f"404 {url}")


def test_job_med_flere_lokationer_henter_jobsiden(monkeypatch):
    web = FakeWeb(monkeypatch, {"/search/": ROW_HTML, "1446584133": JOBPAGE_MICRODATA})
    [job] = sf.fetch({"url": BASE})
    assert job.countries == ["FI"]                                           # JP er ikke et af settings' lande
    assert job.location == "Kobe, JP | Helsinki, FI"
    assert job.posted == "Wed Nov 11 02:00:00 UTC 2026"
    assert len([c for c in web.calls if "/job/" in c]) == 1                  # jobsiden hentes kun én gang (dedup over søgeord)


def test_job_med_dato_og_land_henter_ikke_jobsiden(monkeypatch):
    row = ROW_HTML.replace("+2 more…", "").replace("Toyama, JP", "Helsinki, FI")
    web = FakeWeb(monkeypatch, {"/search/": row})
    [job] = sf.fetch({"url": BASE})
    assert (job.location, job.posted, job.countries) == ("Helsinki, FI", "11 Nov 2026", [])
    assert not [c for c in web.calls if "/job/" in c]


def test_titler_uden_match_henter_aldrig_jobsiden(monkeypatch):
    row = ROW_HTML.replace("HRIS Specialist", "Strategic Purchaser")
    web = FakeWeb(monkeypatch, {"/search/": row})
    [job] = sf.fetch({"url": BASE})
    assert job.title == "Strategic Purchaser"
    assert not [c for c in web.calls if "/job/" in c]


def test_jobside_der_fejler_vaelter_ikke_kilden(monkeypatch):
    FakeWeb(monkeypatch, {"/search/": ROW_HTML, "1446584133": requests.ConnectionError("nede")})
    [job] = sf.fetch({"url": BASE})
    assert job.title == "HRIS Specialist" and job.posted == "11 Nov 2026"


def test_loft_paa_jobsider(monkeypatch):
    rows = "".join(f'<tr class="data-row"><a class="jobTitle-link" href="/job/X-HRIS-{i}/{1000000 + i}/">HRIS {i}</a></tr>'
                   for i in range(40))
    web = FakeWeb(monkeypatch, {"/search/": f'<div id="search-wrapper"></div><table id="searchresults">{rows}</table>',
                                "/job/": JOBPAGE_JSONLD})
    jobs = sf.fetch({"url": BASE})
    assert len(jobs) == 40
    assert len([c for c in web.calls if "/job/" in c]) == sf.MAX_JOBPAGES


def test_paginering_stopper_ved_total_og_uden_nye_raekker(monkeypatch):
    def page(ids, total):
        rows = "".join(f'<tr class="data-row"><a class="jobTitle-link" href="/job/A-{i}/{i}/">T{i}</a></tr>' for i in ids)
        return f'<table id="searchresults">{rows}</table><span class="paginationLabel">Results <b>1</b> of <b>{total}</b></span>'
    web = FakeWeb(monkeypatch, {"startrow=0": page([10001, 10002], 3), "startrow=2": page([10003], 3)})
    jobs = sf.fetch({"url": BASE})
    assert sorted(j.external_id for j in jobs) == ["10001", "10002", "10003"]
    assert len(web.calls) == 3                                              # 2 sider for første søgeord, 1 side (kun dubletter) for andet


def test_sitemap_fallback_ved_fejl_paa_soegesiden(monkeypatch):
    web = FakeWeb(monkeypatch, {"/search/": requests.HTTPError("503"), "/sitemap.xml": RSS,
                                "1450503233": JOBPAGE_MICRODATA})
    jobs = sf.fetch({"url": BASE})
    assert [j.title for j in jobs] == ["HRIS Specialist", "Sales Manager (m/f/d)"]
    assert jobs[0].posted == "Wed Nov 11 02:00:00 UTC 2026"                 # dato fra jobsiden (sitemap har ingen)
    assert "FI" in jobs[0].countries
    assert jobs[1].location == "Berlin, DE" and jobs[1].posted is None
    assert any("/sitemap.xml" in c for c in web.calls)


def test_sitemap_fallback_naar_soegesiden_ikke_kan_parses(monkeypatch):
    FakeWeb(monkeypatch, {"/search/": "<html>Access denied</html>", "/sitemap.xml": URLSET, "1433825433": JOBPAGE_JSONLD})
    [job] = sf.fetch({"url": BASE})
    assert job.title == "HRIS Analyst"                                       # rigtig titel fra jobsiden
    assert job.countries == ["SE", "DE"]


def test_sitemap_fallback_for_unify_soegeside(monkeypatch):
    unify = '<body class="unify"><div id="search-wrapper"></div><script>j2w.SearchResultsUnify.removeResultContent()</script>'
    web = FakeWeb(monkeypatch, {"/search/": unify, "/sitemap.xml": RSS, "1450503233": JOBPAGE_MICRODATA})
    assert [j.title for j in sf.fetch({"url": BASE})] == ["HRIS Specialist", "Sales Manager (m/f/d)"]
    assert any("/sitemap.xml" in c for c in web.calls)


UNIFY_JOBPAGE = ("<html><head><title>Senior Consultant SAP SuccessFactors / HCM (w/m/d) Stellendetails | KPMG AG</title></head>"
                 "<body><h2>Stellenbeschreibung</h2></body></html>")


def test_unify_jobside_giver_kun_titel():
    assert sf.parse_jobpage(UNIFY_JOBPAGE) == {"title": "Senior Consultant SAP SuccessFactors / HCM (w/m/d)",
                                               "posted": "", "locations": []}


def test_unify_sitemap_uden_lokation_bruger_landet_fra_config(monkeypatch):
    urlset = URLSET.replace("M%C3%BCnchen-SAP", "K%C3%B6ln-SAP")
    FakeWeb(monkeypatch, {"/search/": '<div id="search-wrapper"></div><script>j2w.SearchResultsUnify</script>',
                          "/sitemap.xml": urlset, "1433825433": UNIFY_JOBPAGE})
    [job] = sf.fetch({"url": BASE, "country": "DE"})
    assert job.countries == ["DE"] and job.posted is None and job.location == ""
    assert job.title == "Senior Consultant SAP SuccessFactors / HCM (w/m/d)"
    [job] = sf.fetch({"url": BASE})                                         # uden `country`: intet at gå efter
    assert job.countries == []


def test_country_overstyrer_ikke_en_oplyst_lokation(monkeypatch):
    FakeWeb(monkeypatch, {"/search/": ROW_HTML.replace("Toyama, JP", "Paris, FR").replace("+2 more…", "")})
    [job] = sf.fetch({"url": BASE, "country": "GB"})
    assert job.countries == [] and job.location == "Paris, FR"


def test_ingen_sitemap_fallback_ved_nul_resultater(monkeypatch):
    web = FakeWeb(monkeypatch, {"/search/": '<div id="search-wrapper"></div>', "/sitemap.xml": RSS})
    assert sf.fetch({"url": BASE}) == []
    assert not any("/sitemap.xml" in c for c in web.calls)


def test_begge_veje_fejler(monkeypatch):
    FakeWeb(monkeypatch, {"/search/": requests.HTTPError("503"), "/sitemap.xml": requests.HTTPError("404")})
    with pytest.raises(RuntimeError, match="søgesiden.*sitemap"):
        sf.fetch({"url": BASE})


# ---------------------------------------------------------------- optagne svar (ingen netværk)
def test_registreret_som_adapter():
    assert ADAPTERS["successfactors"] is sf.fetch


@pytest.fixture
def replay(monkeypatch):
    def use(name):
        monkeypatch.setenv("SCRAPER_REPLAY", str(FIXTURES / name))
    return use


def test_wartsila_fixture(replay):
    replay("wartsila")
    jobs = sf.fetch({"url": "https://careers.wartsila.com"})
    assert len(jobs) == 10
    assert all(j.url.startswith("https://careers.wartsila.com/job/") and j.external_id for j in jobs)
    assert all(j.posted for j in jobs)
    assert run.run_source("Wärtsilä", {"type": "successfactors", "url": "https://careers.wartsila.com"})[1]["ok"]


def test_bertelsmann_fixture(replay):
    replay("bertelsmann")
    jobs = sf.fetch({"url": "https://jobsearch.createyourowncareer.com"})
    assert len(jobs) == 39
    [hris] = [j for j in jobs if "HRIS" in j.title]
    assert hris.title == "Praktikant:in im Bereich HRIS (m/w/d)"
    assert hris.external_id == "1412284033" and hris.posted == "Oct 31, 2026"
    m = run.match_job(hris, ["DK", "SE", "FI", "DE", "GB", "CH"])
    assert m["country"] == "DE" and m["posted"] == "2026-10-31"
