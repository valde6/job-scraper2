"""KPMG Danmark (HR-Manager), Finland (Oracle) og Sverige (Jobylon): optagede svar + håndskrevne til match-stierne."""
from pathlib import Path
from types import SimpleNamespace

import pytest
import requests

from scraper import run
from scraper.adapters import ADAPTERS, hrmanager, jobylon, oracle

FIXTURES = Path(__file__).parent / "fixtures"
ALLOWED = ["DK", "SE", "FI", "DE", "GB", "CH"]
SRC_DK = {"type": "hrmanager", "customer": "kpmg", "label": "Danmark"}
SRC_FI = {"type": "oracle", "url": "https://iabdgs.fa.ocs.oraclecloud.com", "site": "CX_1002", "label": "Finland"}
SRC_SE = {"type": "jobylon", "company_id": 1532, "label": "Sverige"}


def _resp(**attrs):
    return SimpleNamespace(**attrs)


def test_registreret():
    assert ADAPTERS["hrmanager"] is hrmanager.fetch and ADAPTERS["oracle"] is oracle.fetch and ADAPTERS["jobylon"] is jobylon.fetch


# ---------------------------------------------------------------- HR-Manager
HRM_ITEM = {"Id": 144529, "Name": " HRIS Consultant – Copenhagen ", "Created": "/Date(1793354171000+0100)/",
            "Published": "/Date(1794298671000+0100)/",
            "AdvertisementUrlSecure": "https://candidate.hr-manager.net/ApplicationInit.aspx?cid=1762&ProjectId=144529&",
            "PositionLocation": {"Name": "Odense"}, "Department": {"City": "Odense", "Country": "Danmark"}}


def test_hrmanager_rawjob():
    j = hrmanager.to_rawjob(HRM_ITEM)
    assert j.title == "HRIS Consultant – Copenhagen" and j.external_id == "144529"
    assert j.location == "Odense, Danmark" and j.url.startswith("https://candidate.hr-manager.net/ApplicationInit.aspx")
    m = run.match_job(j, ALLOWED)
    assert m["country"] == "DK" and m["posted"] == "2026-11-10"          # Published vælges frem for Created
    assert hrmanager.to_rawjob(dict(HRM_ITEM, Published=None))  .posted == 1793354171000
    assert hrmanager._date_ms("/Date(-62135596800000)/") is None
    assert hrmanager.to_rawjob({"Id": 1}) is None


def test_hrmanager_henter_alle_sider(monkeypatch):
    items = [dict(HRM_ITEM, Id=i) for i in range(hrmanager.PAGE + 5)]
    calls = []

    def fake_get(url, params=None, **kw):
        calls.append((url, dict(params)))
        s = params["skip"]
        return _resp(json=lambda: {"Items": items[s:s + hrmanager.PAGE], "PositionCountCustomer": len(items)})

    monkeypatch.setattr(hrmanager, "get", fake_get)
    out = hrmanager.fetch({"customer": "kpmg"})
    assert len(out) == hrmanager.PAGE + 5
    assert calls[0][0] == "https://api.hr-manager.net/jobportal.svc/kpmg/positionlist/json/"
    assert [c[1]["skip"] for c in calls] == [0, hrmanager.PAGE] and calls[0][1]["take"] == hrmanager.PAGE


def test_kpmg_danmark_fixture(monkeypatch):
    monkeypatch.setenv("SCRAPER_REPLAY", str(FIXTURES / "kpmg_danmark"))
    jobs = hrmanager.fetch(SRC_DK)
    assert len(jobs) == 14 and all(j.url and j.posted for j in jobs)
    assert all(run.match_job(j, ALLOWED) is None for j in jobs)             # ingen HRIS-/SuccessFactors-titler lige nu
    st = run.run_source("KPMG", SRC_DK)[1]
    assert st["ok"] and st["listed"] == 14


# ---------------------------------------------------------------- Oracle
ORA_ITEM = {"Id": "1541", "Title": "SAP SuccessFactors Consultant", "PostedDate": "2026-11-11", "PrimaryLocation": "Helsinki, Finland",
            "PrimaryLocationCountry": "FI", "secondaryLocations": [{"Name": "Stockholm, Sweden"}]}


def test_oracle_rawjob():
    j = oracle.to_rawjob("https://h.example", "CX_1002", ORA_ITEM)
    assert j.url == "https://h.example/hcmUI/CandidateExperience/en/sites/CX_1002/job/1541"
    assert j.location == "Helsinki, Finland | Stockholm, Sweden" and j.countries == ["FI", "SE"] and j.posted == "2026-11-11"
    assert run.match_job(j, ALLOWED)["countries"] == ["FI", "SE"]
    assert oracle.to_rawjob("https://h", "S", {"Title": "uden id"}) is None


def test_oracle_paginerer_med_offset(monkeypatch):
    reqs = [dict(ORA_ITEM, Id=str(i)) for i in range(30)]
    finders = []

    def fake_get(url, params=None, **kw):
        finders.append(params["finder"])
        off = int(params["finder"].split("offset=")[1].split(",")[0])
        return _resp(json=lambda: {"items": [{"TotalJobsCount": 30, "requisitionList": reqs[off:off + 25]}]})

    monkeypatch.setattr(oracle, "get", fake_get)
    out = oracle.fetch({"url": "https://h.example/", "site": "CX_1002"})
    assert len(out) == 30
    assert finders[0] == "findReqs;siteNumber=CX_1002,keyword=SuccessFactors,limit=25,offset=0,sortBy=POSTING_DATES_DESC"
    assert "offset=25" in finders[1] and "keyword=HRIS" in finders[2]


def test_kpmg_finland_fixture(monkeypatch):
    monkeypatch.setenv("SCRAPER_REPLAY", str(FIXTURES / "kpmg_finland"))
    st = run.run_source("KPMG", SRC_FI)[1]
    assert st["ok"] and st["listed"] == 0


# ---------------------------------------------------------------- Jobylon
EMBED = """<script>JBL.embed_v2['jobs'] = [
  { id: '1', url: '/jobs/1-kpmg-hris-specialist/', title: 'HRIS Specialist \\u002D Payroll \\u0026 Reward',
    company: 'KPMG', klass: { 'job-id-1': true } },
  { id: '2', url: '/jobs/2-kpmg-tax/', title: 'Tax \\u0026 Legal söker praktikanter', company: 'KPMG' },
];</script><script>var id: '9', url: 'x', title: 'efter listen';</script>"""
JOBPAGE = """<script type="application/ld+json">{"@type": "JobPosting", "title": "HRIS Specialist - Payroll & Reward",
"datePosted": "2026-11-09T14:16:00+00:00", "jobLocation": [{"address": {"addressLocality": "Göteborg"}}]}</script>"""


def test_js_streng_og_embed():
    assert jobylon.js_string(r"A - B & C \x26 D \'E\'") == "A - B & C & D 'E'"
    assert jobylon.parse_embed(EMBED) == [("1", "/jobs/1-kpmg-hris-specialist/", "HRIS Specialist - Payroll & Reward"),
                                          ("2", "/jobs/2-kpmg-tax/", "Tax & Legal söker praktikanter")]
    with pytest.raises(ValueError):
        jobylon.parse_embed("<html>Just a moment...</html>")


def test_jobylon_henter_kun_jobside_ved_titelmatch(monkeypatch):
    fetched = []

    def fake_get(url, **kw):
        fetched.append(url)
        return _resp(text=EMBED if "embed" in url else JOBPAGE)

    monkeypatch.setattr(jobylon, "get", fake_get)
    hris, tax = jobylon.fetch(SRC_SE)
    assert fetched[0] == "https://cdn.jobylon.com/jobs/companies/1532/embed/v2/?target=jobylon-jobs-widget&page_size=100"
    assert fetched[1:] == ["https://emp.jobylon.com/jobs/1-kpmg-hris-specialist/"]
    assert hris.url == "https://emp.jobylon.com/jobs/1-kpmg-hris-specialist/" and hris.posted == "2026-11-09T14:16:00+00:00"
    assert hris.countries == ["SE"] and run.match_job(hris, ALLOWED)["posted"] == "2026-11-09"
    assert tax.countries == ["SE"] and tax.posted is None


def test_jobylon_cloudflare_bliver_til_klar_fejl(monkeypatch):
    def blocked(url, **kw):
        r = requests.Response()
        r.status_code, r._content = 403, b"<html>Just a moment...</html>"
        r.headers["server"] = "cloudflare"
        raise requests.HTTPError("403", response=r)

    monkeypatch.setattr(jobylon, "get", blocked)
    with pytest.raises(RuntimeError, match="blokeret af Cloudflare"):
        jobylon.fetch(SRC_SE)
    status = run.run_source("KPMG", SRC_SE)[1]
    assert not status["ok"] and "blokeret af Cloudflare" in status["error"]


def test_jobylon_andre_fejl_er_ikke_cloudflare(monkeypatch):
    def gone(url, **kw):
        r = requests.Response()
        r.status_code = 404
        raise requests.HTTPError("404", response=r)

    monkeypatch.setattr(jobylon, "get", gone)
    with pytest.raises(requests.HTTPError):
        jobylon.fetch(SRC_SE)


def test_kpmg_sverige_fixture(monkeypatch):
    monkeypatch.setenv("SCRAPER_REPLAY", str(FIXTURES / "kpmg_sverige"))
    jobs = jobylon.fetch(SRC_SE)
    assert len(jobs) == 8 and all(j.url.startswith("https://emp.jobylon.com/jobs/") and j.countries == ["SE"] for j in jobs)
    assert all("\\u" not in j.title for j in jobs)
    st = run.run_source("KPMG", SRC_SE)[1]
    assert st["ok"] and st["listed"] == 8
