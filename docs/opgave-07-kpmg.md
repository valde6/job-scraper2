# Opgave 7 – KPMG Danmark, Finland og Sverige

## Mål
De sidste tre kilder: `type: hrmanager` (KPMG Danmark), `type: oracle` (KPMG Finland) og `type: jobylon` (KPMG Sverige).
KPMG Tyskland og UK virker allerede via SuccessFactors (opgave 2). KPMG Schweiz må ikke scrapes.

## Baggrund
Se **KPMG** i `docs/KILDER.md`. Kopiér gerne `hrmanager.py` og `oracle.py` fra `../job-scraper/scraper/adapters/`, men tilpas til
`fetch(source) -> list[RawJob]` og fjern studiejob-logikken.

## Det skal laves
1. `scraper/adapters/hrmanager.py` (config `customer`). Hent alle opslag for kunden, url = opslagets offentlige adresse, posted fra
   kildens dato-felt.
2. `scraper/adapters/oracle.py` (config `url`, `site`): REST-kaldet fra KILDER.md for hvert søgeord, side for side med `offset`.
   url = `{url}/hcmUI/CandidateExperience/en/sites/{site}/job/{Id}`, location = `PrimaryLocation`, countries fra
   `PrimaryLocationCountry` (+ `secondaryLocations`), posted = `PostedDate`.
3. `scraper/adapters/jobylon.py` (config `company_id`): hent embed-siden, træk `JBL.embed_v2['jobs']`-listen ud (JS, ikke JSON:
   parse `id`, `url`, `title` med regex pr. objekt). Kun for titler der matcher: hent jobsiden for JSON-LD (`datePosted`, location).
   Alle KPMG Sverige-job er i Sverige → countries `["SE"]`, hvis JSON-LD ikke siger andet.
   Får du 403 eller en Cloudflare-side: lad kilden fejle med en klar fejltekst ("blokeret af Cloudflare") – ingen omgåelse. Virker
   det ikke fra din maskine, så skriv det i noterne og lad `type: jobylon` stå (måske virker det fra GitHub).
4. Registrér alle tre. Fixtures for de kilder, der virker.

## Færdig når
- `python -m scraper.run --only KPMG` viser alle fem KPMG-kilder; Schweiz under "ikke dækket". Noter resultatet pr. kilde.
- Hele kørslen (`python -m scraper.run`) har nu ingen "adapter mangler".
- Tests grønne. Commit: `Opgave 7: KPMG Danmark, Finland og Sverige`. Afkryds. **Ingen push.**

## Noter fra udførelsen
_(udfyldes af Claude Code)_
