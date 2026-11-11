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
_(udfyldes af Claude Code)_
