# CLAUDE.md - Håven (kollektverktyg)

Kodbasöversikt för Claude. Kravspec finns i `SPEC.md`. Globala preferenser
(språk, git, delegering) gäller från `~/.claude/CLAUDE.md`.

## Vad projektet gör

Läser Härnösands pastorats månatliga Swish-rapport, klassar transaktioner som
kollekt eller gåva, matchar ändamål via ändamålskalendern, aggregerar till
KOB:s registreringsenheter och stämmer av mot KOB-exporter. Underlag för
manuell inmatning i KOB - ingen automatisk registrering i MVP.

## Stack

- Python 3.12, beroenden via **uv** (pyproject.toml). Ingen global pip/venv.
- FastAPI + Jinja2 + uvicorn för webbvyn (Fas 0+).
- openpyxl (.xlsx: Swish-rapport, kalender), xlrd==2.0.1 (.xls: KOB-export).
- SQLAlchemy + SQLite för tillstånd/idempotens (introduceras skarpt i Fas 2).
- Belopp hanteras som `Decimal` hela vägen (öresäkert, inga float-diffar).

## Filstruktur

```
app/
  config.py            # konstanter, enums, frödata (mottagarmappning, församlingsalias)
  core/                # ren pipeline, testbar utan webb
    models.py          # värdeobjekt (Transaktion, Kalenderrad, Kob*-rader, Underlag)
    normalize.py       # namnnormalisering, to_decimal
    ingest_swish.py    # Swish-rapport (dynamisk rubrik, metadata, summeringsfilter)
    ingest_kalender.py # ändamålskalender (ett blad per församling)
    ingest_kob.py      # båda KOB-exporterna (serienummerdatum, flera blad)
    classify.py        # kollekt/gåva via mottagarmappning
    match.py           # ändamålsmatchning (framåtfyllning, Kalenderindex)
    aggregate.py       # registreringsunderlag (F / R-S-grupper / gåva)
    reconcile.py       # KOB-avstämning (kollekt per tillfälle, gåva per konto)
    regler.py          # handläggarregler: ändamålsöverstyrning + särskilda poster
    pipeline.py        # orkestrering: las_rapport + bearbeta (tar regler)
  routes/              # FastAPI-routes (webbvy)
  templates/ static/   # Jinja2 + Pico CSS + tokens.css
  main.py              # app, lifespan, router-registrering
cli.py                 # CLI för validering mot en rapport
tests/                 # facit-test mot maj 2026
data/                  # in-filer (gitignorat, givarmeddelanden = personuppgifter)
```

## Viktiga designbeslut och fallgropar

- **Datumankare = transaktionsdatum.** Framåtfyllning: ändamål(P,D) = raden i
  P:s kalender där Datum = max(Datum <= D). Se `match.py`.
- **Registreringsenhet = tillfällesdatum, inte betalningsdatum.** Aggregeringen
  grupperar kollekter på `matchad_kalenderdatum` så att en betalning dagen efter
  gudstjänsten folas in på gudstjänstens tillfälle. Se `aggregate.py`.
- **KOB-avstämning: bara `Swish 1`-rader.** KOB innehåller även Kontant-rader
  för samma tillfälle; endast Swish 1 jämförs mot Swish-rapporten.
- **KOB-datum är Excel-serienummer** och datan ligger utspridd över flera blad.
- **Swish-rubrik hittas dynamiskt** via "Bokföringsdatum"; summerings-, tom- och
  totalrader saknar bokföringsdatum och filtreras på det.
- **Testmånad = maj 2026** (filnamnet "25-05" till trots; innehållet är maj 2026).
  Facit: total 30 692, Domkyrko 5 016, ACT 6 656, Diakoni 1 885, 0 omatchade.
- **tx_id** är en stabil hash per transaktion (innehåll + dup-index i filordning),
  satt vid inläsning i `ingest_swish.py`. Används för radval i justeringsreglerna;
  överlever omläsning av samma fil. Regler tillämpas på tx_id om satt, annars
  på filter (bakåtkompatibelt).
- **DB-migrering:** raw ALTER TABLE-guards i `database._migrera()` (ingen Alembic
  i Fas 0-1). Lägg nya kolumner där.
- **Kalendern kan vara ofullständig** för extra-gudstjänster (t.ex. konsert
  23 maj). Då blir framåtfyllningen "rätt enligt regeln" men avviker mot KOB:s
  faktiska tillfälle - fångas i avstämningen (Fas 1) och via manuell
  överstyrning (spec 8.3).
- **Ändamålstext skiljer sig** mellan kalender och KOB (t.ex. "Svenska Kyrkans
  Unga" vs "Svenska Kyrkans Unga / SALT..."). Behöver aliasnormalisering vid
  avstämning per ändamål i Fas 1.

## Frödata

Mottagarmappning och församlingsalias ligger i `app/config.py`, bekräftade mot
maj 2026. Flyttas till SQLite och blir redigerbara i Fas 2.

## Köra

Se README.md. CLI: `uv run cli.py <swishfil>`. Test: `uv run --with pytest pytest`.

## Dev-serverflöde (stående instruktion från Rasmus)

När en synlig funktion byggts eller ändrats: **starta själv igång servern och
lämna en klickbar länk** så Rasmus kan testa direkt (även från telefon).

- Hämta ledig port med `svc port`, starta uvicorn i bakgrunden med stdout/stderr
  till `dev.log`, smoke-testa med `curl` och browser-verifiera (obscura/shot).
- Ge alltid full `http://ubuntu-ai:PORT/`-länk (plus relevant subsökväg, t.ex.
  `/ko`, `/underlag`) - aldrig `localhost`/`127.0.0.1`.
- Registrera tjänsten i portalen (`svc register haven --port N --project haven
  --pid PID`) medan den kör.
- **Tillåtelse att städa egna orphanade Håven-servrar:** om en tidigare
  Håven-uvicorn glömts kvar (t.ex. efter en `/clear`), identifiera exakt PID
  (`ss -tlnp`, verifiera mot `svc list` att det är haven) och döda bara den.
  Gäller enbart Håvens egna processer - rör aldrig andra projekts servrar.
