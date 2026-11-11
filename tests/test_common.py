import pytest
import requests

from scraper import common
from scraper.common import RobotsBlocked, jsonld_jobposting, robots_allows


def _html(body):
    return f'<html><head><script type="application/ld+json">{body}</script></head></html>'


def test_jsonld_enkelt():
    jp = jsonld_jobposting(_html('{"@type": "JobPosting", "title": "HRIS Analyst", "datePosted": "2026-11-10"}'))
    assert jp["title"] == "HRIS Analyst"


def test_jsonld_i_graph_og_liste():
    graph = '{"@graph": [{"@type": "WebSite"}, {"@type": "JobPosting", "title": "A"}]}'
    assert jsonld_jobposting(_html(graph))["title"] == "A"
    assert jsonld_jobposting(_html('[{"@type": "Org"}, {"@type": ["Thing", "JobPosting"], "title": "B"}]'))["title"] == "B"


def test_jsonld_mangler_eller_er_ugyldig():
    assert jsonld_jobposting("<html></html>") is None
    assert jsonld_jobposting(_html("{ikke json")) is None
    assert jsonld_jobposting(_html('{"@type": "Organization"}')) is None


class _Resp:
    def __init__(self, text="", status=200):
        self.text, self.status_code = text, status


@pytest.fixture
def fake_robots(monkeypatch):
    def install(text):
        common._ROBOTS.clear()
        monkeypatch.delenv("SCRAPER_REPLAY", raising=False)
        monkeypatch.setattr(common, "http", lambda m, url, **kw: _Resp(text) if text is not None else (_ for _ in ()).throw(
            requests.HTTPError("404")))
    yield install
    common._ROBOTS.clear()


ROBOTS = """
User-agent: *
Disallow: /services/
Disallow: */apply
Disallow: /private$
Allow: /services/public
"""


def test_robots_jokertegn_og_allow(fake_robots):
    fake_robots(ROBOTS)
    assert robots_allows("https://a.example/job/1")
    assert not robots_allows("https://a.example/services/rss")
    assert robots_allows("https://a.example/services/public")        # længste regel vinder
    assert not robots_allows("https://a.example/gb/en/apply")         # `*/apply`
    assert not robots_allows("https://a.example/private")
    assert robots_allows("https://a.example/private/x")               # `$` = kun præcis


def test_robots_404_er_tilladt(fake_robots):
    fake_robots(None)
    assert robots_allows("https://b.example/alt")


def test_robots_forbyder_alt(fake_robots):
    fake_robots("User-agent: *\nDisallow: /\n")
    assert not robots_allows("https://c.example/")


def test_get_rejser_robotsblocked(monkeypatch):
    monkeypatch.delenv("SCRAPER_REPLAY", raising=False)
    common._ROBOTS["https://d.example"] = common._Robots("User-agent: *\nDisallow: /\n")
    monkeypatch.setattr(common._session, "request", lambda *a, **kw: pytest.fail("kaldte netværket trods robots.txt"))
    with pytest.raises(RobotsBlocked):
        common.get("https://d.example/job/1")


def test_optag_og_afspil(tmp_path, monkeypatch):
    common._ROBOTS["https://e.example"] = common._Robots("")
    monkeypatch.setattr(common, "_throttle", lambda url: None)
    monkeypatch.setenv("SCRAPER_RECORD", str(tmp_path))
    r = requests.Response()
    r.status_code, r._content, r.url = 200, b"hej", "https://e.example/x"
    monkeypatch.setattr(common._session, "request", lambda *a, **kw: r)
    assert common.get("https://e.example/x").text == "hej"
    monkeypatch.delenv("SCRAPER_RECORD")
    monkeypatch.setenv("SCRAPER_REPLAY", str(tmp_path))
    monkeypatch.setattr(common._session, "request", lambda *a, **kw: pytest.fail("netværk i replay"))
    assert common.get("https://e.example/x").text == "hej"
    with pytest.raises(requests.ConnectionError):
        common.get("https://e.example/andet")


def test_genforsoeg_ved_429_og_retry_after(monkeypatch):
    common._ROBOTS["https://f.example"] = common._Robots("")
    monkeypatch.delenv("SCRAPER_REPLAY", raising=False)
    monkeypatch.delenv("SCRAPER_RECORD", raising=False)
    monkeypatch.setattr(common, "_throttle", lambda url: None)
    sleeps = []
    monkeypatch.setattr(common.time, "sleep", sleeps.append)
    answers = []
    for status, headers in ((429, {"Retry-After": "999"}), (503, {}), (200, {})):
        r = requests.Response()
        r.status_code, r._content = status, b"ok"
        r.headers.update(headers)
        answers.append(r)
    monkeypatch.setattr(common._session, "request", lambda *a, **kw: answers.pop(0))
    assert common.get("https://f.example/x").status_code == 200
    assert sleeps == [30.0, 5.0]          # Retry-After kappes ved 30 s


def test_en_sekunds_pause_pr_vaert(monkeypatch):
    common._last_call.clear()
    sleeps, now = [], [100.0]
    monkeypatch.setattr(common.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(common.time, "sleep", lambda s: (sleeps.append(round(s, 2)), now.__setitem__(0, now[0] + s)))
    common._throttle("https://g.example/a")
    now[0] += 0.4
    common._throttle("https://g.example/b")       # samme vært → venter resten af sekundet
    common._throttle("https://h.example/a")       # anden vært → ingen ventetid
    assert sleeps == [0.6]
