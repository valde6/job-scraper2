# AGENTS.md – til kode-agenter

## Hvad projektet er
**HRIS-jobradar**: finder nye stillinger med **SuccessFactors** eller **HRIS** i titlen hos 18 virksomheder
(se `config/companies.yaml`) i DK, SE, FI, DE, UK og CH. GitHub Actions kører scraperen hver morgen og skriver
`data/jobs.json` og en færdig side `site/jobradar.html`, som en planlagt Cowork-opgave udgiver som delbart Claude-artefakt.

Søsterprojektet `../job-scraper` (studiejob) har mange færdige adaptere. Kopiér gerne derfra, men hold koden her enkel:
vi har to søgeord og 18 virksomheder, ikke hundredvis.

## Kort over koden (når opgave 1-4 er lavet)
| Fil | Ansvar |
|---|---|
| `config/settings.yaml` | Søgeord (regex på titel), lande med aliaser, oprydning |
| `config/companies.yaml` | Virksomheder → én eller flere kilder (`type` vælger adapter) |
| `scraper/common.py` | HTTP (UA, retries, pause pr. vært, optag/afspil), robots.txt, JSON-LD-hjælpere |
| `scraper/match.py` | `title_keywords(title)`, `countries_in(text)` – den eneste definition af et match |
| `scraper/adapters/<type>.py` | `fetch(source: dict) -> list[RawJob]` – én adapter pr. system |
| `scraper/run.py` | Kører kilderne, filtrerer, fletter med forrige kørsel, skriver `data/jobs.json` |
| `scraper/build_page.py` | Indsætter data i `site/template.html` → `site/jobradar.html` |
| `scraper/health.py` | Sundhedstjek: historik i `data/health.json`, alarmtekst i `data/health_alert.md` (bliver til GitHub-issue) |
| `site/template.html` | Artefaktets side (design er færdigt – ret kun når en opgave siger det) |
| `docs/` | Opgaver, kilder, arbejdsmåde |

## Datakontrakt: `data/jobs.json`
```json
{
  "schema": 1,
  "generated_at": "2026-11-12T04:20:00+00:00",
  "keywords": ["SuccessFactors", "HRIS"],
  "countries": ["DK", "SE", "FI", "DE", "GB", "CH"],
  "jobs": [{
    "id": "a1b2c3d4e5f6",              // sha1(company + "|" + kanonisk url)[:12]
    "company": "Wärtsilä",             // navnet fra companies.yaml
    "title": "HRIS Specialist",
    "url": "https://careers.wartsila.com/job/…/1450503233/",
    "location": "Helsinki, FI",        // som kilden skriver det
    "country": "FI",                   // første matchende land
    "countries": ["FI"],               // alle matchende lande
    "posted": "2026-11-10",            // kildens opslagsdato (YYYY-MM-DD) eller null
    "first_seen": "2026-11-12",
    "last_seen": "2026-11-12",
    "active": true,
    "date_basis": "posted",            // "posted" | "first_seen" | "baseline"
    "source": "successfactors"
  }],
  "sources": [{"company": "KPMG", "label": "Tyskland", "type": "successfactors", "ok": true,
               "listed": 25, "matched": 1, "error": null, "seconds": 2.1, "last_ok": "2026-11-12"}],
  "not_covered": [{"company": "KPMG", "scope": "Schweiz (jobs.kpmg.ch)", "reason": "robots.txt forbyder al automatisk adgang"}]
}
```
- **Dato for "nyt job"** = `posted`, ellers `first_seen`. Job uden `posted`, som blev fundet ved en kildes **første** vellykkede
  kørsel, får `date_basis: "baseline"` og tæller ikke som nye (ellers ville alt se nyt ud på dag 1).
- Et job, der ikke længere vises af en kilde, der **virkede**, sættes `active: false`. Fejler kilden, røres dens job ikke.
- Inaktive job slettes efter `keep_inactive_days`.
- `sources[].last_ok` = datoen for kildens seneste vellykkede kørsel (`null` = aldrig). Er den `null`, er næste vellykkede kørsel kildens
  **første** (baseline). Feltet er tilføjet i opgave 1; siden ignorerer det, så `schema` er uændret. En kildes job kendes på
  `company` + `source` (adaptertypen); fejler en kilde, røres alle virksomhedens job med samme adaptertype.
- Siden (`site/template.html`) læser præcis disse felter. Ændrer du kontrakten, så hæv `schema` og ret siden i samme opgave.

## Regler
1. **Respektér robots.txt** (tjek før hver ny sti; `robots_allows()` i `common.py`). Lav frekvens: højst ét kald pr. sekund pr. vært.
   Ingen omgåelse af bot-mure, CAPTCHA eller login. Se `docs/KILDER.md` for hvad hver side tillader.
2. **Officielle JSON-API'er/feeds før HTML, HTML før browser.** Ingen Playwright i dette projekt.
3. **Én adapter pr. system, ikke pr. virksomhed.** Ny virksomhed på et kendt system = kun en linje i `companies.yaml`.
4. **Filtrering sker ét sted** (`match.py` + `run.py`). Adaptere må søge efter søgeordene for at spare kald, men afgør ikke selv, om et job er et match.
5. Ét opslag, der fejler, må ikke vælte kilden; én kilde, der fejler, må ikke vælte kørslen.
6. Tests: `python -m pytest -q` skal være grønt. Adaptere testes med optagede svar i `tests/fixtures/` (ingen netværk i tests).
7. Ingen hemmeligheder i repoet. Commit-beskeder på dansk. **Push aldrig** (se `ARBEJDSMAADE.md`).
