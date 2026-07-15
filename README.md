# Håven - Swish-kollekt och gåvoavstämning

Verktyg för Härnösands pastorat som läser månadens Swish-rapport, klassificerar
varje transaktion som kollekt eller gåva, föreslår rätt ändamål och kollekttyp
via ändamålskalendern, aggregerar till de registreringsenheter KOB behöver och
stämmer av mot KOB-exporter. Ersätter en skör Excel-arbetsbok med Power Query.

Se `SPEC.md` för fullständig kravspecifikation och `CLAUDE.md` för kodbasöversikt.

## Status

**Fas 0 (klar):** kärnpipeline - import, normalisering, klassning,
ändamålsmatchning (framåtfyllning), aggregering till registreringsunderlag
(F församlingsvis, R/S grupperat per tillfälle) och lista över omatchade rader.
Validerad mot maj 2026 (kollekt per församling och gåva-månadssummor stämmer
mot KOB på öret).

**Fas 1a (klar):** KOB-avstämning per församling och tillfälle (kollekt) och
per konto (gåva), med diff-flaggning och nettorollup per församling. Endast
KOB:s Swish 1-rader jämförs. Validerad mot maj 2026 (alla församlingar nettar,
Stigsjö-avvikelsen fångas som två motverkande diffar).

Kommande: särskilda poster + ändamålsöverstyrning (Fas 1b), SQLite-tillstånd och
statusspårning (Fas 2), halvautomatisk KOB-inmatning (Fas 3).

## Köra

Beroenden hanteras med [uv](https://github.com/astral-sh/uv) (ingen global pip
behövs). Datafiler ligger i `data/` (gitignorat - innehåller givarmeddelanden).

### CLI-validering

```
uv run cli.py "data/1948 25-05 Uppdelad.xlsx" \
    --kob-kollekt "data/KOB_ParishCollectionReport (18).xls" \
    --kob-insamling "data/KOB_Accounts_Contributions (15).xls"
```

Skriver ut registreringsunderlaget, omatchade rader och en självkontroll
(delarna ska motsvara rapportens total) samt en jämförelse mot KOB.

### Webbtjänst

```
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Nås över Tailscale i homelabben. Se `.env.example` för konfiguration.

### Tester

```
uv run --with pytest pytest
```

Facit-testet i `tests/test_maj2026.py` låser maj 2026-siffrorna och hoppas över
om `data/`-filerna saknas.
