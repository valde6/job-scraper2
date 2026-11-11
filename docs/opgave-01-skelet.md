# Opgave 1 – Skelet, fælles kode og dataformat

## Mål
En kørsel (`python -m scraper.run`), der læser `config/`, kalder adaptere, filtrerer, fletter med forrige kørsel og skriver
`data/jobs.json` efter kontrakten i `AGENTS.md`. Endnu uden rigtige adaptere – dem laver opgave 2, 5, 6 og 7.

## Baggrund
- `config/settings.yaml` og `config/companies.yaml` findes allerede (lavet af Claude i Cowork). Ret dem ikke, medmindre noget er forkert.
- `../job-scraper/scraper/common.py` har velafprøvet HTTP-kode med optag/afspil af svar (`SCRAPER_RECORD`/`SCRAPER_REPLAY`)
  og `robots_allows()`. Kopiér det, du kan bruge, og skær resten væk.
- Lokalt repo har endnu ingen commits. Remote `origin` (github.com/valde6/job-scraper2) er tomt.

## Det skal laves
1. `requirements.txt` med fastlåste versioner: `requests`, `beautifulsoup4`, `lxml`, `pyyaml` (samme versioner som i
   `../job-scraper/requirements.txt`). `requirements-dev.txt`: `pytest`. `.gitignore` (`__pycache__/`, `.pytest_cache/`, `.venv/`, `.DS_Store`).
2. `scraper/common.py`
   - `get(url, **kw)` / `post(url, **kw)`: User-Agent `Mozilla/5.0 (compatible; job-scraper2/1.0; personal use; +https://github.com/valde6/job-scraper2)`,
     timeout 25 s, 2 genforsøg ved 429/5xx (respektér `Retry-After`, højst 30 s), **mindst 1 s mellem kald til samme vært**.
   - Optag/afspil som i job-scraper (`SCRAPER_RECORD=<mappe>` gemmer svar, `SCRAPER_REPLAY=<mappe>` svarer fra filer).
   - `robots_allows(url) -> bool` med cache pr. vært; robots.txt der giver 404/fejl = tilladt. `get()`/`post()` kalder den selv og
     rejser `RobotsBlocked`, hvis stien er forbudt.
   - `jsonld_jobposting(html) -> dict | None` (schema.org JobPosting, også i `@graph` og lister).
   - `parse_date(text) -> "YYYY-MM-DD" | None`: ISO, unix-sekunder/-millisekunder, `10 Nov 2026`, `10.11.2026`, `Nov 10, 2026`,
     tyske/danske/svenske/finske månedsnavne, "Posted 3 Days Ago"/"today"/"yesterday" (relativt til i dag).
3. `scraper/match.py` (læser `config/settings.yaml` én gang)
   - `title_keywords(title) -> list[str]` – navnene på de søgeord, der matcher titlen.
   - `countries_in(text) -> list[str]` – ISO-koder for de lande i settings, der nævnes. Landekoder (`FI`, `DE`, `GB`, `UK`, `CH`…) må kun
     matche som selvstændigt led adskilt af komma/mellemrum/slut (så `"DE"` ikke rammer "Dear", og `"CH"` ikke "Munich"); navne og byer
     matches som hele ord uden hensyn til store/små bogstaver og accenter.
4. `scraper/model.py`: `RawJob` (dataclass): `title`, `url`, `location` (str), `countries` (list, kan være tom = afgøres af `countries_in(location)`),
   `posted` (str|None), `external_id` (str|None).
5. `scraper/adapters/__init__.py`: register `ADAPTERS = {}` (navn → `fetch`-funktion). Adaptere tilføjes i senere opgaver.
6. `scraper/run.py`
   - CLI: `python -m scraper.run [--only "<virksomhed>"] [--dry-run]` (dry-run skriver ikke filer, printer resultat).
   - For hver virksomhed og kilde: `type: none` → `not_covered` (scope = `label` + værtsnavn, reason = `note`). Ukendt type →
     kildestatus `ok: false, error: "adapter mangler"`. Ellers kald adapteren i `try/except` og tag tid.
   - Match: `title_keywords(title)` ikke tom **og** mindst ét land (fra `RawJob.countries` eller `countries_in(location)`) i settings.
   - Flet med forrige `data/jobs.json` efter reglerne i `AGENTS.md` (first_seen, last_seen, active, date_basis/baseline, fejlende kilde rører
     ikke sine job, oprydning efter `keep_inactive_days`). Ved `--only` røres kun den virksomheds job.
   - Kanonisk url: fjern tracking-/sessionsparametre (`utm_*`, `jsessionid`, `feedId`, `_ga`), behold resten. Dedup på `id`.
   - Skriv `data/jobs.json` (sorteret: aktive først, nyeste dato først; `indent=1`, `ensure_ascii=False`) og en kort opsummering på stdout
     (pr. kilde: ok/fejl, listed, matched).
7. Tests i `tests/`:
   - `test_match.py`: "SAP SuccessFactors Consultant", "Success Factors Specialist", "HRIS Analyst", "Senior HRIS-specialist" matcher;
     "Chris Hansen Assistant", "HR Business Partner" matcher ikke. Lande: "Helsinki, FI" → FI, "London, United Kingdom" → GB,
     "Zürich, ZH, CH" → CH, "Munich, Bavaria, Germany" → DE, "Remote" → [], "Bucharest, Bucharest, RO" → [].
   - `test_parse_date.py` for formaterne ovenfor.
   - `test_run.py` med en falsk adapter (registrér i testen): nyt job får first_seen = i dag; job der forsvinder → `active: false`;
     kilde der fejler → dens job forbliver aktive; første kørsel uden `posted` → `baseline`; `--only` rører ikke andre virksomheder.

## Færdig når
- `python -m pytest -q` er grønt.
- `python -m scraper.run --dry-run` kører igennem og viser alle 22 kilder som "adapter mangler" og KPMG Schweiz under ikke dækket.
- Commit: `Opgave 1: skelet, fælles kode og dataformat`. Afkryds i `docs/OPGAVER.md`. **Ingen push.**

## Ikke i denne opgave
Rigtige adaptere, siden, GitHub Actions.

## Noter fra udførelsen
- **robots.txt-parser er skrevet selv** (`_Robots` i `common.py`) i stedet for `urllib.robotparser`, som ikke forstår jokertegn
  (`*/apply`, `$`). Ricoh og Givaudan bruger dem (se `docs/KILDER.md`), så urllib ville have tilladt stier, der er forbudt.
  Længste regel vinder, `Allow` vinder ved lighed. I afspilningstilstand (`SCRAPER_REPLAY`) tjekkes robots.txt ikke.
- **Nyt felt `last_ok` i `sources[]`** (dato for seneste vellykkede kørsel). Det behøves for at afgøre, om en kørsel er kildens
  *første* vellykkede (baseline) – det kan ikke ses af jobbene alene, hvis kilden ikke har haft match endnu. Feltet er beskrevet i
  `AGENTS.md`; siden ignorerer det, så `schema` er stadig 1.
- **Hvilken kilde et job stammer fra** gemmes ikke (kontrakten har kun `source` = adaptertype). Fejler en kilde, røres derfor alle
  virksomhedens job med samme adaptertype (fx begge SuccessFactors-kilder hos KPMG Tyskland/UK). Det er den sikre side.
- `RawJob.countries` normaliseres (`UK` → `GB`, store bogstaver) og begrænses til landene i settings. Er listen ikke tom, bruges
  `countries_in(location)` ikke.
- `countries_in` returnerer landene i den rækkefølge, de først står i teksten (så `country` = det første, kilden nævner).
- `parse_date("Posted 30+ Days Ago")` giver `None`: "30+" er ikke en dato. Dd/mm/åååå (med skråstreger) understøttes ikke, fordi
  det er tvetydigt.
- `python -m scraper.run` skriver ikke `data/` før første rigtige kørsel; mappen er ikke committet.
- Lokalt kørt i `.venv` (ignoreret af git). Python 3.15 lokalt – koden bruger kun standardfunktioner fra 3.10+.
- Skrevet uden plan mode: sessionen var ikke interaktiv, så en plan kunne ikke godkendes.
