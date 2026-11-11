"""Phenom (Ricoh Europe, Givaudan) og Eightfold (Ericsson). Små håndskrevne svar + optagede svar uden netværk."""
import json
from pathlib import Path

import pytest

from scraper import run
from scraper.adapters import ADAPTERS, eightfold, phenom

FIXTURES = Path(__file__).parent / "fixtures"
ALLOWED = ["DK", "SE", "FI", "DE", "GB", "CH"]


def _page(jobs, total):
    ddo = {"eagerLoadRefineSearch": {"totalHits": total, "data": {"jobs": jobs}}}
    return "<html><script>var x=1; phApp.ddo = " + json.dumps(ddo) + "; phApp.other = {};</script></html>"


def test_registreret():
    assert ADAPTERS["phenom"] is phenom.fetch and ADAPTERS["eightfold"] is eightfold.fetch


# ---------------------------------------------------------------- Phenom
def test_ddo_laeses_midt_i_scriptet():
    assert phenom._ddo(_page([], 0))["eagerLoadRefineSearch"]["totalHits"] == 0
    assert phenom._ddo("<html>ingenting</html>") == {}
    assert phenom._ddo("phApp.ddo = {ødelagt") == {}


def test_phenom_rawjob():
    p = {"jobId": "RE02842", "title": " SAP SuccessFactors Engineer ", "city": "London", "country": "United Kingdom",
         "postedDate": "2026-11-10T09:00:00.000+0000", "multi_location": ["London, London, United Kingdom", "Stockholm, Sweden"]}
    j = phenom.to_rawjob("https://c.example/gb/en", p)
    assert j.url == "https://c.example/gb/en/job/RE02842" and j.title == "SAP SuccessFactors Engineer"
    assert j.location == "London, United Kingdom" and j.countries == ["GB", "SE"]
    assert run.match_job(j, ALLOWED)["posted"] == "2026-11-10"
    assert phenom.to_rawjob("https://c.example", {"title": "uden id"}) is None


def test_phenom_sider_og_ignoreret_soegeord(monkeypatch):
    """Serveren ignorerer `keywords`: listen hentes én gang, side for side, og andet ord springes over."""
    jobs = [{"jobId": f"J{i}", "title": f"Job {i}", "city": "Berlin", "country": "Germany"} for i in range(25)]
    calls = []

    def fake_get(url, **kw):
        calls.append(url)
        frm = int(url.split("from=")[1].split("&")[0])
        return type("R", (), {"text": _page(jobs[frm:frm + 10], 25)})()

    monkeypatch.setattr(phenom, "get", fake_get)
    out = phenom.fetch({"url": "https://c.example/global/en/"})
    assert [j.external_id for j in out] == [f"J{i}" for i in range(25)]
    assert len(calls) == 3 + 1          # tre sider for første ord, kun side 1 for andet ord
    assert all("/search-results?keywords=" in c and "/apply" not in c and "px-widgets" not in c for c in calls)


def test_ricoh_fixture(monkeypatch):
    monkeypatch.setenv("SCRAPER_REPLAY", str(FIXTURES / "ricoh_europe"))
    jobs = phenom.fetch({"url": "https://careersatricoh.com/gb/en"})
    assert len(jobs) == 119
    [hit] = [j for j in jobs if run.match_job(j, ALLOWED)]
    assert hit.title == "SAP SuccessFactors Employee Central & Compensation Engineer"
    assert hit.url == "https://careersatricoh.com/gb/en/job/RE02842" and hit.location == "London, United Kingdom"
    assert run.match_job(hit, ALLOWED)["country"] == "GB"
    status = run.run_source("Ricoh Europe", {"type": "phenom", "url": "https://careersatricoh.com/gb/en"})[1]
    assert status["ok"] and status["listed"] == 119


# ---------------------------------------------------------------- Eightfold
POS = {"id": 563121777377485, "name": "SAP SuccessFactors Specialist", "postedTs": 1794253431,
       "standardizedLocations": ["Stockholm, Stockholm County, SE", "Bucharest, Bucharest, RO"],
       "locations": ["Stockholm,Stockholm County,Sweden"], "positionUrl": "/careers/job/563121777377485"}


def test_eightfold_rawjob():
    j = eightfold.to_rawjob("https://jobs.example.com", POS)
    assert j.url == "https://jobs.example.com/careers/job/563121777377485"
    assert j.location == "Stockholm, Stockholm County, SE | Bucharest, Bucharest, RO"
    assert j.countries == ["SE", "RO"] and j.posted == 1794253431
    m = run.match_job(j, ALLOWED)
    assert m["country"] == "SE" and m["countries"] == ["SE"] and m["posted"] == "2026-11-09"
    assert eightfold._country_code("Jakarta,ID") == "ID"
    assert eightfold.to_rawjob("https://x", {"name": "uden id"}) is None


def test_eightfold_paginering_og_sti(monkeypatch):
    positions = [dict(POS, id=1000 + i, name=f"HRIS {i}") for i in range(7)]
    calls = []

    def fake_get(url, params=None, **kw):
        calls.append((url, dict(params)))
        s = params["start"]
        return type("R", (), {"json": lambda self: {"data": {"count": 7, "positions": positions[s:s + 3]}}})()

    monkeypatch.setattr(eightfold, "get", fake_get)
    out = eightfold.fetch({"url": "https://jobs.example.com/", "domain": "example.com"})
    assert len(out) == 7
    assert {u for u, _ in calls} == {"https://jobs.example.com/api/pcsx/search"}
    assert [p["start"] for u, p in calls[:3]] == [0, 3, 6] and calls[0][1]["sort_by"] == "timestamp" and calls[0][1]["location"] == ""


def test_ericsson_fixture(monkeypatch):
    monkeypatch.setenv("SCRAPER_REPLAY", str(FIXTURES / "ericsson"))
    status = run.run_source("Ericsson", {"type": "eightfold", "url": "https://jobs.ericsson.com", "domain": "ericsson.com"})[1]
    assert status["ok"] and status["listed"] == 6 and status["matched"] == 0
