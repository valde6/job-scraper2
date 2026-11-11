"""Nordea, ZF Lifetec (Strapi) og Munich Re (Radancy-sitemap): optagede svar (Nordea, ZF) og håndskrevne (Munich Re)."""
import json
from pathlib import Path

from scraper import run
from scraper.adapters import ADAPTERS, nordea, radancy_sitemap, strapi_zf

FIXTURES = Path(__file__).parent / "fixtures"
ALLOWED = ["DK", "SE", "FI", "DE", "GB", "CH"]


def test_registreret():
    assert ADAPTERS["nordea"] is nordea.fetch
    assert ADAPTERS["strapi_zf"] is strapi_zf.fetch
    assert ADAPTERS["radancy_sitemap"] is radancy_sitemap.fetch


# ---------------------------------------------------------------- Nordea
NORDEA_ITEM = {"title": "HRIS Specialist &amp; Analyst", "nid": "92851", "created": "2026-11-10",
               "location_name": "Poland, Warszawa, Sweden, Stockholm, Finland, Helsinki",
               "field_ad_url": "https://careers.nordea.com/job/Helsinki-HRIS/1456120333/?feedId=451033&amp;amp;utm_source=CareerSite"}


def test_nordea_rawjob():
    j = nordea.to_rawjob(NORDEA_ITEM)
    assert j.title == "HRIS Specialist & Analyst" and j.external_id == "92851" and j.posted == "2026-11-10"
    assert j.url == "https://careers.nordea.com/job/Helsinki-HRIS/1456120333/?feedId=451033&utm_source=CareerSite"
    m = run.match_job(j, ALLOWED)
    assert m["countries"] == ["SE", "FI"] and m["url"] == "https://careers.nordea.com/job/Helsinki-HRIS/1456120333/"
    assert nordea.to_rawjob({"title": "uden adresse"}) is None


def test_nordea_paginerer_til_en_side_med_faerre_end_50(monkeypatch):
    pages = {0: [dict(NORDEA_ITEM, nid=str(i)) for i in range(50)], 1: [dict(NORDEA_ITEM, nid="a"), dict(NORDEA_ITEM, nid="0")]}
    calls = []

    def fake_get(url, params=None, **kw):
        calls.append(dict(params))
        return type("R", (), {"json": lambda self: {"results": pages.get(params["page"], [])}})()

    monkeypatch.setattr(nordea, "get", fake_get)
    out = nordea.fetch({"url": "https://www.nordea.com/en/api/jobs-list"})
    assert len(out) == 51                                  # nid "0" gentages og dubletter fjernes
    assert [c["page"] for c in calls[:2]] == [0, 1] and calls[0]["items_per_page"] == 50 and calls[0]["_format"] == "json"


def test_nordea_fixture(monkeypatch):
    monkeypatch.setenv("SCRAPER_REPLAY", str(FIXTURES / "nordea"))
    jobs = nordea.fetch({"url": "https://www.nordea.com/en/api/jobs-list"})
    assert len(jobs) == 10
    assert all(j.url.startswith("https://careers.nordea.com/job/") and "&amp;" not in j.title for j in jobs)
    assert run.run_source("Nordea", {"type": "nordea", "url": "https://www.nordea.com/en/api/jobs-list"})[1]["ok"]


# ---------------------------------------------------------------- ZF Lifetec
ZF_ITEM = {"id": 5894, "Title": "HR SuccessFactors Senior Technology Analyst", "Slug": "hr-successfactors-senior-technology-analyst-73939",
           "SapID": "73939", "City": "Stuttgart", "publishedAt": "2026-11-11T15:21:04.121Z",
           "Countries": [{"Title": "Germany"}, {"Title": "Poland"}]}


def test_zf_rawjob():
    j = strapi_zf.to_rawjob("https://careers.zf-lifetec.com/jobs", ZF_ITEM)
    assert j.url == "https://careers.zf-lifetec.com/jobs/hr-successfactors-senior-technology-analyst-73939"
    assert j.location == "Stuttgart, Germany" and j.countries == ["DE"] and j.external_id == "73939"
    assert run.match_job(j, ALLOWED)["posted"] == "2026-11-11"
    assert strapi_zf.to_rawjob("https://x", {"Title": "uden slug"}) is None


def test_zf_filtre_og_sider(monkeypatch):
    calls = []

    def fake_get(url, params=None, **kw):
        calls.append(dict(params))
        n = params["pagination[page]"]
        return type("R", (), {"json": lambda self: {"data": [dict(ZF_ITEM, Slug=f"s{n}", SapID=str(n))],
                                                    "meta": {"pagination": {"pageCount": 2}}}})()

    monkeypatch.setattr(strapi_zf, "get", fake_get)
    out = strapi_zf.fetch({"url": "https://api.example/api/jobs", "job_base": "https://careers.example/jobs/"})
    assert [j.url for j in out] == ["https://careers.example/jobs/s1", "https://careers.example/jobs/s2"]
    p = calls[0]
    assert p["populate[0]"] == "Countries" and p["pagination[pageSize]"] == 100
    assert p["filters[$or][0][Title][$containsi]"] == "SuccessFactors" and p["filters[$or][1][Title][$containsi]"] == "HRIS"
    assert "locale" not in p


def test_zf_fixture(monkeypatch):
    monkeypatch.setenv("SCRAPER_REPLAY", str(FIXTURES / "zf_lifetec"))
    src = {"type": "strapi_zf", "url": "https://careers-strapi.zf-lifetec.com/api/jobs", "job_base": "https://careers.zf-lifetec.com/jobs"}
    [job] = strapi_zf.fetch(src)
    assert job.title == "HR SuccessFactors Senior Technology Analyst" and job.location == "Washington, United States"
    assert run.match_job(job, ALLOWED) is None            # USA er ikke et af landene
    assert run.run_source("ZF Lifetec", src)[1]["ok"]


# ---------------------------------------------------------------- Munich Re
SITEMAP = """﻿<?xml version="1.0" encoding="utf-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>https://careers.example.com</loc></url>
<url><loc>https://careers.example.com/en/category/it-jobs/3167/32278592/1</loc><lastmod>2026-11-11T18:05:36Z</lastmod></url>
<url><loc>https://careers.example.com/en/job/munich/sap-successfactors-consultant-m-w-d/3342/111</loc><lastmod>2026-11-10T10:00:00Z</lastmod></url>
<url><loc>https://careers.example.com/en/job/zurich/hris-analyst/3342/222</loc><lastmod>2026-11-09T10:00:00Z</lastmod></url>
<url><loc>https://careers.example.com/en/job/new-york/director-client-implementation-and-success/3342/333</loc><lastmod>2026-11-11T10:00:00Z</lastmod></url>
<url><loc>https://careers.example.com/en/job/berlin/chris-assistant/3342/444</loc></url>
</urlset>"""

JOBPAGE = """<html><script type="application/ld+json">{"@type": "JobPosting", "title": "SAP SuccessFactors Consultant (m/w/d)",
"datePosted": "2026-11-11", "jobLocation": [{"@type": "Place", "address": {"addressLocality": "München", "addressRegion": "DE-BY", "addressCountry": "DEU"}}]}</script></html>"""
JOBPAGE_UDEN_DATO = """<html><script type="application/ld+json">{"@type": "JobPosting", "title": "HRIS Analyst",
"jobLocation": {"address": {"addressLocality": "Zürich", "addressCountry": "CH"}}}</script></html>"""


def test_titel_fra_url():
    assert radancy_sitemap.title_from_url("https://x/en/job/munich/sap-successfactors-consultant/3342/1") == "sap successfactors consultant"
    assert radancy_sitemap.title_from_url("https://x/en/category/it-jobs/3167/1/1") == ""


def test_sitemap_med_bom_laeses():
    urls = radancy_sitemap.parse_sitemap(SITEMAP)
    assert len(urls) == 6 and urls[2][1] == "2026-11-10T10:00:00Z"
    assert len(radancy_sitemap.parse_sitemap("ï»¿" + SITEMAP.lstrip("﻿"))) == 6   # BOM læst som latin-1


def test_munichre_kun_titler_med_soegeord_hentes(monkeypatch):
    fetched = []
    pages = {"111": JOBPAGE, "222": JOBPAGE_UDEN_DATO}

    def fake_get(url, **kw):
        fetched.append(url)
        text = SITEMAP if url.endswith("sitemap.xml") else pages[url.rsplit("/", 1)[-1]]
        return type("R", (), {"text": text})()

    monkeypatch.setattr(radancy_sitemap, "get", fake_get)
    out = radancy_sitemap.fetch({"url": "https://careers.example.com", "sitemap": "https://careers.example.com/en/sitemap.xml"})
    assert [u.rsplit("/", 1)[-1] for u in fetched] == ["sitemap.xml", "111", "222"]      # ikke "…-and-success" og ikke "chris"
    assert not any("search-jobs" in u for u in fetched)
    a, b = out
    assert a.title == "SAP SuccessFactors Consultant (m/w/d)" and a.countries == ["DE"] and a.posted == "2026-11-11"
    assert b.countries == ["CH"] and b.posted == "2026-11-09T10:00:00Z"                  # reserve: lastmod
    assert run.match_job(b, ALLOWED)["posted"] == "2026-11-09"


def test_munichre_sitemap_fra_url_uden_sitemap_felt(monkeypatch):
    seen = []
    monkeypatch.setattr(radancy_sitemap, "get", lambda url, **kw: (seen.append(url), type("R", (), {"text": "<urlset></urlset>"})())[1])
    assert radancy_sitemap.fetch({"url": "https://careers.example.com/"}) == []
    assert seen == ["https://careers.example.com/sitemap.xml"]
