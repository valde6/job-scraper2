# Opgaver

Sig `lav opgave N, commit ikke push` i Claude Code. Tag dem i rækkefølge – hver bygger på den forrige.
Afkryds med dato og én linje, når opgaven er committet.

- [x] **1. Skelet, fælles kode og dataformat** – `opgave-01-skelet.md`
      → 2026-11-11: common/match/model/run + 92 tests grønne; `--dry-run` viser 22 kilder "adapter mangler" og KPMG Schweiz som ikke dækket.
- [x] **2. SuccessFactors-adapter (13 kilder)** – `opgave-02-successfactors.md`
      → 2026-11-11: alle 13 kilder ok (søgeside + sitemap-fallback), 1 aktivt match (Bertelsmann) + 1 hos KPMG Tyskland; 116 tests grønne.
- [x] **3. Byg siden til artefaktet** – `opgave-03-side.md`
      → 2026-11-11: `scraper/build_page.py` + 6 tests (122 grønne); `site/jobradar.html` bygget af rigtige data (2 aktive job).
- [x] **4. GitHub Actions: daglig kørsel + tests** – `opgave-04-github-actions.md`
      → 2026-11-11: `hris-scrape` (daglig + manuel med `only`) og `ci` oprettet; mangler at blive pushet og kørt første gang.
      → Når den er pushet og har kørt én gang: sig til Claude i Cowork, så den tjekker at artefaktet opdateres.
- [x] **5. Phenom (Ricoh, Givaudan) og Eightfold (Ericsson)** – `opgave-05-phenom-eightfold.md`
      → 2026-11-11: afkrydset bagud i opgave 9 (var committet uden afkrydsning); tal fra `--only`-kørsler står i opgavefilens noter.
- [x] **6. Nordea, ZF Lifetec og Munich Re** – `opgave-06-nordea-zf-munichre.md`
      → 2026-11-11: alle tre ok (Nordea 10 listed, ZF 1, Munich Re 0 job med søgeord i titlen); 0 matches; 141 tests grønne.
- [x] **7. KPMG Danmark, Finland og Sverige** – `opgave-07-kpmg.md`
      → 2026-11-11: alle fem KPMG-kilder ok (Schweiz under "ikke dækket"); hele kørslen 22/22 kilder ok, ingen "adapter mangler"; 153 tests grønne.
- [x] **8. Sundhedstjek og alarm** – `opgave-08-sundhed.md`
      → 2026-11-11: `scraper/health.py` + `data/health.json` + issue-alarm i workflowet; 18 nye tests, 171 grønne.
- [x] **9. Ingen falske alarmer fra tomme kilder** – `opgave-09-tomme-kilder.md`
      → 2026-11-11: `allow_empty: true` på 4 kilder; `health.py` springer "tom" og "fald" over for dem, "fejl" gælder stadig; 175 tests grønne.

## Kan ikke dækkes
- **KPMG Schweiz** (jobs.kpmg.ch): robots.txt forbyder al automatisk adgang. Vises som "Ikke dækket" på siden.
