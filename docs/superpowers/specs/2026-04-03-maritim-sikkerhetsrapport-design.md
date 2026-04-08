# Maritim Sikkerhetsrapport — Design Spec
**Dato:** 2026-04-03
**Status:** Godkjent

## Oversikt

Et automatisk oppdatert nyhets-dashboard for maritim forsvarssikkerhet, med fokus på miner, undervannssikkerhet og ROV-teknologi. Dashboardet henter nyheter og regelverk fra norske og internasjonale kilder to ganger daglig, og publiseres som en statisk nettside via GitHub Pages. Primærbruker er en arbeidsgiver som utvikler undervann-ROV for minerydding.

---

## Arkitektur

Systemet består av tre komponenter som kjører i sekvens:

1. **Python-script** — henter, filtrerer og strukturerer innhold fra datakilder
2. **HTML-generator** — rendrer innholdet til en statisk nettside via Jinja2-template
3. **GitHub Actions** — orkestrerer kjøringen to ganger daglig og deployer til GitHub Pages

### Dataflyt

```
[RSS-feeds / nettsider]
        ↓
[Python-script (fetch + parse + filter)]
        ↓
[Genererer docs/data.json + docs/index.html]
        ↓
[GitHub Actions: commit + push (bare hvis endringer)]
        ↓
[GitHub Pages serverer dashboardet]
        ↓
[Arbeidsgiver åpner URL i nettleser]
```

---

## Datakilder

### Norske myndighetskilder — web scraping (ingen RSS tilgjengelig)

Norske myndighetsnettsider tilbyr ikke standard RSS-feeds. Innholdet hentes via `requests` + `BeautifulSoup`.

| Kilde | URL | Metode | Format |
|-------|-----|--------|--------|
| Forsvaret.no | `https://www.forsvaret.no/aktuelt` | Scrape artikelliste | HTML |
| Kystverket.no | `https://www.kystverket.no/nyheter/` | Scrape nyhetsliste | HTML |
| Sjøfartsdirektoratet | `https://www.sjofartsdir.no/nyheter/` | Scrape nyhetsliste | HTML |

**Scraping-strategi:** Hent HTML fra listesiden, parse artikkelkort (tittel, dato, URL, ingress) via CSS-selektorer. Selektorer verifiseres under implementasjon og dokumenteres i koden. Feilhåndtering:
- HTTP 4xx/5xx: loggfør feil, hopp over kilden, behold forrige kjøringens data
- Vellykket HTTP 200, men CSS-selektorer returnerer null resultater: loggfør advarsel (`WARNING: 0 articles scraped from [kilde] — page structure may have changed`) og behandle som feil (behold gammel data for den kilden)

**Merk:** Sjøfartsdirektoratet publiserer også rundskriv som PDF. PDF-innhold inkluderes ikke i v1 — kun HTML-nyheter hentes.

### Internasjonale fagkilder — RSS-feeds

| Kilde | RSS URL | Språk |
|-------|---------|-------|
| USNI News | `https://news.usni.org/feed` | Engelsk |
| Defense News | `https://www.defensenews.com/arc/outboundfeeds/rss/` | Engelsk |
| Naval News | `https://www.navalnews.com/feed/` | Engelsk |
| Breaking Defense | `https://breakingdefense.com/feed/` | Engelsk |
| The Maritime Executive | `https://maritime-executive.com/rss/articles` | Engelsk |

Google News RSS brukes **ikke** som kilde — feeden er udokumentert, ustabil og upålitelig for forsvarsnyheter.

### Nøkkelord for filtrering

**Norsk:** `mine`, `minerydding`, `undervann`, `ROV`, `havnesikkerhet`, `maritim sikkerhet`, `sjøforsvar`, `ubåt`, `MCM`

**Engelsk:** `naval mine`, `underwater ROV`, `mine countermeasure`, `MCM`, `UUV`, `AUV`, `underwater security`, `port security`, `subsea defense`, `ROV defense`

En artikkel inkluderes hvis minst ett nøkkelord finnes i tittel eller sammendrag (case-insensitive).

---

## Dashboard-layout

Én statisk HTML-side med følgende seksjoner:

### Header
- Tittel: "Maritim Sikkerhetsrapport — Miner & Undervannssikkerhet"
- Sist oppdatert: dato og klokkeslett (UTC)
- Neste planlagte oppdatering: statisk label, f.eks. "Neste oppdatering: 12:00 UTC" — beregnet fra tidspunkt for kjøringen, ikke en live nedtelling
- JavaScript-basert live nedtelling til neste oppdatering er utenfor scope for v1

### Seksjon 1 — Aktuelle nyheter
- Norske nyheter øverst, internasjonale under
- Kortvisning: tittel, kilde, dato, ett avsnitt sammendrag
- Klikkbare lenker til originalkilde
- Maks 10 artikler per underseksjon, maks 30 dager gammel

### Seksjon 2 — Regelverk & Havnesikkerhet
- **Kilde:** Kun artikler fra Kystverket og Sjøfartsdirektoratet
- Tittel, dato, kort beskrivelse og lenke til offisiell kilde
- Maks 10 artikler, maks 90 dager gammel (regelverk oppdateres sjeldnere)

### Seksjon 3 — ROV & Teknologi
- **Kilde:** Artikler fra alle kilder som inneholder ROV/UUV/AUV/mine countermeasure-nøkkelord
- Internasjonale fagkilder prioriteres
- Maks 10 artikler, maks 30 dager gammel

**Seksjonstildeling:**
- Seksjon 2 har kildeprioritering — Kystverket/Sjøfartsdirektoratet-artikler havner alltid her
- Seksjon 3 tilordnes basert på nøkkelord (ROV, UUV, AUV, MCM, mine countermeasure)
- Seksjon 1 får alt som ikke tilhører seksjon 2 eller 3
- En artikkel kan kun tilhøre én seksjon (prioritet: 2 > 3 > 1)

### Footer
- Automatisk generert tidsstempel
- Lenke til GitHub-repository

### Visuelt
- Mørk marineblå fargepalett
- Rent og profesjonelt utseende
- Responsivt — fungerer på mobil og desktop
- HTML `lang="no"` på rotnivå; internasjonale seksjoner markert med `lang="en"` på container-element

---

## Repository-struktur

```
nettbyen-dashboard/
├── .github/
│   └── workflows/
│       └── update.yml        # GitHub Actions cron-jobb
├── scripts/
│   └── fetch_news.py         # Henter og prosesserer nyheter
├── templates/
│   └── index.html.j2         # Jinja2 HTML-template
├── docs/                     # GitHub Pages serverer herfra
│   ├── index.html            # Generert dashboard
│   └── data.json             # Rådata fra siste kjøring
└── requirements.txt          # Pinnede avhengigheter
```

---

## GitHub Actions Workflow

**Fil:** `.github/workflows/update.yml`

**Kjøretider:** 04:00 og 12:00 UTC (= 06:00 og 14:00 CEST / 05:00 og 13:00 CET)

**Steg:**
1. Checkout repository
2. Sett opp Python 3.11
3. Installer avhengigheter (`pip install -r requirements.txt`)
4. Kjør `scripts/fetch_news.py`
5. Sjekk om filer er endret (`git diff --quiet docs/`)
6. Commit og push **kun hvis endringer finnes** (unngår feilstatus på uendrede kjøringer)

**Feilhåndtering i workflow:**
- Hvis `fetch_news.py` avslutter med ikke-null exit-kode, stoppes workflowen uten commit
- Forrige gyldige `docs/index.html` og `docs/data.json` beholdes i git — dashboardet forblir synlig med gammel data
- GitHub Actions-logg viser feilen; utvikler kan inspisere loggen

---

## Python-script

**Fil:** `scripts/fetch_news.py`

**Avhengigheter (pinnede versjoner i requirements.txt):**
```
feedparser==6.0.11
requests==2.31.0
beautifulsoup4==4.12.3
jinja2==3.1.4
```

**Logikk:**
1. Hent RSS-feeds fra internasjonale kilder med `feedparser`
2. Hent HTML fra norske myndighetsnettsider med `requests` + `BeautifulSoup`
3. For hver kilde: loggfør feil og fortsett — ikke avbryt hele kjøringen ved én feilende kilde
4. Parse artikler til felles datastruktur (se data.json-schema nedenfor)
5. Filtrer på nøkkelord (tittel + sammendrag, case-insensitive)
6. Dedupliser: primærnøkkel = normalisert URL (fjern UTM-parametere, trailing slash); sekundær = normalisert tittellikhet > 85% (via `difflib.SequenceMatcher`)
7. Tilordne seksjoner (prioritet: 2 > 3 > 1) — dette gjøres FØR sortering og begrensning
8. Per seksjon: filtrer ut artikler eldre enn seksjonens maksalder, sorter etter dato (nyeste først), behold maks antall
9. Hvis totalt 0 artikler er hentet på tvers av alle seksjoner: avslutt med exit-kode 1 (utløser workflow-feil, ingen fil overskrives)
10. Render HTML via Jinja2-template, skriv `docs/index.html`
11. Skriv `docs/data.json`

---

## data.json-schema

```json
{
  "generated_at": "2026-04-03T06:00:00Z",
  "next_update_utc": "12:00 UTC",
  "sections": {
    "nyheter": [
      {
        "title": "Artikkelens tittel",
        "url": "https://kilde.no/artikkel",
        "published": "2026-04-03T05:30:00Z",
        "source": "Forsvaret.no",
        "language": "no",
        "summary": "Kort sammendrag av artikkelen..."
      }
    ],
    "regelverk": [],
    "rov_teknologi": []
  }
}
```

**Jinja2-template context-variabler:**
- `generated_at` — ISO 8601 streng
- `next_update_utc` — streng, f.eks. `"12:00 UTC"`
- `sections.nyheter` — liste av artikkelobjekter
- `sections.regelverk` — liste av artikkelobjekter
- `sections.rov_teknologi` — liste av artikkelobjekter

---

## Deploy

- GitHub Pages aktiveres på `docs/`-mappen i `main`-branch
- Arbeidsgiver får én permanent URL: `https://[github-brukernavn].github.io/[repo-navn]/`
- Ingen innlogging eller server nødvendig — åpen nettside

---

## Begrensninger og risiko

| Risiko | Sannsynlighet | Håndtering |
|--------|--------------|------------|
| Norsk myndighetsnettside endrer HTML-struktur | Medium | Loggfør feil, behold gammel data, fiks CSS-selektorer manuelt |
| Internasjonal RSS-feed er nede | Lav | Loggfør og hopp over — de andre kildene dekker fortsatt |
| Alle kilder feiler samtidig | Svært lav | Exit-kode 1, workflow-feil, gammel HTML beholdes synlig |
| GitHub Actions-kvote overskrides | Svært lav | 2×60 kjøringer = ~120 min/mnd av 2000 gratis min |
