# Arbejdsmåde

Sådan arbejder vi i job-scraper2. Gælder for alle – Valdemar, Claude i Cowork og Claude Code i VS Code.

## Roller
| Hvem | Gør |
|---|---|
| **Claude (Cowork)** | Planlægger, undersøger kilder (karrieresider, robots.txt), skriver opgaver i `docs/`, publicerer det delbare Claude-artefakt og sætter den daglige opdatering op. Skriver ikke selv kode i repoet. |
| **Claude Code (VS Code)** | Udfører én opgave ad gangen fra `docs/`. Skriver kode og tests, committer. **Pusher aldrig.** |
| **Valdemar** | Beder Claude Code om at lave en opgave, kigger ændringerne igennem i GitHub Desktop og pusher selv. |

## Gangen i en opgave
1. Valdemar skriver i Claude Code: **`lav opgave 3, commit ikke push`**
2. Claude Code læser `AGENTS.md` og `docs/opgave-03-*.md` (kun den opgave) og laver den.
3. Claude Code kører `python -m pytest -q`. Rød test = ikke færdig.
4. Claude Code afkrydser opgaven i `docs/OPGAVER.md` med en kort note (dato + én linje) og skriver eventuelle afvigelser under
   **"Noter fra udførelsen"** nederst i opgavefilen.
5. Claude Code committer alt i én commit: `Opgave 3: <kort beskrivelse>`. **Ingen `git push`.**
6. Valdemar åbner GitHub Desktop, kigger diff'en igennem og trykker **Push origin**.

## Regler for Claude Code
- **Aldrig `git push`**, heller ikke hvis en opgave ser ud til at kræve det. Valdemar pusher.
- Én opgave pr. gang. Lav ikke ting fra andre opgaver, selvom de er lige ved hånden – skriv dem i noterne i stedet.
- Passer opgaven ikke med virkeligheden (en side har ændret sig, et API svarer anderledes), så gør det, der kan lade sig gøre,
  og skriv præcist hvad og hvorfor under "Noter fra udførelsen". Gæt ikke på data.
- Kan en kilde ikke hentes lovligt (robots.txt, bot-mur, CAPTCHA, login), så omgå det **ikke**: sæt kilden til `type: none`
  med en `note` og skriv det i noterne.
- Commit-beskeder og kommentarer på dansk. Ingen hemmeligheder i repoet.
- Kan du ikke nå en karriereside fra din maskine, så sig det – siderne kan også testes via GitHub Actions (workflow_dispatch med `only`, når opgave 4 er lavet).

## Opgavefilerne
- Ligger i `docs/` som `opgave-NN-<emne>.md`. Overblik og status i `docs/OPGAVER.md`.
- Fast opbygning: **Mål**, **Baggrund**, **Det skal laves**, **Færdig når**, **Ikke i denne opgave**, **Noter fra udførelsen**.
- Nye opgaver beder Valdemar Claude i Cowork om. De nummereres fortløbende og tilføjes `docs/OPGAVER.md`.
- Fakta om kilderne (adresser, API-felter, robots.txt) står i `docs/KILDER.md`.

## Efter push
- GitHub Actions kører scraperen hver morgen og bygger `site/jobradar.html` med de nyeste job.
- En planlagt opgave i Cowork henter siden fra GitHub og genudgiver Claude-artefaktet **HRIS-jobradar** på samme link,
  så det link, der er delt, altid viser nyeste data.
