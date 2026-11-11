"""Sundhedstjek efter hver kørsel: opdager kilder, der er gået i stykker, før radaren stille bliver tom.

Læser data/jobs.json (kildestatus fra seneste kørsel), fører historik i data/health.json (14 kørsler pr. kilde)
og skriver data/health_alert.md – men KUN når noget skal ses på. Findes filen ikke, er alt sundt.

    python -m scraper.health

Reglerne (se docs/opgave-08-sundhed.md):
  fejl  – kilden har fejlet i 2 kørsler i træk
  tom   – kilden har haft listed = 0 i 3 kørsler i træk (mulig ændring af siden)
  fald  – listed er under 20 % af medianen for de 7 foregående kørsler med data
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parent.parent
JOBS_FILE = ROOT / "data" / "jobs.json"
HEALTH_FILE = ROOT / "data" / "health.json"
ALERT_FILE = ROOT / "data" / "health_alert.md"

SCHEMA = 1
KEEP = 14               # kørsler i historikken pr. kilde
FAIL_RUNS = 2           # fejl i så mange kørsler i træk
EMPTY_RUNS = 3          # listed = 0 i så mange kørsler i træk
DROP_RATIO = 0.2        # under 20 % af medianen
DROP_WINDOW = 7         # medianen tages over de seneste 7 kørsler med data (før den aktuelle)
DROP_MIN_RUNS = 3       # ... og kræver mindst så mange kørsler med data
DROP_MIN_MEDIAN = 5     # små kilder (median < 5) svinger for meget til, at et fald siger noget

HINTS = {
    "fejl": "åbn karrieresiden og tjek om adressen/systemet er ændret; se docs/KILDER.md",
    "tom": "åbn karrieresiden og tjek om den stadig viser job, og om adapteren stadig læser den rigtige sti; se docs/KILDER.md",
    "fald": "åbn karrieresiden og sammenlign antallet af job med det, scraperen fandt; tjek om siden er bygget om; se docs/KILDER.md",
}


def source_name(source: dict) -> str:
    """Kildens navn i historikken: 'Virksomhed' eller 'Virksomhed – label'."""
    return f"{source['company']} – {source['label']}" if source.get("label") else source["company"]


def _streak(history: list[dict], pred) -> int:
    n = 0
    for entry in reversed(history):
        if not pred(entry):
            break
        n += 1
    return n


def problems(history: list[dict]) -> list[tuple[str, str]]:
    """Problemer for én kilde som [(kode, forklaring)]. history = kørsler, ældste først, nyeste (nu) sidst."""
    found: list[tuple[str, str]] = []
    if not history:
        return found

    fails = _streak(history, lambda h: not h["ok"])
    if fails >= FAIL_RUNS:
        found.append(("fejl", f"fejlet i {fails} kørsler i træk"))

    empties = _streak(history, lambda h: h["ok"] and h["listed"] == 0)
    if empties >= EMPTY_RUNS:
        found.append(("tom", f"listed = 0 i {empties} kørsler i træk"))

    now = history[-1]
    if now["ok"] and now["listed"] is not None:
        earlier = [h["listed"] for h in history[:-1] if h["ok"] and h["listed"] is not None][-DROP_WINDOW:]
        if len(earlier) >= DROP_MIN_RUNS:
            med = median(earlier)
            if med >= DROP_MIN_MEDIAN and now["listed"] < DROP_RATIO * med:
                found.append(("fald", f"listed = {now['listed']} mod en median på {med:g} (de seneste {len(earlier)} kørsler)"))
    return found


def update_history(old: dict, sources: list[dict], day: str) -> dict:
    """Lægger dagens kørsel ind i historikken. Samme dato to gange = den nyeste erstatter den gamle (idempotent)."""
    out: dict[str, list[dict]] = {}
    for s in sources:
        name = source_name(s)
        rows = [r for r in old.get("sources", {}).get(name, []) if r.get("date") != day]
        ok = bool(s.get("ok"))
        rows.append({"date": day, "ok": ok, "listed": s.get("listed") if ok else None})
        out[name] = sorted(rows, key=lambda r: r["date"])[-KEEP:]
    return {"schema": SCHEMA, "sources": out}   # kilder, der ikke længere findes, glemmes


def alert_text(sources: list[dict], health: dict) -> str | None:
    """Teksten til GitHub-issuet, eller None hvis alle kilder er sunde."""
    lines = []
    for s in sources:
        probs = problems(health["sources"][source_name(s)])
        if not probs:
            continue
        codes = ", ".join(code for code, _ in probs)
        detail = "; ".join(text for _, text in probs)
        error = s.get("error") or "ingen (kilden svarer, men giver for lidt)"
        todo = "; ".join(dict.fromkeys(HINTS[code] for code, _ in probs))
        lines.append(f"- **{source_name(s)}** ({s['type']}): {codes} – {detail}. Seneste fejltekst: {error}. Typisk: {todo}.")
    if not lines:
        return None
    return ("Scraperen har kilder, der ser ud til at være gået i stykker:\n\n" + "\n".join(lines)
            + "\n\nHistorik pr. kilde: `data/health.json`. Kildernes adresser og regler: `docs/KILDER.md`.\n")


def main(argv: list[str] | None = None, *, jobs_file: Path = JOBS_FILE, health_file: Path = HEALTH_FILE,
         alert_file: Path = ALERT_FILE) -> int:
    if not jobs_file.exists():
        print(f"{jobs_file} findes ikke – intet at tjekke.", file=sys.stderr)
        return 1
    doc = json.loads(jobs_file.read_text(encoding="utf-8"))
    sources = doc.get("sources", [])
    day = doc["generated_at"][:10]          # kørslens dato, ikke dagens: kører vi to gange på en gammel fil, tæller den kun én gang

    old = json.loads(health_file.read_text(encoding="utf-8")) if health_file.exists() else {}
    health = update_history(old, sources, day)
    health_file.parent.mkdir(parents=True, exist_ok=True)
    health_file.write_text(json.dumps(health, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    text = alert_text(sources, health)
    if text:
        alert_file.write_text(text, encoding="utf-8")
        print(text)
    else:
        alert_file.unlink(missing_ok=True)
        print(f"Alle {len(sources)} kilder er sunde.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
