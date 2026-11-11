"""Kører kilderne, filtrerer, fletter med forrige kørsel og skriver data/jobs.json (kontrakten står i AGENTS.md).

    python -m scraper.run [--only "<virksomhed>"] [--dry-run]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

import yaml

from scraper import adapters
from scraper.common import parse_date, today_utc
from scraper.match import country_codes, countries_in, keyword_names, settings, title_keywords
from scraper.model import RawJob

ROOT = Path(__file__).resolve().parent.parent
COMPANIES_FILE = ROOT / "config" / "companies.yaml"
DATA_FILE = ROOT / "data" / "jobs.json"
SCHEMA = 1

_TRACKING_KEYS = {"jsessionid", "feedid", "_ga"}
_JSESSION_PATH = re.compile(r";jsessionid=[^/?#]*", re.I)


# ---------------------------------------------------------------- url og id
def canonical_url(url: str) -> str:
    """Url uden tracking- og sessionsparametre (utm_*, jsessionid, feedId, _ga) og uden #fragment."""
    p = urlsplit(url.strip())
    query = [kv for kv in p.query.split("&") if kv
             and (k := kv.split("=", 1)[0].lower()) not in _TRACKING_KEYS and not k.startswith("utm_")]
    path = _JSESSION_PATH.sub("", p.path)
    out = f"{p.scheme.lower()}://{p.netloc.lower()}{path}"
    return out + ("?" + "&".join(query) if query else "")


def job_id(company: str, url: str) -> str:
    return hashlib.sha1(f"{company}|{canonical_url(url)}".encode()).hexdigest()[:12]


# ---------------------------------------------------------------- kilder
def source_key(company: str, source: dict) -> tuple[str, str | None]:
    return company, source.get("label")


def not_covered_entry(company: str, source: dict) -> dict:
    host = urlsplit(source.get("url") or "").netloc
    scope = " ".join(x for x in (source.get("label"), f"({host})" if host else "") if x) or company
    return {"company": company, "scope": scope, "reason": source.get("note") or "ikke dækket"}


def run_source(company: str, source: dict) -> tuple[list[RawJob] | None, dict]:
    """Kalder adapteren. Fejl bliver til kildestatus, de vælter ikke kørslen (AGENTS.md regel 5)."""
    status = {"company": company, "label": source.get("label"), "type": source["type"], "ok": False,
              "listed": 0, "matched": 0, "error": None, "seconds": 0.0,
              "allow_empty": bool(source.get("allow_empty"))}
    fetch = adapters.ADAPTERS.get(source["type"])
    if fetch is None:
        status["error"] = "adapter mangler"
        return None, status
    t0 = time.monotonic()
    try:
        raw = list(fetch(dict(source)))
        status.update(ok=True, listed=len(raw))
    except Exception as e:  # noqa: BLE001
        raw = None
        status["error"] = f"{type(e).__name__}: {e}"[:300]
    status["seconds"] = round(time.monotonic() - t0, 1)
    return raw, status


def match_job(raw: RawJob, allowed: list[str]) -> dict | None:
    """Et match = søgeord i titlen og mindst ét land fra settings. Returnerer felterne til jobbet, ellers None."""
    if not raw.title or not raw.url or not title_keywords(raw.title):
        return None
    if raw.countries:
        found = [("GB" if c.upper() == "UK" else c.upper()) for c in raw.countries]
    else:
        found = countries_in(raw.location)
    countries = [c for c in dict.fromkeys(found) if c in allowed]
    if not countries:
        return None
    return {"title": raw.title.strip(), "url": canonical_url(raw.url), "location": (raw.location or "").strip(),
            "country": countries[0], "countries": countries, "posted": parse_date(raw.posted)}


# ---------------------------------------------------------------- fletning
def merge(previous: list[dict], results: list[dict], today: date, keep_inactive_days: int,
          run_companies: set[str], prev_sources: list[dict]) -> list[dict]:
    """Fletter nye resultater ind i forrige kørsels job.

    results: [{"company", "source": kilde-dict, "ok": bool, "jobs": [match_job-dict]}] for de kørte virksomheder."""
    iso = today.isoformat()
    jobs = {j["id"]: dict(j) for j in previous}
    last_ok = {(s["company"], s.get("label")): s.get("last_ok") for s in prev_sources}
    seen: set[str] = set()
    failed_types = {(r["company"], r["source"]["type"]) for r in results if not r["ok"]}

    for r in results:
        if not r["ok"]:
            continue
        first_success = last_ok.get(source_key(r["company"], r["source"])) is None
        for m in r["jobs"]:
            jid = job_id(r["company"], m["url"])
            if jid in seen:                       # samme opslag to gange: første vinder
                continue
            seen.add(jid)
            job = jobs.get(jid)
            if job is None:
                basis = "posted" if m["posted"] else ("baseline" if first_success else "first_seen")
                job = {"id": jid, "company": r["company"], "first_seen": iso, "date_basis": basis, "posted": None}
                jobs[jid] = job
            elif m["posted"] and job.get("date_basis") != "posted":
                job["date_basis"] = "posted"
            job.update(title=m["title"], url=m["url"], location=m["location"], country=m["country"],
                       countries=m["countries"], last_seen=iso, active=True, source=r["source"]["type"])
            if m["posted"]:
                job["posted"] = m["posted"]

    for jid, job in jobs.items():
        if jid in seen or job["company"] not in run_companies:
            continue
        if (job["company"], job.get("source")) in failed_types:
            continue                              # kilden fejlede: dens job røres ikke
        job["active"] = False

    cutoff = (today - timedelta(days=keep_inactive_days)).isoformat()
    kept = [j for j in jobs.values()
            if j["active"] or j["company"] not in run_companies or j["last_seen"] >= cutoff]
    kept.sort(key=lambda j: (not j["active"], _neg(j.get("posted") or j["first_seen"]), j["company"], j["title"]))
    return [_ordered(j) for j in kept]


def _neg(d: str) -> str:
    """Nyeste dato først, når der sorteres stigende: vend cifrene om (9-komplement)."""
    return "".join(str(9 - int(c)) if c.isdigit() else c for c in d)


_JOB_FIELDS = ["id", "company", "title", "url", "location", "country", "countries", "posted", "first_seen",
               "last_seen", "active", "date_basis", "source"]


def _ordered(job: dict) -> dict:
    return {k: job.get(k) for k in _JOB_FIELDS}


# ---------------------------------------------------------------- hovedprogram
def load_json(path: Path) -> dict:
    if not path.exists():
        return {"jobs": [], "sources": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError as e:
        raise SystemExit(f"{path} er ikke gyldig JSON ({e}). Ret eller slet filen – jeg overskriver den ikke.") from e


def build(companies: list[dict], previous: dict, today: date, only: str | None = None) -> tuple[dict, list[str]]:
    """Kører kilderne og returnerer (nyt dokument, linjer til stdout)."""
    st = settings()
    allowed = country_codes()
    run_names = {c["name"] for c in companies if only is None or c["name"].lower() == only.lower()}
    prev_sources = previous.get("sources", [])
    results, statuses, lines, not_covered = [], [], [], []

    for comp in companies:
        name = comp["name"]
        for src in comp["sources"]:
            if src["type"] == "none":
                not_covered.append(not_covered_entry(name, src))
                continue
            if name not in run_names:
                continue
            raw, status = run_source(name, src)
            matched = []
            if raw is not None:
                for rj in raw:
                    try:
                        if (m := match_job(rj, allowed)) is not None:
                            matched.append(m)
                    except Exception as e:  # noqa: BLE001  – ét dårligt opslag vælter ikke kilden
                        lines.append(f"  ! {name}: sprang opslag over ({type(e).__name__}: {e})")
                status["matched"] = len(matched)
            old = next((s for s in prev_sources if source_key(s["company"], s) == source_key(name, src)), None)
            status["last_ok"] = today.isoformat() if status["ok"] else (old or {}).get("last_ok")
            statuses.append(status)
            results.append({"company": name, "source": src, "ok": status["ok"], "jobs": matched})
            label = f" {src['label']}" if src.get("label") else ""
            lines.append(f"{'ok ' if status['ok'] else 'FEJL'}  {name}{label} [{src['type']}]  "
                         f"listed={status['listed']} matched={status['matched']}"
                         + (f"  ({status['error']})" if status["error"] else ""))

    jobs = merge(previous.get("jobs", []), results, today, st["keep_inactive_days"], run_names, prev_sources)

    order = {c["name"]: i for i, c in enumerate(companies)}
    kept_sources = [s for s in prev_sources if s["company"] not in run_names and s["company"] in order]
    all_sources = sorted(kept_sources + statuses, key=lambda s: order[s["company"]])
    doc = {"schema": SCHEMA, "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "keywords": keyword_names(), "countries": allowed, "jobs": jobs,
           "sources": all_sources, "not_covered": not_covered}
    for nc in not_covered:
        lines.append(f"ikke dækket  {nc['company']} – {nc['scope']}: {nc['reason']}")
    active = sum(1 for j in jobs if j["active"])
    lines.append(f"{len(statuses)} kilder kørt, {sum(1 for s in statuses if s['ok'])} ok; "
                 f"{len(jobs)} job i alt, {active} aktive")
    return doc, lines


def main(argv: list[str] | None = None, *, companies_file: Path = COMPANIES_FILE, data_file: Path = DATA_FILE,
         today: date | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m scraper.run", description="Hent HRIS-/SuccessFactors-job.")
    ap.add_argument("--only", metavar="VIRKSOMHED", help="kør kun denne virksomhed (navn som i companies.yaml)")
    ap.add_argument("--dry-run", action="store_true", help="skriv ingen filer, print kun resultatet")
    args = ap.parse_args(argv)

    companies = yaml.safe_load(companies_file.read_text(encoding="utf-8"))["companies"]
    if args.only and args.only.lower() not in {c["name"].lower() for c in companies}:
        print(f"Ukendt virksomhed: {args.only!r}. Kendte: {', '.join(c['name'] for c in companies)}", file=sys.stderr)
        return 2

    doc, lines = build(companies, load_json(data_file), today or today_utc(), args.only)
    print("\n".join(lines))
    if args.dry_run:
        print("(dry-run: data/jobs.json er ikke skrevet)")
        return 0
    data_file.parent.mkdir(parents=True, exist_ok=True)
    tmp = data_file.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(data_file)
    print(f"Skrev {data_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
