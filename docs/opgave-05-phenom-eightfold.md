# Opgave 5 – Phenom (Ricoh Europe, Givaudan) og Eightfold (Ericsson)

## Mål
Tre kilder mere: `type: phenom` (Ricoh Europe, Givaudan) og `type: eightfold` (Ericsson).

## Baggrund
Se **Phenom** og **Eightfold** i `docs/KILDER.md`. Vigtigt fra robots.txt:
- Givaudan: brug `/global/en` (stien `*/gb/en` er forbudt). Phenom forbyder også `*/apply` og `*/px-widgets` – brug dem ikke.
- Ericsson: alt er forbudt undtagen bl.a. `/careers` og `/api/pcsx`. Brug kun `/api/pcsx/search`.
`robots_allows()` i `common.py` skal fange det, hvis du kommer til at bruge en forbudt sti – lad være med at slå den fra.

## Det skal laves
1. `scraper/adapters/phenom.py`: for hvert søgeord `GET {url}/search-results?keywords={ord}&from={n}&s=1`, læs `phApp.ddo`
   (kopiér `_ddo()` fra `../job-scraper/scraper/adapters/phenom.py`), side for side med `from` += antal indtil `totalHits`.
   `RawJob`: titel, url `{url}/job/{jobId}`, location `"{city}, {country}"`, countries fra `country` og evt. `multi_location`,
   posted fra `postedDate`.
2. `scraper/adapters/eightfold.py`: for hvert søgeord `GET {url}/api/pcsx/search` med `domain`, `query`, `location=""`, `start`,
   `sort_by=timestamp`. Side for side (`start += len(positions)`) indtil ingen flere eller 300. Location = `standardizedLocations`
   sammensat; countries fra landekoden sidst i hver `standardizedLocations`-streng; posted fra `postedTs`; url
   `{url}/careers/job/{id}`.
3. Registrér begge. Optag fixtures for Ricoh Europe og Ericsson og test uden netværk.

## Færdig når
- `python -m scraper.run --only "Ricoh Europe"`, `--only Givaudan` og `--only Ericsson` giver `ok: true`. Noter listed/matched/titler.
  (11/11 fandtes "SAP SuccessFactors Employee Central & Compensation Engineer" hos Ricoh i London.)
- Tests grønne. Commit: `Opgave 5: Phenom og Eightfold`. Afkryds. **Ingen push.**

## Noter fra udførelsen
_(udfyldes af Claude Code)_
