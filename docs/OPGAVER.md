# Opgaver

Sig `lav opgave N, commit ikke push` i Claude Code. Tag dem i rækkefølge – hver bygger på den forrige.
Afkryds med dato og én linje, når opgaven er committet.

- [x] **1. Skelet, fælles kode og dataformat** – `opgave-01-skelet.md`
      → 2026-11-11: common/match/model/run + 92 tests grønne; `--dry-run` viser 22 kilder "adapter mangler" og KPMG Schweiz som ikke dækket.
- [x] **2. SuccessFactors-adapter (13 kilder)** – `opgave-02-successfactors.md`
      → 2026-11-11: alle 13 kilder ok (søgeside + sitemap-fallback), 1 aktivt match (Bertelsmann) + 1 hos KPMG Tyskland; 116 tests grønne.
- [x] **3. Byg siden til artefaktet** – `opgave-03-side.md`
      → 2026-11-11: `scraper/build_page.py` + 6 tests (122 grønne); `site/jobradar.html` bygget af rigtige data (2 aktive job).
- [ ] **4. GitHub Actions: daglig kørsel + tests** – `opgave-04-github-actions.md`
      → Når den er pushet og har kørt én gang: sig til Claude i Cowork, så den tjekker at artefaktet opdateres.
- [ ] **5. Phenom (Ricoh, Givaudan) og Eightfold (Ericsson)** – `opgave-05-phenom-eightfold.md`
- [ ] **6. Nordea, ZF Lifetec og Munich Re** – `opgave-06-nordea-zf-munichre.md`
- [ ] **7. KPMG Danmark, Finland og Sverige** – `opgave-07-kpmg.md`
- [ ] **8. Sundhedstjek og alarm** – `opgave-08-sundhed.md`

## Kan ikke dækkes
- **KPMG Schweiz** (jobs.kpmg.ch): robots.txt forbyder al automatisk adgang. Vises som "Ikke dækket" på siden.
