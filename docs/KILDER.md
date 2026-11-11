# Kilder – undersøgt 11/11-2026

Hvor hver virksomhed slår job op, hvordan de hentes, og hvad robots.txt siger.
Opdatér filen, når en kilde ændrer sig (dato + hvad).

## Oversigt

| Virksomhed | System | Kilde | robots.txt | Status |
|---|---|---|---|---|
| Ambu | SuccessFactors CSB | jobs.ambu.com | standard CSB (se nedenfor) | ✅ |
| Lundbeck | SuccessFactors CSB | jobs.lundbeck | standard CSB | ✅ |
| Novo Nordisk | SuccessFactors CSB | careers.novonordisk.com | standard CSB | ✅ |
| Wärtsilä | SuccessFactors CSB | careers.wartsila.com | standard CSB | ✅ (138 opslag i alt) |
| Demant | SuccessFactors CSB | careers.demant.com | standard CSB | ✅ |
| Ericsson | Eightfold | jobs.ericsson.com `/api/pcsx/search` | **alt forbudt undtagen** `/careers`, `/api/pcsx`, `/api/apply` m.fl. | ✅ brug kun `/api/pcsx/search` |
| Nordea | Eget JSON-API | www.nordea.com/en/api/jobs-list | `/en/api/` ikke forbudt | ✅ |
| Søstrene Grene | SuccessFactors CSB | career.sostrenegrene.com | standard CSB | ✅ |
| Bygma | SuccessFactors CSB | jobs.bygma.dk | standard CSB | ✅ (kun DK-job) |
| Bertelsmann | SuccessFactors CSB | jobsearch.createyourowncareer.com | standard CSB | ✅ ca. 980 opslag, hele koncernen |
| Ricoh Europe | Phenom | careersatricoh.com/gb/en | forbyder bl.a. `*/apply`, `*/px-widgets` | ✅ |
| ZF Lifetec | Strapi CMS (Nuxt-side) | careers-strapi.zf-lifetec.com/api/jobs | ingen robots.txt (404) = tilladt | ✅ 75 opslag |
| KPMG Danmark | HR-Manager | kunde `kpmg` | – (bruges allerede i job-scraper) | ✅ |
| KPMG Finland | Oracle Recruiting Cloud | iabdgs.fa.ocs.oraclecloud.com, site `CX_1002` | ingen robots.txt (404) = tilladt | ✅ |
| KPMG Sverige | Jobylon | cdn.jobylon.com/jobs/companies/1532/embed/v2/ | `*` tilladt (kun `/jobs/*/preview/` forbudt) | ⚠️ Cloudflare foran – kan blive blokeret fra GitHub |
| KPMG Tyskland | SuccessFactors CSB | jobs.kpmg.de | standard CSB | ✅ |
| KPMG UK | SuccessFactors CSB | experienced.kpmgcareers.co.uk | standard CSB | ✅ |
| **KPMG Schweiz** | ukendt | jobs.kpmg.ch | **`User-agent: *` / `Disallow: /`** | ❌ **må ikke scrapes** |
| DSV | SuccessFactors CSB | jobs.dsv.com | standard CSB | ✅ ca. 2.000 opslag |
| Coloplast | SuccessFactors CSB | careers.coloplast.com | standard CSB | ✅ |
| Givaudan | Phenom | careers.givaudan.com/global/en | forbyder `*/gb/en`, `*/apply`, `*/px-widgets` m.fl. | ✅ brug `/global/en` |
| Swiss Re | SuccessFactors CSB | careers.swissre.com | standard CSB | ✅ |
| Munich Re | Radancy | careers.munichre.com | **`/search-jobs/` forbudt** for alle undtagen Indeed | ✅ via `/en/sitemap.xml` + jobsider |

**Standard CSB robots.txt** (identisk på alle SuccessFactors-siderne): forbyder `/applybutton/`, `/talentcommunity/`,
`/emailsubscribe/`, `/email/image/`, `/services/` (dvs. også RSS-feeds under `/services/rss/`), `/preapply/`, `/error`,
`/unsubscribe/`, `/reset/`. **Tilladt:** `/search/`, `/job/…`, `/sitemap.xml`.

## Detaljer pr. system

### SuccessFactors Career Site Builder (13 kilder)
- **Søgeside:** `{base}/search/?q={ord}&locationsearch=&sortColumn=referencedate&sortDirection=desc&startrow={n}`
  Server-renderet HTML. Rækker: `tr.data-row` → `a.jobTitle-link` (titel + href), `.jobLocation` (fx `Helsinki, FI`,
  evt. `+10 more…`), `.jobDate` (fx `10 Nov 2026` – formatet afhænger af sprog). Antal: tekst `Results 1 to 50 of 138`.
  Søgningen er fuldtekst, så filtrér selv på titel bagefter.
- **`/sitemap.xml` findes i to varianter:**
  - RSS/Google Base-feed (fx Wärtsilä): `<item>` med `<title>Titel (By, Region, CC)</title>`, `<link>`, `<g:location>By, CC</g:location>`,
    `<g:expiration_date>`, `<g:employer>`. Alle opslag i én fil, men ingen opslagsdato.
  - Almindelig `<urlset>` (fx Bertelsmann, ZF): `<loc>` med titel og by i adressen (`/job/München-Manager-…/1433825433/`) og `<lastmod>`.
- **Jobside** `/job/<slug>/<id>/`: schema.org JobPosting (JSON-LD eller `itemprop`) med `datePosted` og `jobLocation`.
- Job-id = det lange tal i adressen.
- **"Unify"-sider (11/11-2026, opgave 2):** Ambu, Novo Nordisk (delvist), KPMG Tyskland m.fl. – søgesiden `/search/` er et tomt skelet
  (`j2w.SearchResultsUnify`), og resultaterne hentes af JavaScript fra `/services/` (forbudt). Adapteren bruger så `/sitemap.xml`.
  KPMG Tysklands jobsider er også tomme skeletter: kun `<title>` og adressens by findes, **ingen opslagsdato** og ingen lokation
  (derfor `country: DE` i companies.yaml). Sider med `tr.data-row` og søgefeltet `#search-wrapper` uden rækker = ægte 0 resultater.
- Wärtsilä, Lundbeck, Bygma m.fl. viser 7–10 "anbefalede" rækker, når søgeordet ikke findes (samme rækker for alle søgeord).
- Fuldtekstsøgning er ordbaseret: `q=SuccessFactors` finder ikke "Success Factors" med mellemrum (sitemap-tjek 11/11 fandt ingen sådan titel).

### Eightfold – Ericsson
- `GET https://jobs.ericsson.com/api/pcsx/search?domain=ericsson.com&query={ord}&location=&start={n}&sort_by=timestamp`
- Svar: `data.positions[]` med `name`, `locations[]` (`"Stockholm,Stockholm County,Sweden"`),
  `standardizedLocations[]` (`"Bucharest, Bucharest, RO"`), `postedTs` (unix-sekunder), `positionUrl` (`/careers/job/<id>`), `id`.
- Opslagets adresse: `https://jobs.ericsson.com/careers/job/<id>`.
- Brug ALDRIG andre stier end dem robots.txt tillader.

### Phenom – Ricoh Europe, Givaudan
- `GET {base}/search-results?keywords={ord}&from={n}&s=1` → HTML med `phApp.ddo = {...}`.
  `ddo.eagerLoadRefineSearch.totalHits` og `.data.jobs[]`: `title`, `city`, `country` (fulde navne, fx `United Kingdom`),
  `postedDate` (ISO), `jobId`, evt. `multi_location`.
- Opslagets adresse: `{base}/job/{jobId}`.
- Fundet 11/11: Ricoh "SAP SuccessFactors Employee Central & Compensation Engineer", London, slået op 10/11.
- Kopiér gerne `_ddo()` fra `../job-scraper/scraper/adapters/phenom.py`.

### Nordea
- `GET https://www.nordea.com/en/api/jobs-list?_format=json&items_per_page=50&page={n}&search={ord}`
- `results[]`: `title`, `location_name`, `created`, `field_ad_url` (HTML-escaped to gange), `nid`.
- Kopiér gerne fra `../job-scraper/scraper/adapters/nordea.py`.

### ZF Lifetec (Strapi)
- `GET https://careers-strapi.zf-lifetec.com/api/jobs?pagination[pageSize]=100&populate[0]=Countries`
  `&filters[$or][0][Title][$containsi]=successfactors&filters[$or][1][Title][$containsi]=hris`
- Felter: `Title`, `Slug`, `SapID`, `City`, `Countries[].Title` (fx `Germany`), `publishedAt`, `createdAt`.
- Opslag: `https://careers.zf-lifetec.com/jobs/{Slug}`. Tjek om `locale=all` giver flere (siden har EN/DE/ZH).
- Fundet 11/11: "HR SuccessFactors Senior Technology Analyst", Washington (USA – filtreres fra).

### Munich Re (Radancy)
- `/en/sitemap.xml`: ca. 4.000 adresser, heraf ca. 1.600 job: `/en/job/{by}/{titel-slug}/3342/{id}`, alle med `<lastmod>`.
- Filtrér på titel-slug (`successfactors`, `hris`), hent derefter jobsiden for JSON-LD (`datePosted`, land).
- `/search-jobs/` er forbudt i robots.txt – brug den ikke, heller ikke som fallback.

### KPMG
- **Danmark:** HR-Manager, kunde `kpmg`. Kopiér `../job-scraper/scraper/adapters/hrmanager.py`.
- **Finland:** Oracle Recruiting Cloud.
  `GET https://iabdgs.fa.ocs.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true`
  `&expand=requisitionList.secondaryLocations&finder=findReqs;siteNumber=CX_1002,keyword={ord},limit=25,offset={n},sortBy=POSTING_DATES_DESC`
  → `items[0].requisitionList[]`: `Id`, `Title`, `PrimaryLocation`, `PrimaryLocationCountry`, `PostedDate`.
  Opslag: `https://iabdgs.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1002/job/{Id}`.
  Kopiér gerne fra `../job-scraper/scraper/adapters/oracle.py`.
- **Sverige:** Jobylon-widget `https://cdn.jobylon.com/jobs/companies/1532/embed/v2/?target=jobylon-jobs-widget&page_size=100`.
  Joblisten står i HTML'en som JavaScript: `JBL.embed_v2['jobs'] = [ { id: '396006', url: '/jobs/396006-kpmg-…/', title: '…', … }, … ]`.
  Opslag: `https://emp.jobylon.com/jobs/{id}-…/` (tjek domænet) med JSON-LD `datePosted`. Cloudflare foran: får vi 403/challenge,
  så markér kilden som blokeret – ingen omgåelse.
- **Tyskland / UK:** SuccessFactors CSB (se ovenfor).
- **Schweiz:** jobs.kpmg.ch – robots.txt forbyder alt. Ikke med.
