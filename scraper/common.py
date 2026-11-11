"""Fælles hjælpefunktioner: HTTP (høflig, med optag/afspil), robots.txt, JSON-LD og datoer."""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import re
import time
import unicodedata
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

import requests
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (compatible; job-scraper2/1.0; personal use; +https://github.com/valde6/job-scraper2)"
ROBOTS_AGENT = "job-scraper2"
TIMEOUT = 25
MIN_INTERVAL = 1.0          # sekunder mellem kald til samme vært (AGENTS.md regel 1)
MAX_RETRY_WAIT = 30.0

_session = requests.Session()
_session.headers.update({"User-Agent": UA, "Accept-Language": "en,da;q=0.8"})


class RobotsBlocked(Exception):
    """robots.txt forbyder stien. Adaptere må ikke forsøge at omgå det."""


def today_utc() -> date:
    return datetime.now(timezone.utc).date()


# ---------------------------------------------------------------- optag / afspil
# SCRAPER_RECORD=<mappe>  gemmer alle svar (til fixtures i tests/fixtures/)
# SCRAPER_REPLAY=<mappe>  svarer fra gemte filer uden netværk (bruges i tests)
def _fixture_dir(env: str) -> Path | None:
    d = os.environ.get(env)
    return Path(d) if d else None


def request_key(method: str, url: str, kw: dict) -> str:
    body = kw.get("json") if kw.get("json") is not None else kw.get("data")
    raw = json.dumps([method.upper(), url, sorted((kw.get("params") or {}).items()), body],
                     sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def _save_fixture(d: Path, key: str, method: str, url: str, r: requests.Response) -> None:
    d.mkdir(parents=True, exist_ok=True)
    rec = {"method": method, "url": url, "final_url": r.url, "status": r.status_code,
           "content_type": r.headers.get("content-type", ""), "text": r.text}
    (d / f"{key}.json.gz").write_bytes(gzip.compress(json.dumps(rec, ensure_ascii=False).encode()))


def _load_fixture(d: Path, key: str, method: str, url: str) -> requests.Response:
    f = d / f"{key}.json.gz"
    if not f.exists():
        raise requests.ConnectionError(f"REPLAY: intet gemt svar for {method} {url} ({key})")
    rec = json.loads(gzip.decompress(f.read_bytes()))
    r = requests.Response()
    r.status_code, r.url, r.encoding = rec["status"], rec.get("final_url") or url, "utf-8"
    r._content = rec["text"].encode("utf-8")  # noqa: SLF001
    r.headers["content-type"] = rec.get("content_type", "")
    return r


# ---------------------------------------------------------------- HTTP
_last_call: dict[str, float] = {}


def _throttle(url: str) -> None:
    """Mindst MIN_INTERVAL sekunder mellem to kald til samme vært."""
    host = urlsplit(url).netloc.lower()
    wait = MIN_INTERVAL - (time.monotonic() - _last_call.get(host, float("-inf")))
    if wait > 0:
        time.sleep(wait)
    _last_call[host] = time.monotonic()


def _retry_wait(r: requests.Response | None, attempt: int) -> float:
    """Ventetid før næste forsøg: Retry-After (sekunder) hvis den findes, ellers 2, 5, 8 … – aldrig over 30 s."""
    base = 2.0 + attempt * 3
    if r is not None:
        ra = (r.headers.get("Retry-After") or "").strip()
        if ra.isdigit():
            base = max(base, float(ra))
    return min(base, MAX_RETRY_WAIT)


def http(method: str, url: str, *, retries: int = 2, robots: bool = True, **kw) -> requests.Response:
    """Ét HTTP-kald. Tjekker robots.txt (rejser RobotsBlocked), venter 1 s pr. vært og prøver igen ved 429/5xx."""
    replay = _fixture_dir("SCRAPER_REPLAY")
    if replay:
        r = _load_fixture(replay, request_key(method, url, kw), method, url)
        r.raise_for_status()
        return r
    if robots and not robots_allows(url):
        raise RobotsBlocked(f"robots.txt forbyder {url}")
    record = _fixture_dir("SCRAPER_RECORD")
    kw.setdefault("timeout", TIMEOUT)
    last: Exception | None = None
    for attempt in range(retries + 1):
        _throttle(url)
        r = None
        try:
            r = _session.request(method, url, **kw)
            if (r.status_code == 429 or r.status_code >= 500) and attempt < retries:
                time.sleep(_retry_wait(r, attempt))
                continue
            r.raise_for_status()
            if record:
                _save_fixture(record, request_key(method, url, kw), method, url, r)
            return r
        except (requests.ConnectionError, requests.Timeout) as e:
            last = e
            if attempt < retries:
                time.sleep(_retry_wait(None, attempt))
    assert last is not None
    raise last


def get(url: str, **kw) -> requests.Response:
    return http("GET", url, **kw)


def post(url: str, **kw) -> requests.Response:
    return http("POST", url, **kw)


# ---------------------------------------------------------------- robots.txt
# Egen parser, fordi urllib.robotparser ikke forstår jokertegn (`*/apply`, `$`), som bl.a. Ricoh og Givaudan bruger.
class _Robots:
    def __init__(self, text: str):
        groups: list[tuple[list[str], list[tuple[bool, re.Pattern, int]]]] = []
        agents: list[str] = []
        rules: list[tuple[bool, re.Pattern, int]] = []
        in_rules = False
        for line in text.splitlines():
            line = line.split("#", 1)[0].strip()
            if ":" not in line:
                continue
            key, _, val = line.partition(":")
            key, val = key.strip().lower(), val.strip()
            if key == "user-agent":
                if in_rules:
                    groups.append((agents, rules))
                    agents, rules, in_rules = [], [], False
                agents.append(val.lower())
            elif key in ("allow", "disallow"):
                in_rules = True
                if val:   # tom Disallow = alt er tilladt
                    rules.append((key == "allow", self._pattern(val), len(val)))
        if agents:
            groups.append((agents, rules))
        mine = [g for g in groups if any(a and a != "*" and a in ROBOTS_AGENT for a in g[0])]
        star = [g for g in groups if "*" in g[0]]
        self.rules = [r for g in (mine or star) for r in g[1]]

    @staticmethod
    def _pattern(path: str) -> re.Pattern:
        end = path.endswith("$")
        body = re.escape(path.rstrip("$")).replace(r"\*", ".*")
        return re.compile(body + ("$" if end else ""))

    def allows(self, path: str) -> bool:
        best: tuple[int, bool] | None = None
        for allow, pat, length in self.rules:
            if pat.match(path) and (best is None or length > best[0] or (length == best[0] and allow)):
                best = (length, allow)
        return True if best is None else best[1]


_ROBOTS: dict[str, _Robots] = {}


def robots_allows(url: str) -> bool:
    """Må vi hente url? Cache pr. vært. robots.txt, der giver 404 eller fejl, tæller som tilladt."""
    u = urlsplit(url)
    base = f"{u.scheme}://{u.netloc}"
    rb = _ROBOTS.get(base)
    if rb is None:
        try:
            rb = _Robots(http("GET", base + "/robots.txt", retries=0, robots=False).text)
        except Exception:  # noqa: BLE001
            rb = _Robots("")
        _ROBOTS[base] = rb
    return rb.allows((u.path or "/") + (f"?{u.query}" if u.query else ""))


# ---------------------------------------------------------------- tekst og JSON-LD
def clean(s: str | None) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def jsonld_jobposting(html: str) -> dict | None:
    """Første schema.org JobPosting i siden – også inde i @graph og i lister."""
    s = BeautifulSoup(html or "", "lxml")
    for tag in s.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or tag.get_text() or "", strict=False)
        except ValueError:
            continue
        stack = [data]
        while stack:
            it = stack.pop(0)
            if isinstance(it, list):
                stack = it + stack
            elif isinstance(it, dict):
                t = it.get("@type")
                types = t if isinstance(t, list) else [t]
                if "JobPosting" in [str(x) for x in types]:
                    return it
                if "@graph" in it:
                    stack = list(it["@graph"]) + stack
    return None


# ---------------------------------------------------------------- datoer
# Månedsnavne: eksakte ord (engelsk, tysk, dansk, svensk) + finske stammer (tammikuuta, marraskuun …)
_MONTH_WORDS = {
    **{w: 1 for w in ("jan", "january", "januar", "januari")},
    **{w: 2 for w in ("feb", "february", "februar", "februari")},
    **{w: 3 for w in ("mar", "march", "mär", "mrz", "märz", "marts", "mars")},
    **{w: 4 for w in ("apr", "april")},
    **{w: 5 for w in ("may", "mai", "maj")},
    **{w: 6 for w in ("jun", "june", "juni")},
    **{w: 7 for w in ("jul", "july", "juli")},
    **{w: 8 for w in ("aug", "august", "augusti")},
    **{w: 9 for w in ("sep", "sept", "september")},
    **{w: 10 for w in ("oct", "okt", "october", "oktober")},
    **{w: 11 for w in ("nov", "november")},
    **{w: 12 for w in ("dec", "dez", "december", "dezember")},
}
_FI_STEMS = [("tammi", 1), ("helmi", 2), ("maalis", 3), ("huhti", 4), ("touko", 5), ("kesä", 6), ("heinä", 7),
             ("elo", 8), ("syys", 9), ("loka", 10), ("marras", 11), ("joulu", 12)]


def _month(word: str) -> int | None:
    w = word.lower().rstrip(".")
    if w in _MONTH_WORDS:
        return _MONTH_WORDS[w]
    for stem, n in _FI_STEMS:
        if w.startswith(stem) and len(w) > 4:
            return n
    return None


_WORD = r"([^\W\d_]+\.?)"
_RE_ISO = re.compile(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)")
_RE_DMY_NUM = re.compile(r"(?<!\d)(\d{1,2})\.\s?(\d{1,2})\.\s?(\d{4})(?!\d)")
_RE_D_MON_Y = re.compile(r"(?<!\d)(\d{1,2})(?:st|nd|rd|th)?\.?\s+(?:of\s+)?" + _WORD + r",?\s+(\d{4})(?!\d)", re.I)
_RE_MON_D_Y = re.compile(_WORD + r"\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})(?!\d)", re.I)
_RE_AGO = re.compile(r"(\d+)(\+)?\s*(?:days?|dage|dagar|tagen?|päivää)\s+(?:ago|siden|sedan|sitten)\b|\bvor\s+(\d+)(\+)?\s+tagen?\b", re.I)
_TODAY_WORDS = re.compile(r"\b(?:today|heute|i\s*dag|idag|tänään|just\s+posted)\b|\b\d+\s*(?:hours?|minutes?)\s+ago\b", re.I)
_YESTERDAY_WORDS = re.compile(r"\b(?:yesterday|gestern|i\s*går|igår|eilen)\b", re.I)


def _ymd(y: int, m: int, d: int) -> str | None:
    try:
        return date(y, m, d).isoformat()
    except ValueError:
        return None


def parse_date(text, today: date | None = None) -> str | None:
    """Alt, kilderne kalder en dato → "YYYY-MM-DD", ellers None.

    ISO (også med klokkeslæt), unix-sekunder/-millisekunder, `10 Nov 2026`, `10.11.2026`, `Nov 10, 2026`, månedsnavne på
    engelsk/tysk/dansk/svensk/finsk og relative udtryk ("Posted 3 Days Ago", "today", "yesterday").
    "Posted 30+ Days Ago" giver None – "30+" er ikke en dato."""
    if text is None or isinstance(text, bool):
        return None
    today = today or today_utc()
    if isinstance(text, (int, float)) or re.fullmatch(r"\s*\d{9,13}\s*", str(text)):
        n = float(text)
        if n > 1e11:          # millisekunder
            n /= 1000
        try:
            return datetime.fromtimestamp(n, timezone.utc).date().isoformat()
        except (OverflowError, OSError, ValueError):
            return None
    s = unicodedata.normalize("NFC", str(text)).strip()
    if not s:
        return None
    if m := _RE_ISO.search(s):
        return _ymd(*(int(g) for g in m.groups()))
    if m := _RE_DMY_NUM.search(s):
        d, mo, y = (int(g) for g in m.groups())
        return _ymd(y, mo, d)
    for m in _RE_D_MON_Y.finditer(s):
        if mo := _month(m.group(2)):
            return _ymd(int(m.group(3)), mo, int(m.group(1)))
    for m in _RE_MON_D_Y.finditer(s):
        if mo := _month(m.group(1)):
            return _ymd(int(m.group(3)), mo, int(m.group(2)))
    if m := _RE_AGO.search(s):
        n, plus = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
        return None if plus else (today - timedelta(days=int(n))).isoformat()
    if _YESTERDAY_WORDS.search(s):
        return (today - timedelta(days=1)).isoformat()
    if _TODAY_WORDS.search(s):
        return today.isoformat()
    return None
