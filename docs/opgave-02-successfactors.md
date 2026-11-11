# Opgave 2 – SuccessFactors-adapter (13 kilder)

## Mål
`scraper/adapters/successfactors.py`, så alle kilder med `type: successfactors` i `config/companies.yaml` virker:
Ambu, Lundbeck, Novo Nordisk, Wärtsilä, Demant, Søstrene Grene, Bygma, Bertelsmann, DSV, Coloplast, Swiss Re, KPMG Tyskland, KPMG UK.

## Baggrund
Læs afsnittet **SuccessFactors Career Site Builder** i `docs/KILDER.md` (søgeside, to sitemap-varianter, jobside, robots.txt).
`/services/` er forbudt i robots.txt – brug derfor ikke RSS-feeds under `/services/rss/`.

## Det skal laves
1. `fetch(source) -> list[RawJob]`, config: `url` (CSB-domænet).
2. **Primært: søgesiden** for hvert søgeord i settings (`SuccessFactors`, `HRIS`):
   `{url}/search/?q={ord}&locationsearch=&sortColumn=referencedate&sortDirection=desc&startrow={n}`.
   - Parse `tr.data-row` (titel, href, `.jobLocation`, `.jobDate`). Fallback hvis der ikke er rækker: alle `a[href*='/job/']`.
   - Sidetal: fortsæt med `startrow` så længe der kommer nye rækker og "of N" ikke er nået (loft 300).
   - Dedup på job-id (tallet i adressen) på tværs af søgeord.
3. **Kun for job hvis titel matcher** (`match.title_keywords`): mangler dato, eller står der `+N more…`/ingen land i lokationen, så hent jobsiden
   og brug JSON-LD (`datePosted`, alle `jobLocation`-adresser → `countries`). Højst 30 jobsider pr. kilde.
4. **Fallback til `/sitemap.xml`**, hvis søgesiden svarer med fejl eller ikke kan parses (ikke hvis den bare giver 0 resultater):
   RSS-varianten (`<item>`, `<g:location>`) og `<urlset>`-varianten (titel fra adressens slug; jobside for land/dato). Del parsingen
   i små funktioner, så de kan testes hver for sig.
5. Registrér adapteren i `scraper/adapters/__init__.py`.
6. Fixtures: `python -m scraper.record` (lav et lille script, der kører én virksomhed med `SCRAPER_RECORD=tests/fixtures/<navn>`) for
   **Wärtsilä** og **Bertelsmann**. Test i `tests/test_successfactors.py` med `SCRAPER_REPLAY` (ingen netværk). Tilføj en ren parsertest
   med en lille håndskrevet HTML-række og en lille RSS-item, så formatet er dokumenteret.

## Færdig når
- `python -m scraper.run --only "<navn>"` giver `ok: true` og et rimeligt `listed` for hver af de 13 kilder. Skriv i noterne en
  linje pr. kilde: listed / matched / fundne titler. (0 match er fint – det er sjældne stillinger.)
- `python -m pytest -q` er grønt.
- Commit: `Opgave 2: SuccessFactors-adapter`. Afkryds i `docs/OPGAVER.md`. **Ingen push.**

## Ikke i denne opgave
Andre systemer. GitHub Actions.

## Noter fra udførelsen
Kørt live 11/11-2026 med `python -m scraper.run --only "<navn>" --dry-run`. Format: listed / matched (titel + land ok) / titler med søgeord i titlen.

| Kilde | listed | matched | Titler med søgeord (før landefilter) |
|---|---|---|---|
| Ambu | 151 | 0 | – (via sitemap, se nedenfor) |
| Lundbeck | 10 | 0 | – |
| Novo Nordisk | 0 | 0 | – (ægte 0 resultater; sitemap har 466 opslag, ingen med søgeord) |
| Wärtsilä | 10 | 0 | – (sitemap: 138 opslag, ingen) |
| Demant | 7 | 0 | "(Senior) HR Digitalisation Specialist for Core & Workforce, SuccessFactors" – Szczecin, PL (ikke et af landene) |
| Søstrene Grene | 0 | 0 | – |
| Bygma | 10 | 0 | – |
| Bertelsmann | 39 | **1** | "Praktikant:in im Bereich HRIS (m/w/d)" – Gütersloh, DE, slået op 31/10 |
| KPMG Tyskland | 370 | **1** | "Senior Consultant SAP SuccessFactors / HCM (w/m/d)" – Berlin, DE (ingen opslagsdato) |
| KPMG UK | 6 | 0 | – |
| DSV | 55 | 0 | – |
| Coloplast | 281 | 0 | – |
| Swiss Re | 202 | 0 | – |

Fund og afvigelser:
- **"Unify"-sider:** Ambu og KPMG Tyskland (og Novo/Søstrene Grene i nogle tilfælde) leverer et tomt søgeskelet; resultaterne hentes af
  JavaScript fra `/services/`, som robots.txt forbyder. Første udgave behandlede det som "0 resultater" og missede KPMG Tysklands
  SuccessFactors-job (fundet ved at tjekke sitemap'en). Nu regnes en søgeside kun som ægte 0 resultater, hvis den har `#search-wrapper`
  og ikke `SearchResultsUnify`; ellers bruges `/sitemap.xml`. Se `docs/KILDER.md`.
- **KPMG Tysklands jobsider er tomme skeletter** (ingen JSON-LD, ingen dato, ingen lokation). Titlen hentes fra `<title>`, byen står i
  adressen, og **opslagsdato mangler** – jobbet får derfor `first_seen`/`baseline` i run.py. For at få land på jobbene tilføjede jeg en
  valgfri `country`-nøgle i `companies.yaml` (KPMG Tyskland: `DE`, KPMG UK: `GB`). Den bruges kun, når kilden slet ikke oplyser et sted.
  (Rettelse af config uden for opgavens ordlyd – ellers ville fx et KPMG-job i Köln blive tabt, fordi byen ikke står i settings.)
- Jobsiden hentes kun for job med søgeord i titlen og kun når dato/land mangler (højst 30 pr. kilde). "Mangler land" betyder: ingen
  af settings' lande i lokationen – også en række med fx "Toyama, JP" giver derfor ét ekstra jobside-kald.
- CSB-datoer i microdata ser ud som `Wed Nov 11 02:00:00 UTC 2026`; `parse_date` forstår nu formatet (`common.py`).
- `scraper/record.py` (`python -m scraper.record "Wärtsilä"`) optager til `tests/fixtures/<navn>/`. Fixtures: `wartsila`, `bertelsmann`
  (kun de normale svar – sitemap-fallbacken testes med håndskrevne RSS/urlset-eksempler og falske svar).
- `soup()` er tilføjet til `common.py`. Sitemap-parseren bruger lxml (`recover=True`) fordi RSS-filerne er store (1,9 MB hos Wärtsilä).
- Søgningen bruger kun ordene fra `settings.yaml` ("SuccessFactors", "HRIS"). "Success Factors" med mellemrum findes ikke af søgningen,
  men fanges via sitemap-fallback på unify-sider.
