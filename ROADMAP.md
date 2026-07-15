# Roadmap - Håven

Nyast/närmast först. Faserna följer SPEC.md avsnitt 13.

## Närmast (påsatta todos)

- [ ] **Fäll ut transaktioner per post i arbetskön.** Varje kopost ska kunna
  expanderas för att visa de underliggande Swish-transaktionerna (datum, tid,
  belopp, meddelande). Stödjer spec 8.2 (visa meddelandefältet) och gör det lätt
  att upptäcka avvikelser (t.ex. Stigsjö-fallet där betalningar 05-23 gällde en
  konsert utanför kalendern). Data finns redan i aggregatposterna; kräver att
  `Kopost` bär med transaktionerna och en `<details>`-utfällning i `ko.html`.
  Låg insats.

- [ ] **Kanoniskt församlingsnamn = KOB-formen.** Visa "Härnösands
  domkyrkoförsamling" (inte "Domkyrkoförsamlingen") och "Stigsjö församling"
  (litet f) överallt, så underlaget matchar exakt det handläggaren ser och
  skriver i KOB. Innebär att byta `kanoniskt` <-> `alias` i `app/config.py`
  (Swish-stavningen blir alias). Matchningen är kortkodsbaserad så
  ändamålsmatchningen påverkas inte; klassning och KOB-normalisering behåller
  Swish- och KOB-formerna som alias. Låg insats, avviker medvetet från spec 6.4
  som listade Swish-formen som kanonisk.

## Fas 1a - KOB-avstämning (klar)

- [x] Avstämning per församling och tillfälle (`reconcile.py`, vy `/avstamning`).
  Endast `Swish 1`-rader jämförs, nettorollup per församling.
- [x] Ändamålstext-normalisering mellan kalender och KOB ("Svenska Kyrkans Unga
  ½, ..." vs "Svenska Kyrkans Unga / ...").
- [x] Gåvoavstämning per konto med nyckelordsmappning mot KOB-insamlingsrader.

## Fas 1b - särskilda poster + ändamålsöverstyrning (klar)

- [x] Ändamålsöverstyrning (`regler.py`, vy `/justeringar`) - rättar
  framåtfyllningen via filter på församling/datum/meddelande, sätter
  ändamål/typ/tillfällesdatum. Löser Stigsjö-typen (05-17 Diakonala -> 05-23 Musik).
- [x] Särskilda poster - bryter ut loppis/ljus/konsert ur månadssumman via filter.
  Invariant: allmän + särskilda = kontototal.
- [ ] Kvar: historik på överstyrningar (vem/när/tidigare värde) - byggs med Fas 2.
- [ ] Kvar: live-förhandsvisning av filterträff (antal/summa) innan man sparar.

## Fas 2 - tillstånd, status och redigerbar konfiguration

- Flytta mottagarmappning, församlingsalias och ändamålskalender till SQLite och
  gör dem **redigerbara i ett gränssnitt**. Detta är förutsättningen för att
  verktyget ska kunna bli generellt och användas av andra enheter/pastorat utan
  kodändring (påsatt todo). Byggs när det finns konkret efterfrågan från fler
  enheter - inte spekulativt i förväg.
- Statusspårning per verksamhet/församling (Ej påbörjad -> Registrerad -> Avstämd)
  som ersätter matrisen `Registreringar`.
- Idempotens och historik (rapport-hash, överstyrningshistorik).

## Fas 3 - bekvämlighet

- Halvautomatisk KOB-inmatning via återanvänt userscript. Först här behöver
  verktyget skilja på att komplettera befintliga tillfällen och skapa nya, och
  veta att R- och S-tillfällen aldrig skapas.
- Arkivering av gammalt underlag.
