import json
import re

import pytest

from scraper.build_page import TEMPLATE_FILE, build, render

MARKER = re.compile(r'<script type="application/json" id="jobdata">.*?</script>', re.S)


def _job(i, title, active=True):
    return {"id": f"id{i}", "company": "Æblerød A/S", "title": title, "url": f"https://x.test/{i}", "location": "København, DK",
            "country": "DK", "countries": ["DK"], "posted": "2026-11-10", "first_seen": "2026-11-11", "last_seen": "2026-11-11",
            "active": active, "date_basis": "posted", "source": "successfactors"}


@pytest.fixture
def built(tmp_path):
    data = {"schema": 1, "generated_at": "2026-11-11T04:20:00+00:00", "keywords": ["HRIS"], "countries": ["DK"],
            "jobs": [_job(1, "HRIS Specialist"), _job(2, "SuccessFactors </script><b>æøå"), _job(3, "Gammelt HRIS-job", active=False)],
            "sources": [{"company": "Æblerød A/S", "label": None, "type": "successfactors", "ok": True, "listed": 5,
                         "matched": 2, "error": None, "seconds": 1.0, "last_ok": "2026-11-11"}],
            "not_covered": [{"company": "KPMG", "scope": "Schweiz", "reason": "robots.txt"}]}
    src = tmp_path / "jobs.json"
    src.write_text(json.dumps(data), encoding="utf-8")
    out = build(src, TEMPLATE_FILE, tmp_path / "out" / "jobradar.html")
    return out.read_text(encoding="utf-8")


def _payload(html):
    body = re.search(r'id="jobdata">(.*?)</script>', html, re.S).group(1)
    return json.loads(body)


def test_starter_med_titel(built):
    assert built.startswith("<title>HRIS-jobradar</title>")


def test_json_kan_parses_og_inaktive_mangler(built):
    p = _payload(built)
    assert [j["title"] for j in p["jobs"]] == ["HRIS Specialist", "SuccessFactors </script><b>æøå"]
    assert "last_seen" not in p["jobs"][0] and "source" not in p["jobs"][0]
    assert set(p["sources"][0]) == {"company", "label", "ok", "matched", "error"}
    assert p["not_covered"][0]["company"] == "KPMG"


def test_script_afslutning_er_escapet(built):
    assert "</script><b>" not in built
    assert "<\\/script><b>æøå" in built


def test_resten_er_identisk_med_skabelonen(built):
    template = TEMPLATE_FILE.read_text(encoding="utf-8")
    assert MARKER.sub("X", built) == MARKER.sub("X", template)


def test_manglende_datafil_giver_tom_struktur(tmp_path):
    out = build(tmp_path / "findes-ikke.json", TEMPLATE_FILE, tmp_path / "o.html")
    p = _payload(out.read_text(encoding="utf-8"))
    assert p["generated_at"] is None and p["jobs"] == []


def test_manglende_markoer_fejler():
    with pytest.raises(ValueError):
        render("<title>x</title>", {})
