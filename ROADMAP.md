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

## Fas 1 - särskilda poster + KOB-avstämning

- Utbrytning av särskilda poster (filter på meddelande/datum), t.ex. loppis, ljus.
- Inläsning av KOB-exporterna finns redan (`ingest_kob.py`); bygg avstämning per
  församling och tillfälle med tydliga diffar. Endast `Swish 1`-rader jämförs.
- Ändamålstext-normalisering mellan kalender och KOB (t.ex. "Svenska Kyrkans
  Unga" vs "Svenska Kyrkans Unga / SALT, barn och unga i EFS").
- Manuell överstyrning av föreslaget ändamål (spec 8.3) - fångar Stigsjö-typen
  där framåtfyllningen är "rätt enligt regeln" men avviker mot KOB.

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
