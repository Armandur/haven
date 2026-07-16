# Roadmap - Håven

Nyast/närmast först. Faserna följer SPEC.md avsnitt 13.

## Närmast (påsatta todos)

- [x] **Visa ändamålskalendern** (`/kalender`) - läsvy per församling; ny kalender
  för nytt år laddas upp via kalender-slotten på översikten. (klar)
- [x] **Filuppladdning i webben.** (klar) Uppladdning på översikten av Swish-rapport,
  KOB-exporter och kalender: en request per fil (per-fil-persistens), begränsad
  parallellitet, per-fil-progress och full felmeddelandetext, temp-fil + testparsning
  med atomisk spar (trasig fil ersätter aldrig fungerande). Progressivt (funkar utan JS).
- [x] **Import-fellogg** - fel per fil visas med full text i uppladdnings-overlayn. (klar)
- [x] **/konfig: Ändra/Ta bort på samma rad.** (klar)
- Not: mottagar-/församlingskonfigen är **global**, inte per fil - "upptäckta"
  mappningar ackumuleras och gäller alla filer (redan uppfyllt av datamodellen).

- [x] **Fäll ut berörda rader i historiken.** (klar) Varje historikpost på
  `/justeringar` kan expanderas och visa exakt vilka transaktionsrader ändringen
  gällde. `regelhistorik` sparar urvalet (tx_ids/filter/scope) vid händelsen och
  routen löser upp dem mot periodens rapport med samma matchningslogik som
  reglerna. Fungerar även för borttagna regler.

- [x] **Fäll ut transaktioner per post i arbetskön.** (klar) Varje kopost ska kunna
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
- [x] Radval: välj församling/konto, se raderna, filtrera live (datum/meddelande)
  och bocka för de rader som ska justeras. Stabil tx_id per transaktion; regeln
  lagrar bockade tx_ids (filter finns kvar som alternativ, bakåtkompatibelt).
- [ ] Kvar: historik på överstyrningar (vem/när/tidigare värde) - byggs med Fas 2.

## Fas 2 - tillstånd, status och redigerbar konfiguration

- [x] Statusspårning (`status_service.py`, vy `/status`): tillstånd per enhet
  (Ej påbörjad -> Påbörjad -> Registrerad -> Avstämd) härlett ur arbetsköns
  bekräftelser + KOB-avstämningen. Ersätter Registreringar-matrisen.
- [x] Rapportregister + idempotens + ändringsdetektering (`rapport`-tabell): samma
  rapport dubbelregistrerar inte, och en ändrad version (ny innehålls-hash på samma
  filnamn) flaggas så tx_id-baserade regler kan ses över. Månadsöversikt på
  dashboarden.
- [x] Historik på regeländringar (`regelhistorik`-tabell, visas på `/justeringar`):
  skapad/borttagen loggas med tidpunkt och beskrivning. ("Vem" saknas tills auth
  finns - enanvändarmiljö.)
- [x] Redigerbar konfiguration (`/konfig`): mottagarmappning och församlingsalias
  flyttade till SQLite (fröade från config), redigerbara i UI:t. Nya/okända
  mottagare kan klassas direkt från `/omatchade`. Normaliseringen laddas om vid
  ändring. Grunden för att andra enheter ska kunna använda verktyget utan
  kodändring. (Ändamålskalendern förblir Excel-filen - fastställt beslut.)

**Fas 2 klar.**

## Fas 3 - bekvämlighet

- Halvautomatisk KOB-inmatning via återanvänt userscript. Först här behöver
  verktyget skilja på att komplettera befintliga tillfällen och skapa nya, och
  veta att R- och S-tillfällen aldrig skapas.
- Arkivering av gammalt underlag.
