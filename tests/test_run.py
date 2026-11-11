import json
from datetime import date

import pytest
import yaml

from scraper import adapters, run
from scraper.model import RawJob

DAY1, DAY2, DAY3 = date(2026, 11, 10), date(2026, 11, 11), date(2026, 11, 12)


def raw(title="HRIS Specialist", path="1", loc="Helsinki, FI", posted=None, **kw):
    return RawJob(title=title, url=f"https://x.example/job/{path}", location=loc, posted=posted, **kw)


@pytest.fixture
def env(tmp_path, monkeypatch):
    """To virksomheder med hver sin falske adapter. `state` styrer, hvad adapteren svarer."""
    state = {"A": [], "B": []}

    def fake(source):
        r = state[source["name"]]
        if isinstance(r, Exception):
            raise r
        return r

    monkeypatch.setitem(adapters.ADAPTERS, "fake", fake)
    cfg = tmp_path / "companies.yaml"
    cfg.write_text(yaml.safe_dump({"companies": [
        {"name": "Alfa", "sources": [{"type": "fake", "name": "A"}]},
        {"name": "Beta", "sources": [{"type": "fake", "name": "B"}]},
        {"name": "Gamma", "sources": [{"type": "none", "label": "Schweiz", "url": "https://jobs.g.ch", "note": "forbudt"}]},
    ]}))
    data = tmp_path / "data" / "jobs.json"

    def go(day, *args):
        assert run.main(list(args), companies_file=cfg, data_file=data, today=day) == 0
        return json.loads(data.read_text(encoding="utf-8"))

    return state, go, data


def by_title(doc, title):
    return next(j for j in doc["jobs"] if j["title"] == title)


def test_nyt_job_faar_first_seen_i_dag(env):
    state, go, _ = env
    state["A"] = []
    go(DAY1)                                         # kildens første vellykkede kørsel (tom)
    state["A"] = [raw(path="1")]
    doc = go(DAY2)
    j = doc["jobs"][0]
    assert (j["first_seen"], j["last_seen"], j["active"], j["date_basis"]) == ("2026-11-11", "2026-11-11", True, "first_seen")
    assert j["posted"] is None and j["country"] == "FI" and j["countries"] == ["FI"] and j["source"] == "fake"
    assert len(j["id"]) == 12


def test_job_med_posted_bruger_posted(env):
    state, go, _ = env
    go(DAY1)
    state["A"] = [raw(posted="2026-11-09")]
    j = go(DAY2)["jobs"][0]
    assert (j["posted"], j["date_basis"]) == ("2026-11-09", "posted")


def test_forste_koersel_uden_posted_er_baseline(env):
    state, go, _ = env
    state["A"] = [raw(path="1"), raw(title="SuccessFactors Lead", path="2", posted="2026-11-01")]
    doc = go(DAY1)
    assert by_title(doc, "HRIS Specialist")["date_basis"] == "baseline"
    assert by_title(doc, "SuccessFactors Lead")["date_basis"] == "posted"
    state["A"] += [raw(title="HRIS Analyst", path="3")]
    doc = go(DAY2)                                    # anden kørsel: nyt job uden posted er et rigtigt nyt job
    assert by_title(doc, "HRIS Analyst")["date_basis"] == "first_seen"
    assert by_title(doc, "HRIS Specialist")["date_basis"] == "baseline"
    assert by_title(doc, "HRIS Specialist")["first_seen"] == "2026-11-10"


def test_baseline_gaelder_pr_kilde_ikke_pr_virksomhed(env):
    state, go, _ = env
    state["B"] = RuntimeError("nede")
    go(DAY1)                                          # Alfa lykkes, Beta har aldrig lykkedes
    state["A"] = [raw(path="1")]
    state["B"] = [raw(path="9")]
    doc = go(DAY2)
    assert by_title(doc, "HRIS Specialist")["date_basis"] in ("baseline", "first_seen")
    assert {j["company"]: j["date_basis"] for j in doc["jobs"]} == {"Alfa": "first_seen", "Beta": "baseline"}


def test_forsvundet_job_bliver_inaktivt_og_kan_komme_tilbage(env):
    state, go, _ = env
    state["A"] = [raw(path="1"), raw(title="HRIS Analyst", path="2")]
    go(DAY1)
    state["A"] = [raw(title="HRIS Analyst", path="2")]
    doc = go(DAY2)
    gone = by_title(doc, "HRIS Specialist")
    assert gone["active"] is False and gone["last_seen"] == "2026-11-10"
    assert by_title(doc, "HRIS Analyst")["active"] is True
    assert [j["active"] for j in doc["jobs"]] == [True, False]            # aktive først
    state["A"] = [raw(path="1")]
    back = by_title(go(DAY3), "HRIS Specialist")
    assert back["active"] is True and back["first_seen"] == "2026-11-10" and back["last_seen"] == "2026-11-12"


def test_kilde_der_fejler_roerer_ikke_sine_job(env):
    state, go, _ = env
    state["A"] = [raw(path="1")]
    state["B"] = [raw(title="HRIS Analyst", path="2")]
    go(DAY1)
    state["A"] = RuntimeError("500 Server Error")
    state["B"] = []
    doc = go(DAY2)
    assert by_title(doc, "HRIS Specialist")["active"] is True             # Alfas kilde fejlede
    assert by_title(doc, "HRIS Analyst")["active"] is False               # Betas virkede og er tom
    a = next(s for s in doc["sources"] if s["company"] == "Alfa")
    assert a["ok"] is False and "RuntimeError" in a["error"] and a["last_ok"] == "2026-11-10"


def test_filtrering_soegeord_og_land(env):
    state, go, _ = env
    state["A"] = [raw(title="HR Business Partner", path="1"), raw(path="2", loc="Bucharest, RO"),
                  raw(title="HRIS Analyst", path="3", loc="Remote"),
                  raw(title="HRIS Manager", path="4", loc="Berlin", countries=["de"]),
                  raw(title="HRIS Lead", path="5", loc="Remote", countries=["UK"]),
                  raw(title="HRIS Expert", path="6", loc="Helsinki", countries=["RO"])]
    doc = go(DAY1)
    assert sorted(j["title"] for j in doc["jobs"]) == ["HRIS Lead", "HRIS Manager"]
    assert by_title(doc, "HRIS Lead")["country"] == "GB"
    s = next(s for s in doc["sources"] if s["company"] == "Alfa")
    assert (s["listed"], s["matched"], s["ok"]) == (6, 2, True)


def test_flere_lande_og_dublet(env):
    state, go, _ = env
    state["A"] = [raw(path="1", loc="Berlin | Stockholm | Zürich"), raw(path="1", loc="Berlin")]
    doc = go(DAY1)
    assert len(doc["jobs"]) == 1
    assert doc["jobs"][0]["country"] == "DE" and doc["jobs"][0]["countries"] == ["DE", "SE", "CH"]


def test_only_roerer_ikke_andre_virksomheder(env):
    state, go, _ = env
    state["A"] = [raw(path="1")]
    state["B"] = [raw(title="HRIS Analyst", path="2")]
    first = go(DAY1)
    state["A"], state["B"] = [], RuntimeError("skal ikke kaldes")
    doc = go(DAY2, "--only", "alfa")
    assert by_title(doc, "HRIS Specialist")["active"] is False
    assert by_title(doc, "HRIS Analyst") == by_title(first, "HRIS Analyst")
    assert [s["company"] for s in doc["sources"]] == ["Alfa", "Beta"]
    beta = next(s for s in doc["sources"] if s["company"] == "Beta")
    assert beta["ok"] is True                                              # uændret fra forrige kørsel


def test_only_med_ukendt_navn(env, capsys, tmp_path):
    assert run.main(["--only", "Findes ikke"], companies_file=tmp_path / "companies.yaml",
                    data_file=tmp_path / "x.json") == 2


def test_oprydning_efter_keep_inactive_days(env):
    state, go, _ = env
    state["A"] = [raw(path="1")]
    go(DAY1)
    state["A"] = []
    go(date(2026, 11, 11))                                                 # inaktiv fra nu af
    assert len(go(date(2027, 1, 9))["jobs"]) == 1                          # 59 dage siden last_seen: bliver
    assert go(date(2027, 1, 11))["jobs"] == []                             # 61 dage: slettet


def test_dry_run_skriver_ikke(env, capsys):
    state, go, data = env
    state["A"] = [raw(path="1")]
    run.main(["--dry-run"], companies_file=data.parent.parent / "companies.yaml", data_file=data, today=DAY1)
    assert not data.exists()
    assert "dry-run" in capsys.readouterr().out


def test_not_covered_og_adapter_mangler(tmp_path, capsys):
    cfg = tmp_path / "c.yaml"
    cfg.write_text(yaml.safe_dump({"companies": [
        {"name": "K", "sources": [{"type": "ukendt", "label": "DK"},
                                  {"type": "none", "label": "Schweiz", "url": "https://jobs.kpmg.ch", "note": "robots"}]}]}))
    data = tmp_path / "jobs.json"
    run.main([], companies_file=cfg, data_file=data, today=DAY1)
    doc = json.loads(data.read_text(encoding="utf-8"))
    assert doc["not_covered"] == [{"company": "K", "scope": "Schweiz (jobs.kpmg.ch)", "reason": "robots"}]
    assert doc["sources"][0]["ok"] is False and doc["sources"][0]["error"] == "adapter mangler"
    assert doc["schema"] == 1 and doc["keywords"] == ["SuccessFactors", "HRIS"]
    assert doc["countries"] == ["DK", "SE", "FI", "DE", "GB", "CH"]
    assert "adapter mangler" in capsys.readouterr().out


def test_sortering_aktive_foerst_nyeste_dato_foerst(env):
    state, go, _ = env
    go(DAY1)
    state["A"] = [raw(title="HRIS A", path="1", posted="2026-11-01"), raw(title="HRIS B", path="2", posted="2026-11-08"),
                  raw(title="HRIS C", path="3")]
    state["B"] = [raw(title="HRIS D", path="4", posted="2026-10-01")]
    doc = go(DAY2)
    assert [j["title"] for j in doc["jobs"]] == ["HRIS C", "HRIS B", "HRIS A", "HRIS D"]


@pytest.mark.parametrize("url,expected", [
    ("https://X.example/job/1?utm_source=a&utm_medium=b", "https://x.example/job/1"),
    ("https://x.example/job/1;jsessionid=ABC123?feedId=9&keep=1", "https://x.example/job/1?keep=1"),
    ("https://x.example/job/1?_ga=1.2&jsessionid=z&a=b%20c", "https://x.example/job/1?a=b%20c"),
    ("https://x.example/job/1#apply", "https://x.example/job/1"),
])
def test_kanonisk_url(url, expected):
    assert run.canonical_url(url) == expected


def test_id_er_ens_for_url_med_og_uden_tracking():
    a = run.job_id("Alfa", "https://x.example/job/1?utm_source=z")
    assert a == run.job_id("Alfa", "https://x.example/job/1") and len(a) == 12
    assert a != run.job_id("Beta", "https://x.example/job/1")
