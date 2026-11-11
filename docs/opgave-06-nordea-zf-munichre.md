# Opgave 6 – Nordea, ZF Lifetec og Munich Re

## Mål
Tre egne kilder: `type: nordea`, `type: strapi_zf` og `type: radancy_sitemap`.

## Baggrund
Se **Nordea**, **ZF Lifetec (Strapi)** og **Munich Re (Radancy)** i `docs/KILDER.md`.
Munich Re: `/search-jobs/` er forbudt i robots.txt – heller ikke som fallback.

## Det skal laves
1. `scraper/adapters/nordea.py`: for hvert søgeord `GET {url}?_format=json&items_per_page=50&page={n}&search={ord}` indtil færre end 50.
   url = `field_ad_url` (html-unescape to gange), location = `location_name`, posted = `created`. (Se `../job-scraper/scraper/adapters/nordea.py`.)
2. `scraper/adapters/strapi_zf.py`: ét kald med `$containsi`-filtre for hvert søgeord (se KILDER.md), `populate[0]=Countries`,
   `pagination[pageSize]=100`, side for side. Afprøv `locale=all` og brug det, hvis det giver flere opslag (skriv resultatet i noterne).
   url = `{job_base}/{Slug}`, location = `"{City}, {Countries[0].Title}"`, countries fra `Countries[].Title`, posted = `publishedAt`.
3. `scraper/adapters/radancy_sitemap.py`: hent `sitemap` (eller `{url}/sitemap.xml`), behold `<loc>` der indeholder `/job/` og hvis
   titel-slug (unquote, `-` → mellemrum) matcher et søgeord. Hent hver af dem (højst 30) og læs JSON-LD: titel, `datePosted`,
   `jobLocation` → location + countries. Brug `<lastmod>` som reserve for dato, hvis JSON-LD mangler `datePosted`.
4. Registrér alle tre. Fixtures: Nordea og ZF Lifetec optaget; Munich Re testes med en lille håndskrevet sitemap + jobside.

## Færdig når
- `--only Nordea`, `--only "ZF Lifetec"`, `--only "Munich Re"` giver `ok: true`. Noter listed/matched/titler.
- Tests grønne. Commit: `Opgave 6: Nordea, ZF Lifetec og Munich Re`. Afkryds. **Ingen push.**

## Noter fra udførelsen
_(udfyldes af Claude Code)_
