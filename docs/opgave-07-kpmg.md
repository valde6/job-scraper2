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
`python -m scraper.run --only KPMG` (11/11-2026) – alle fem kilder ok, Schweiz under "ikke dækket":
- **Danmark (hrmanager):** listed 14, matched 0 (ingen HRIS-/SuccessFactors-titler lige nu).
- **Finland (oracle):** listed 0, matched 0. Oracles `keyword=` filtrerer rigtigt (uden ord: 8 opslag i alt, ingen relevante).
- **Sverige (jobylon):** listed 8, matched 0. **Ingen Cloudflare-blokering fra min maskine** (embed-siden og en jobside gav 200), men fra GitHub kan
  det stadig ske; så fejler kilden med "blokeret af Cloudflare (HTTP 403)" (testet med håndskrevet svar).
- **Tyskland (successfactors):** listed 370, matched 1 ("Senior Consultant SAP SuccessFactors / HCM (w/m/d)", Berlin). **UK:** listed 6, matched 0.
- Hele kørslen: 22 kilder, 22 ok, 3 aktive job (Bertelsmann, KPMG Tyskland, Ricoh Europe London) – ingen "adapter mangler".

Bemærkninger:
- **HR-Manager:** alle opslag hentes (`take=200`) og filtreres i run.py. Dato = `Published`, ellers `Created` (`/Date(ms+tz)/` → ms, som `parse_date` forstår).
  Land fra `Department.Country`/`DepartmentTree.Country` ("Danmark"), så byer uden alias i settings.yaml (fx Odense er aliaseret, Esbjerg ikke) stadig får DK.
- **Oracle:** `keyword={ord}` uden anførselstegn (som i opgaveteksten), `limit=25`, `offset` += antal. Land = `PrimaryLocationCountry` (ISO) + lande fra stednavne.
- **Jobylon:** joblisten er JS; `id`/`url`/`title` hentes med regex pr. objekt, og JS-escapes (`\u002D`, `\u0026`) afkodes. Jobsiden (emp.jobylon.com) hentes kun ved titelmatch.
  Er stedet ikke genkendeligt som et land i settings.yaml, bruges `["SE"]` (et job i fx Oslo ville altså fejlagtigt få SE; ikke set i dag).
  Findes `JBL.embed_v2['jobs']` slet ikke (sidens form er ændret, eller det er en bot-mur uden 403), fejler kilden med en klar tekst i stedet for at give 0 job.
- `hrmanager.py` og `oracle.py` er skrevet til `fetch(source) -> list[RawJob]` uden studiejob-logik (ikke kopieret 1:1). `jobylon.py` genbruger `parse_jobpage()` fra successfactors.py.
- Fixtures: `tests/fixtures/kpmg_danmark`, `kpmg_finland`, `kpmg_sverige` (optaget pr. kilde, ikke for hele KPMG, så SuccessFactors-sitemap'en ikke fylder). Match-stierne testes med håndskrevne svar,
  fordi ingen af de optagede svar indeholder et match.
- `data/jobs.json` og `site/jobradar.html` er genbygget efter den fulde kørsel og committet med.
