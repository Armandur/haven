# Roadmap - Håven

Nyast/närmast först. Faserna följer SPEC.md avsnitt 13.

## Närmast (påsatta todos)

- [x] **Redigera befintliga ändamålsöverstyrningar** (klar) - Ändra-knapp som
  förifyller ett redigeringsformulär och uppdaterar målet (ändamål/typ/
  tillfällesdatum); urvalet behålls, historiken loggar "ändrad". Vill man ändra
  själva radurvalet får man ta bort och skapa ny.

- [x] **Filter "visa bara diffar" på /avstamning.** (klar) Toggle som döljer rena
  församlingskort och rader utan diff, i både kollekt- och gåvatabellen.
  JS-toggle (progressivt, allt visas utan JS); märk rader `data-diff` och göm de
  utan. Gäller både kollekt- och gåvatabellen. Liten insats.

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

- [x] **Kanoniskt församlingsnamn = KOB-formen.** (klar) "Härnösands
  domkyrkoförsamling" och "Stigsjö församling" (litet f) överallt; Swish-stavningen
  blev alias.

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
- [x] Historik på överstyrningar (skapad/borttagen + tidpunkt + berörda rader) -
  klar. "Vem" saknas tills auth finns; "tidigare värde" vid redigering hör ihop
  med redigera-överstyrning-todon ovan.

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

- [x] **KOB-handboken (PDF, 76 s) -> HTML-dokumentation.** (klar, docs/kob-handbok.html) `KOB handbok.pdf`
  (i vmworkspace) är textbaserad med skärmdumpar av formulären. Omarbeta till
  `docs/kob-handbok.html` (text sida-för-sida + inline-skärmdumpar + TOC), som
  fältmappnings-referens för Fas 3 (kompletterar Claude-for-Chrome-prompten).
  Måttlig insats, delegerbar. Markdown-variant möjlig om LLM-referens är målet.
- [x] Kartlägg KOB:s inmatningsgränssnitt (klar): `docs/KOB-INMATNING.md` -
  fullständig spec (selektorer, flöden, komplettera-vs-skapa, R/S-gruppering,
  gränsvärdesvarning, attest-spärr) kartlagd mot KOB:s övningssystem. Prompten
  som användes: `docs/kob-inmatning-prompt.md`.
- [x] **JSON-export ur registreringskön** (klar) - "Kopiera underlag som JSON" på
  `/ko` + endpoint `/ko/export.json`. En post per registreringsenhet (F,
  R/S med delposter, insamling månad/särskild/per-ändamål), öresäkra strängbelopp,
  Swish 1. Kontraktet som userscriptet läser (bygg_export i ko_service).
- [~] **Userscriptet** som läser JSON:en och förifyller KOB enligt
  `docs/KOB-INMATNING.md` (`userscript/haven-kob.user.js`). **F-komplettering
  byggd** (sök på Typ+datum med tom Purpose → töm DataTables-filter →
  klientsidig disambiguering på Beslutat av + Kollektändamål → grönt +, rad-scopat
  belopp + Swish 1, stannar före Spara). Attest = opt-in-läge (default av,
  sessions-PIN endast i minnet). Rena hjälpfunktioner enhetstestade i node.
  **Ej live-verifierat mot KOB** (ingen åtkomst härifrån) - all DOM-interaktion
  behöver Rasmus test mot övning/skarp. Kvarstår: R/S-komplettering,
  insamling/gåva, skapa-vy-förifyllnad, attest-DOM (PIN-modal/makulera, §11),
  skarpt system-prefix/host, per-ändamål-mottagare (spec 8).
  - [ ] **Auto-uppdatering av scriptet.** Lägg `@updateURL`/`@downloadURL` →
    `http://ubuntu-ai:8003/kob-userscript.user.js` så Tampermonkey/Violentmonkey
    själv upptäcker ny `@version` och uppdaterar (schemalagt + manuell "sök efter
    uppdateringar"). Ev. även en "Uppdatera script"-länk i panelen som öppnar
    downloadURL:en (manager visar update-prompten från valfri KOB-sida). En helt
    tyst självuppdatering från panelen går INTE - managern måste göra installet
    (avsiktligt, säkerhet). Liten insats, hög nytta.
- Arkivering av gammalt underlag.
