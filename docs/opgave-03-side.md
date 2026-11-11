# Opgave 3 – Byg siden til artefaktet

## Mål
`python -m scraper.build_page` laver `site/jobradar.html` ud fra `site/template.html` og `data/jobs.json`.
Det er den fil, Cowork udgiver som Claude-artefaktet **HRIS-jobradar**.

## Baggrund
- `site/template.html` er færdig og designet (lavet af Claude i Cowork). Den er et **artefakt-fragment**: ingen `<!doctype>`,
  `<html>`, `<head>` eller `<body>` – Claude-artefaktet lægger selv dem på. Filen skal starte med `<title>HRIS-jobradar</title>`.
- Data ligger i `<script type="application/json" id="jobdata">…</script>`. Siden læser felterne fra kontrakten i `AGENTS.md`
  (jobs: `title, company, url, location, country, countries, posted, first_seen, date_basis, active`; samt `generated_at`,
  `countries`, `sources`, `not_covered`).
- Artefakter må ikke hente data udefra (CSP), derfor indlejres data i selve siden.

## Det skal laves
1. `scraper/build_page.py`:
   - Læs `data/jobs.json` (findes den ikke: brug tom struktur med `generated_at: null`).
   - Medtag kun aktive job og kun de felter, siden bruger. Medtag `sources` (company, label, ok, matched, error) og `not_covered`.
   - Erstat **indholdet** mellem `<script type="application/json" id="jobdata">` og `</script>` med
     `json.dumps(payload, ensure_ascii=False)` hvor `</` er escapet som `<\/`. Rør intet andet i skabelonen.
   - Skriv `site/jobradar.html`. Fejl tydeligt, hvis markøren ikke findes.
2. `tests/test_build_page.py`: byg med en lille testdatafil (2 aktive job, 1 inaktivt, en titel med `</script>` og `æøå`) til en tmp-mappe;
   tjek at resultatet starter med `<title>HRIS-jobradar</title>`, at JSON'en kan parses tilbage, at det inaktive job mangler, og at resten
   af filen er identisk med skabelonen.
3. Kør `python -m scraper.run` (de 13 SuccessFactors-kilder) og derefter `python -m scraper.build_page`, og åbn `site/jobradar.html`
   i en browser for at se, at tabellen og periodeknapperne virker. (Lokalt mangler artefaktets skelet, men siden fungerer i en browser.)

## Færdig når
- Tests grønne. `site/jobradar.html` og `data/jobs.json` er committet sammen med koden.
- Commit: `Opgave 3: byg siden til artefaktet`. Afkryds i `docs/OPGAVER.md`. **Ingen push.**

## Ikke i denne opgave
Ændringer i sidens design (bed Claude i Cowork om det). Udgivelse af artefaktet (gøres af Cowork).

## Noter fra udførelsen
- Fuld `python -m scraper.run` giver 13 ok kilder og 2 aktive job (Bertelsmann, KPMG Tyskland). De øvrige 9 kilder står som "adapter mangler" (opgave 5-7) og vises som fejl i kildestatus på siden, indtil de er lavet.
- Siden er ikke åbnet i en rigtig browser (ingen grafisk adgang fra Claude Code). Kontrolleret: filen starter med `<title>HRIS-jobradar</title>`, dataene kan parses tilbage, og sidens script har gyldig JavaScript-syntaks (`node`). Valdemar bør åbne `site/jobradar.html` og kigge på tabel og periodeknapper.
- Manglende `data/jobs.json` giver tom struktur med tomme lister (ikke skabelonens KPMG-linje i `not_covered`).
- `data/jobs.json` indeholder kun to job og er kun et øjebliksbillede; GitHub Actions (opgave 4) overskriver den dagligt.
