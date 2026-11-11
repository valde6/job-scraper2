# Opgave 9 – Ingen falske alarmer fra kilder, der bare er tomme

## Mål
Sundhedstjekket (opgave 8) må ikke oprette et issue for kilder, der virker, men som i dag ikke har nogen SuccessFactors-/HRIS-opslag.

## Baggrund
`listed` tæller opslag fundet med søgeordene – ikke alle virksomhedens opslag. Derfor er `listed: 0` normalt for fx Novo Nordisk,
Søstrene Grene, Munich Re og KPMG Finland (se noterne i opgave 8). Regel 2 ("0 i 3 kørsler i træk") vil give en falsk alarm ca. 3 dage
efter første GitHub-kørsel.

## Det skal laves
1. Valgfri nøgle `allow_empty: true` pr. kilde i `config/companies.yaml`. Sæt den på de kilder, hvor søgningen giver 0 uden at noget er galt:
   Novo Nordisk, Søstrene Grene, Munich Re, KPMG Finland (og andre, hvis en fuld kørsel viser `listed: 0`, mens kilden ellers svarer normalt).
2. `scraper/run.py` skriver `allow_empty` med i `sources[]` (eller `health.py` læser den fra config – vælg den enkleste løsning og skriv den i noterne).
3. `health.py`: regel 2 og regel 3 (fald under 20 %) springes over for kilder med `allow_empty: true`. Regel 1 (fejl 2 kørsler i træk) gælder stadig.
4. Tests for at `allow_empty` slår regel 2 og 3 fra, men ikke regel 1.
5. Oprydning: opgave 5 blev committet uden afkrydsning. Afkryds den i `docs/OPGAVER.md` (2026-11-11) og skriv kort i
   "Noter fra udførelsen" i `opgave-05-phenom-eightfold.md`, hvad en `--only`-kørsel giver for Ricoh Europe, Givaudan og Ericsson (listed/matched/titler).

## Færdig når
- Tests grønne. Commit: `Opgave 9: ingen falske alarmer fra tomme kilder`. Afkryds i `docs/OPGAVER.md`. **Ingen push.**

## Ikke i denne opgave
Ændringer i hvad `listed` betyder, eller i siden.

## Noter fra udførelsen
- **Løsning (punkt 2):** `run.py` skriver `allow_empty` (bool, altid med, `false` som standard) i hver `sources[]`-post, og `health.py` læser den derfra.
  Det er den enkleste vej: `health.py` skal ikke kende `companies.yaml`. Prisen er, at en ændring i config først slår igennem ved næste fulde kørsel
  (health kører lige efter scrape, så i praksis samme morgen). Dokumenteret i datakontrakten i `AGENTS.md`; `schema` er uændret, siden ignorerer feltet.
- `allow_empty: true` er sat på Novo Nordisk, Søstrene Grene, Munich Re og KPMG Finland – de eneste fire med `listed: 0` i den seneste fulde kørsel
  (2026-11-11), mens de ellers svarer normalt. Ingen andre kilder var på 0.
- `--only`-kørsler for Ricoh, Givaudan og Ericsson er kørt med `--dry-run`, så `data/jobs.json` er urørt; tallene står i opgave 5.
- Plan mode blev ikke brugt (ikke-interaktiv session), selvom opgaven rører flere end tre filer.
- Bemærk: `data/jobs.json` i repoet har endnu ikke `allow_empty` på kilderne; det kommer med den næste fulde kørsel. Indtil da behandler `health.py` alle som `false`.
