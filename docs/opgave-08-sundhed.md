# Opgave 8 – Sundhedstjek og alarm

## Mål
Valdemar får besked, hvis en kilde går i stykker, i stedet for at radaren stille og roligt bliver tom.

## Baggrund
Mønstret findes i `../job-scraper/scraper/health.py` og trinnet "Alarm som GitHub-issue" i `../job-scraper/.github/workflows/scrape.yml`.
Hold det meget mindre: 22 kilder.

## Det skal laves
1. `data/health.json`: historik pr. kilde over de seneste 14 kørsler (dato, ok, listed).
2. `scraper/health.py`: skriv `data/health_alert.md`, hvis en kilde
   - har fejlet i 2 kørsler i træk, eller
   - har `listed: 0` i 3 kørsler i træk (mulig ændring af siden), eller
   - har under 20 % af sin median for `listed` (de seneste 7 kørsler med data).
   Teksten: én linje pr. kilde med virksomhed, kilde, problem, seneste fejltekst og hvad der typisk skal gøres
   ("åbn karrieresiden og tjek om adressen/systemet er ændret; se docs/KILDER.md").
3. Workflowet: kør `python -m scraper.health` efter scrape; opret/kommentér/luk et GitHub-issue med label `scraper-health`
   (som i job-scraper; `permissions: issues: write`).
4. Tests for de tre regler.

## Færdig når
- Tests grønne. Commit: `Opgave 8: sundhedstjek og alarm`. Afkryds. **Ingen push.**

## Noter fra udførelsen
_(udfyldes af Claude Code)_
