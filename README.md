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

**Fas 1b (klar):** handläggarregler i vyn `/justeringar` - ändamålsöverstyrning
(rättar framåtfyllningen när den avviker mot KOB, t.ex. Stigsjö-konserten) och
särskilda poster (bryter ut loppis/ljus/konsert ur ett gåvokontos månadssumma).
Reglerna persisteras i SQLite och tillämpas på hela flödet.

**Fas 2 (påbörjad):** statusspårning i vyn `/status` - tillstånd per församling
och verksamhet (Ej påbörjad -> Påbörjad -> Registrerad -> Avstämd) härlett ur
arbetsköns bekräftelser och KOB-avstämningen. Ersätter Registreringar-matrisen.

Rapporter registreras med innehålls-hash (idempotens: samma rapport
dubbelregistreras inte; en ändrad version flaggas), och dashboarden visar en
översikt över importerade månader.

Kommande: historik på regeländringar och redigerbar konfiguration (Fas 2 forts.),
halvautomatisk KOB-inmatning (Fas 3).

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
