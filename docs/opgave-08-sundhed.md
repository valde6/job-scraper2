# Opgave 8 – Sundhedstjek og alarm

## Mål
Valdemar får besked, hvis en kilde går i stykker, i stedet for at radaren stille og roligt bliver tom.

## Baggrund
Mønstret findes i `../job-scraper/scraper/health.py` og trinnet "Alarm som GitHub-issue" i `../job-scraper/.github/workflows/scrape.yml`.
Hold det meget mindre: 22 kilder.

## Det skal laves
1. `data/health.json`: historik pr. kilde over de seneste 14 kørsler (dato, ok, listed).
2. `scraper/health.py`: skriv `data/health_alert.md`, hvis en kilde
   - har fejlet i 2 kørsler i træk, eller
   - har `listed: 0` i 3 kørsler i træk (mulig ændring af siden), eller
   - har under 20 % af sin median for `listed` (de seneste 7 kørsler med data).
   Teksten: én linje pr. kilde med virksomhed, kilde, problem, seneste fejltekst og hvad der typisk skal gøres
   ("åbn karrieresiden og tjek om adressen/systemet er ændret; se docs/KILDER.md").
3. Workflowet: kør `python -m scraper.health` efter scrape; opret/kommentér/luk et GitHub-issue med label `scraper-health`
   (som i job-scraper; `permissions: issues: write`).
4. Tests for de tre regler.

## Færdig når
- Tests grønne. Commit: `Opgave 8: sundhedstjek og alarm`. Afkryds. **Ingen push.**

## Noter fra udførelsen
- `data/health.json` har `{"schema": 1, "sources": {"<virksomhed>[ – <label>]": [{"date", "ok", "listed"}, …]}}`, højst 14 poster pr. kilde.
  Én post pr. **kørselsdato** (`generated_at` i `jobs.json`): kører man health to gange på samme fil, eller scraperen to gange samme dag,
  erstatter den nyeste posten i stedet for at tælle dobbelt. "I træk" betyder derfor "dage i træk" (scraperen kører én gang om dagen). `listed` er `null` ved fejl.
- Workflowet kører sundhedstjek og alarm **kun ved fulde kørsler** (`inputs.only` tom). En kørsel med `only` lader de andre kilders status stå
  uændret i `jobs.json`, og de ville ellers blive talt med igen i historikken.
- Alarmen er `data/health_alert.md` (i `.gitignore` – den bruges kun i workflowet og skal ikke committes). Issuet oprettes med label `scraper-health`
  (oprettes automatisk), kommenteres + opdateres kun hvis teksten har ændret sig (ikke hver morgen), og lukkes når filen ikke findes mere.
- Fald-reglen (<20 % af median) bruger de 7 kørsler **før** den aktuelle og kræver mindst 3 kørsler med data og en median på mindst 5.
  Uden den grænse ville en kilde som ZF Lifetec (listed 1) alarmere ved første kørsel med 0. Grænserne står som konstanter øverst i `health.py`.
- **Kendt falsk alarm:** Novo Nordisk, Søstrene Grene, Munich Re og KPMG Finland har i dag `listed: 0` (Munich Re listes kun efter søgeord i titlen).
  Regel 2 ("0 i 3 kørsler") vil derfor oprette et issue ca. 3 dage efter første kørsel, selv om kilderne virker. Opgaven siger det sådan, så jeg har ikke
  ændret reglen – foreslag til en senere opgave: en `allow_empty: true` på sådanne kilder i `companies.yaml`, som `health.py` respekterer.
- Ikke testet mod rigtige GitHub-issues (kræver push); `gh`-trinnet er kopieret fra `../job-scraper` med ændringen om kommentar-kun-ved-ændring.
- Plan mode blev ikke brugt (sessionen var ikke interaktiv, så en plan kunne ikke godkendes), selvom opgaven rører flere end tre filer.
