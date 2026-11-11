# job-scraper2 – HRIS-jobradar

Finder nye stillinger med **SuccessFactors** eller **HRIS** i titlen hos 18 virksomheder (Ambu, Lundbeck, Novo Nordisk,
Wärtsilä, Demant, Ericsson, Nordea, Søstrene Grene, Bygma, Bertelsmann, Ricoh Europe, ZF Lifetec, KPMG, DSV, Coloplast,
Givaudan, Swiss Re, Munich Re) i Danmark, Sverige, Finland, Tyskland, UK og Schweiz.

- GitHub Actions kører hver morgen → `data/jobs.json` + `site/jobradar.html`
- Siden udgives som Claude-artefaktet **HRIS-jobradar** (kan deles) med filtre for i dag / 7 dage / 14 dage
- Virksomheder og søgeord: `config/`. Kilder og robots.txt: `docs/KILDER.md`. Opgaver: `docs/OPGAVER.md`. Arbejdsgang: `ARBEJDSMAADE.md`

```bash
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest -q
python -m scraper.run --only "Wärtsilä"     # én virksomhed
python -m scraper.run                       # alle
python -m scraper.build_page                # byg site/jobradar.html
```

Kun til personlig brug. Respekterer robots.txt og henter kun offentlige opslag.
