# Opgave 4 – GitHub Actions: daglig kørsel + tests

## Mål
Scraperen kører af sig selv hver morgen på GitHub, committer `data/jobs.json` og `site/jobradar.html`, og tests kører ved hvert push.

## Baggrund
Se `../job-scraper/.github/workflows/scrape.yml` og `ci.yml` for et mønster, der virker (commit som bot, `git pull --rebase` før push).
Repoet er offentligt, og Cowork henter `site/jobradar.html` derfra kl. ca. 06:40 dansk tid.

## Det skal laves
1. `.github/workflows/scrape.yml` (navn `hris-scrape`):
   - `schedule: cron "17 4 * * *"` (05:17 dansk vintertid / 06:17 sommertid) + `workflow_dispatch` med input `only` (tom = alle).
   - `permissions: contents: write`, `concurrency: {group: scrape, cancel-in-progress: false}`, `timeout-minutes: 30`.
   - Python 3.12 med pip-cache → `pip install -r requirements.txt` → `python -m scraper.run [--only …] | tee data/last_run.log`
     → `python -m scraper.build_page` → commit `data/` og `site/jobradar.html` som `hris-radar-bot`
     med besked `Jobradar opdateret <UTC-tid>` (kun hvis der er ændringer) → `git pull --rebase --autostash && git push`.
   - Kørslen må ikke fejle, fordi én kilde fejler (det står i `sources`). Den skal fejle, hvis `run.py` eller `build_page.py` crasher.
2. `.github/workflows/ci.yml`: på push og pull_request: installér `requirements.txt` + `requirements-dev.txt`, kør `python -m pytest -q`.
3. Kort afsnit i `README.md`: sådan startes en kørsel manuelt (Actions → hris-scrape → Run workflow, evt. med `only`).

## Færdig når
- Begge workflows er gyldig YAML (`python -c "import yaml,sys;[yaml.safe_load(open(f)) for f in sys.argv[1:]]" .github/workflows/*.yml`).
- Tests grønne.
- Commit: `Opgave 4: GitHub Actions`. Afkryds i `docs/OPGAVER.md`. **Ingen push** – Valdemar pusher og starter første kørsel
  manuelt under Actions. Skriv i noterne, at han skal gøre det.

## Ikke i denne opgave
Alarmer ved fejlende kilder (opgave 8).

## Noter fra udførelsen
- **Valdemar skal:** pushe, derefter Actions → hris-scrape → Run workflow (tomt `only`) og tjekke, at der kommer en commit fra `hris-radar-bot`. Under Settings → Actions → General skal workflow-rettigheder tillade skrivning (workflowet beder selv om `contents: write`, men repo-indstillingen må ikke være låst til read-only for organisationen).
- `only` sendes via en miljøvariabel (`ONLY`) og ikke direkte ind i shell-scriptet, så et virksomhedsnavn med citationstegn ikke kan ødelægge kommandoen.
- `set -o pipefail` er sat, så en crash i `run.py` fejler trinnet trods `| tee`. `run.py` returnerer 0 når kilder fejler, så det fejler ikke kørslen.
- `data/last_run.log` committes sammen med `data/` (som opgaven foreskriver).
- Workflowene er kun valideret som YAML lokalt; de er ikke kørt på GitHub endnu.
