# KOB-INMATNING.md
Teknisk spec för userscript som förifyller KOB:s inmatningsformulär utifrån Håvens registreringsunderlag.
Kartlagd 2026-07-16 mot KOB Övningssystem (version 2025.3.2), jämförd mot KOB-handboken (14 maj 2025-utgåvan).

Systemet är byggt med ASP.NET MVC + jQuery/jQuery UI (widgets: `hasDatepicker`, `ui-autocomplete-input`, `ui-selectmenu`-liknande combo-fält). Inget React/Angular/Vue. Inget synligt CSRF-token-fält hittades i formulären (auth sker via sessionscookie) – notera dock att detta INTE är verifierat på nätverksnivå, bara i DOM.

> **Not (Håven):** Denna fil är svaret från Claude-for-Chrome-kartläggningen (se `docs/kob-inmatning-prompt.md`). Inklistringen kapades mitt i avsnitt 6 (gemensam fältordlista); den delen är kompletterad ur avsnitt 1–5 och tydligt märkt. Om originalets avsnitt 6 hade fler rader/nyanser, klistra in svansen så uppdaterar vi.

---

## 0. Gemensamt för alla flöden

- Aktiv enhet väljs i headern (`select#global_unitselect`). Detta styr vilket pastorat/vilka församlingar som är tillgängliga i formulären. Userscriptet bör läsa/verifiera detta värde innan ifyllning, och INTE ändra det automatiskt utan att användaren ser det.
- Sidor laddas som vanliga MVC-sidor (full navigation), men Spara-knappar gör AJAX-anrop (ingen redirect). Resultat visas som en grön/röd "noty"-notis (`div.noty_bar`, `div.noty_message`) mitt i sidan.
- Gränsvärdesvarningen och vissa andra varningar renderas också via **noty** (`div.noty_bar.noty_type_warning`) med knappar `button#button-0` ("Ja") och `button#button-1` ("Nej") i en `div.noty_buttons`. OBS: id:n `button-0`/`button-1` är sannolikt inte garanterat unika/stabila mellan noty-instanser – identifiera hellre knappen via text ("Ja"/"Nej") inom `.noty_bar` som är synlig i DOM just då.
- Belopp skrivs med **komma som decimaltecken** (t.ex. `1234,50`). Efter sparning visas beloppet omformaterat med mellanslag som tusentalsavgränsare (t.ex. `1 234,50`). Skriv alltid in med komma, aldrig punkt.
- Datumfält (`OccasionDate`, `CollectedDate`) är jQuery UI-datepicker (`hasDatepicker`) men accepterar direkt textinmatning i formatet `YYYY-MM-DD` utan att datepicker-kalendern behöver öppnas. Tryck Escape eller klicka utanför för att stänga ev. kalender-popup innan nästa fält fylls i.
- Flera `id`-attribut i rad-tabeller (kollektbelopp, insamlingsrader) är **inte unika** – samma `id` (t.ex. `amount_Amount`, `amount_PaymentMethodID`) återanvänds i varje tabellrad (`tr.amountRow.odd/even`). Rader har inga data-GUID-attribut. Identifiera rätt rad via textinnehållet i kolumnerna "Församling"/"Kollektställe" i samma `<tr>`, inte via id/name.
- Ingen synlig CSRF-token i formulären. Inga iframes påträffade i något av flödena.

---

## 1. Församlingskollekt (F)

### 1.1 Navigering
- Skapa nytt tillfälle: Meny **Kollekt → Kollekttillfälle – skapa nytt** → `GET /KOB_Utb1/Web/Collection/CollectionOccasion/Main` (utan querystring = tomt formulär).
- Efter sparat tillfälle: URL blir `.../Collection/CollectionOccasion/Main?collectionOccasionid={GUID}` – deep-linkbar.
- Registrera belopp på befintligt eget tillfälle: Meny **Kollekt → Kollektbelopp – registrera** → lista "tillfällen med ej registrerade belopp" (idag + 60 dagar bakåt) → klick på rad → samma `CollectionOccasion/Main?collectionOccasionid=...`-vy.
- Om tillfället inte finns i den listan: **Sök kollekttillfälle** (Meny Sök → Kollekttillfälle, eller knappen på registreringslistan) → `GET /Collection/CollectionOccasionSearch/Search` – formuläret postar som querystring, t.ex. `?Type={GUID}&Purpose=&ReadyMarked=&OccasionDateFrom=&OccasionDateTo=`, dvs **parametriserbart/deep-linkbart**.

### 1.2 Komplettera vs. skapa
Eftersom övningssystemet saknade registrerade församlingskollekter skapades ett nytt tillfälle från grunden för att kartlägga hela vägen. Beslutsregel för userscriptet: sök alltid först (Sök kollekttillfälle med Typ=Församlingskollekt + datumintervall + ändamål). Hittas exakt en träff på rätt datum/ändamål/kollektställe → öppna och komplettera belopp. Hittas ingen träff → skapa nytt tillfälle.

### 1.3 Fältlista – Kollekttillfälle (skapa nytt)
| Etikett | Typ | Selektor | Möjliga värden | Håven-fält |
|---|---|---|---|---|
| Tillfällesdatum | text, datepicker | `input#OccasionDate[name=OccasionDate]` | fritt datum `YYYY-MM-DD` | gudstjänstdatum |
| Kollekttyp | native select | `select#Type[name=Type]` | `5`=Församlingskollekt nationell organisation, `3`=till egna verksamheten, `4`=till extern kontakt (R/S visas EJ här – kan inte väljas av församling) | kollekttyp F (undertyp bestäms av ändamålets mottagare) |
| Beslutat av | native select | `select#DecidedBy[name=DecidedBy]` | de enskilda församlingarna i aktiv enhet (GUID-värden) | församling |
| Kollektändamål | text m. jQuery UI-autocomplete | `input#Purpose[name=Purpose]` | fritext (för "till egna verksamheten"/"till extern kontakt"); **skrivskyddat/auto-ifyllt** för "nationell organisation" (hämtas från Mottagare+Öronmärkning) | ändamål |
| Kollektställe | native select | `select#CollectionLocationId[name=CollectionLocationId]` | `Alla` + kyrkor (GUID per kyrka) | kollektställe (kyrka) eller "Alla" |
| Notering för egen uppföljning | textarea | `textarea#Note[name=Note]` | fritext | – (ej i Håven) |
| Mottagare (endast "till extern kontakt") | sök+autocomplete | `input#input_search_mottagare` + knapp `input#collectionoccasion_contacts_add` | sökning bland kontaktregister | mottagare/extern kontakt |
| Mottagare (endast "nationell organisation") | native select | `select#FNOReceiver[name=FNOReceiver]` | Act Svenska kyrkan / Svenska kyrkan i utlandet | mottagare |
| Öronmärkning (endast "nationell organisation") | jQuery UI combo (dolt select + synlig autocomplete-input + sökknapp) | dolt `select#EarmarkAllId[name=EarmarkAllId].earmarkContributionDropdown` + synlig `input.ui-autocomplete-input` bredvid | "Ingen öronmärkning" eller insamlingstema (Act) / utlandsförsamlingar (Utlandet) | öronmärkning (om F-posten faktiskt är en nationell-org-kollekt) |
| Spara | knapp | `button.create_occasion` (Alt+S) | – | – |
| Spara och klarmarkera | knapp | `button.create_and_readymark_occasion` (Alt+K) | – | – |

**Viktigt fynd:** För undertyp "till egna verksamheten" fylls **Mottagare-tabellen automatiskt** med egen enhet, 100 %. Klarmarkeringskravet (mottagare valda + 100 %) är alltså redan uppfyllt direkt, och "Spara och klarmarkera" lyckas i ett steg utan extra klick. Detta observerades live: två notiser kom i rad, "Kollekttillfället skapat." och "Kollekttillfället klarmarkerat.".

**Öronmärkning är ett jQuery UI-widget-kombo** (dolt `<select>` synkat mot synligt textfält). Att bara sätta `.value` på det dolda select-elementet räcker sannolikt INTE – widgeten uppdaterar troligen bara sitt UI-state vid egna events. Säkraste metoden: klicka i det synliga sökfältet, skriv sökterm, vänta på dropdown-listan, klicka rätt `<li>`-alternativ (riktig musklick/`mousedown`), inte bara `.val()`.

### 1.4 Fältlista – Kollektbelopp (registrera/komplettera)
Tabellen "Kollektbelopp" har en rad per Församling×Kollektställe (skapas automatiskt utifrån vald Kollektställe = "Alla" eller specifik kyrka vid tillfällets skapande).

| Kolumn | Typ | Selektor (id/name upprepas per rad – matcha via radens text) | Värden |
|---|---|---|---|
| Kollekt ej upptagen | checkbox | `input.notCollected[name="amount.NotCollected"]` | true/false. Är den ikryssad grånas/inaktiveras Belopp, Nr kollektbok och Inbetalningsmetod i samma rad, och "lägg till rad"-ikonen (+) försvinner. |
| Belopp | text | `input.amount[name="amount.Amount"]` (klass `amount numeric resetTimer marginZero rwInput`) | Svenskt talformat, komma decimal |
| Nr kollektbok | text | `input[name="amount.VerificationNumber"]` | fritext/nummer |
| Inbetalningsmetod | native select | `select[name="amount.PaymentMethodID"]` (synlig; det finns även en dold spegel `input.paymentMethodHidden`) | `Kontant`, `Kort`, `Swish 1`, `Swish 2` (GUID-värden, samma GUID-lista återkommer i alla belopps-tabeller i systemet) |
| Lägg till rad (+) | ikonknapp | grön cirkel-ikon längst till höger i varje rad, ingen stabil id – identifiera via `tr.amountRow` + sista `<td>` i den specifika raden | Lägger till en ny, tom Belopp/Inbetalningsmetod-rad för **samma** Församling/Kollektställe (för att registrera samma kollekt uppdelad på fler inbetalningsmetoder) |
| Ta bort (papperskorg) | ikonknapp | visas bara på redan sparade, ej attesterade rader | Tar bort ett registrerat men ej attesterat belopp |
| Spara | knapp | `button` klass `bla` under tabellen, kortkommando Alt+S | Sparar alla ifyllda rader via AJAX |

**Bekräftat live:** vid Spara med belopp som ligger utanför gränsvärdet visas en inline-varning direkt under raden: texten *"Kollektbeloppet är högre än det angivna gränsvärdet på 500,00"* i en gulmarkerad box, samtidigt som en noty-dialog med frågan *"Vill du spara ändå?"* och knappar **Ja**/**Nej** visas. Klick på **Ja** sparar ändå (toast: *"Kollektbeloppen sparade"*). Detta är exakt gränsvärdesvarningen ur handboken – bekräftad, och scriptet måste kunna klicka "Ja" (eller stanna och låta människan klicka).

Efter lyckad sparning: raden får en röd **E**-badge (Ej attesterade) i Församling-kolumnen, beloppet omformateras med tusentalsavgränsare, och en papperskorgsikon dyker upp (går att ta bort igen innan attest).

### 1.5 Klarmarkering / Välj-meny på befintligt tillfälle
På ett redan skapat tillfälle finns knappen **Välj...** (`button` + hamburgerikon) uppe till höger. Menyn innehåller:
- **Nytt** – öppnar tomt formulär för nytt tillfälle (samma som skapa nytt)
- **Avklarmarkera** – tar bort klarmarkeringen (endast synlig på klarmarkerade F-tillfällen; INTE synlig på R/S – se 2.4)
- **Kopiera** – duplicerar tillfället

### 1.6 Attestering (endast kartlagt, ej fullföljt – se säkerhetsnot)
Väg: Meny **Kollekt → Kollektbelopp – ej attesterade** → `GET /Collection/CollectionOccasionSearch/UnAttestedCollectionAmounts` → klick på rad → samma tillfällesvy men filtrerad till "Ej attesterade", med kryssrutor per rad + knapp **"Attestera valda rader"** (`button` grön, klass innehåller `bla`).
Vid klick, om användaren saknar personlig PIN-kod visas först dialogen **"Skapa ny personlig 4-siffrig PIN-kod"** (fält "PIN-kod" + "Verifiera PIN-kod" + knappar **Klar**/**Avbryt**). Efter att PIN skapats försökte systemet attestera automatiskt och gav felmeddelandet: *"Ett eller flera kollektbelopp gick inte att attestera. Användaren saknar attesträtt. Registreras under Arkiv, Administrera användare."* — dvs. attestering kräver att man dessutom är registrerad i Attestregistret, vilket testanvändaren inte var. Jag valde **medvetet att INTE** gå vidare och lägga till attesträtt åt användaren i Administrera användare, eftersom det innebär att ändra behörigheter/åtkomstkontroll – något jag inte utför även i övningsmiljön. Attestflödets DOM (kryssrutor, knapp, PIN-dialog, felmeddelande) är dock fullt dokumenterat ovan.

### 1.7 Komplettera en befintlig F-kollekt (kollega har redan registrerat/attesterat kontantbeloppet)
**Vanligt Håven-fall:** en kollega har redan skapat och klarmarkerat
församlingskollekttillfället och registrerat (och kanske attesterat) det
**kontanta** beloppet. Månaden efter ska vi komplettera samma tillfälle med det
**swishade** beloppet.

- **Tillfället syns INTE i "Kollektbelopp – registrera"-listan** (den visar bara
  tillfällen som *saknar* registrerade belopp; så fort ett kollektställe fått ett
  belopp faller det ur listan). Använd därför **Sök kollekttillfälle** (deep-link,
  se 1.1/2.1) med Typ=Församlingskollekt + datum + ändamål för att hitta det.
- På tillfället: hitta rätt **kollektställe-rad** (matcha via text), klicka på den
  **gröna +-ikonen** längst till höger på raden och fyll i en ny rad med Swish-
  beloppet och Inbetalningsmetod = Swish 1. Handboken ("Lägg till ytterligare
  belopp", s27) bekräftar: *det går att lägga till ett belopp där det redan finns
  ett registrerat, makulerat, **attesterat** eller utbetalt belopp* – man ändrar
  alltså inte kollegans kontantrad, man lägger till en egen Swish-rad bredvid.
- Filterknappen **"alla"** i listen kollektbelopp visar alla kollektställen och
  deras status (ska vara markerad vid registrering). Kollegans kontantbelopp har
  status **A** (attesterat) och är låst - rör den inte; lägg bara till Swish-raden.
- **Userscript-konsekvens:** komplettera-logiken får aldrig skriva över en
  befintlig belopp-rad. Den ska, per kollektställe i underlaget, klicka + och fylla
  i en **ny** Swish-rad. Attestering av den nya raden sker sedan manuellt som vanligt.
- **Ej live-verifierat:** övningssystemet saknade F-kollekter, så denna exakta
  sekvens (skapa F → registrera+attestera kontant → lägg till Swish via +) är
  bekräftad via handboken men inte körd live. Bör testas i övning innan bygge (se avsnitt 8).

---

## 2. Riks- och stiftskollekt (R/S) – endast komplettera belopp

**Bekräftat i övningssystemet:** Rikskollekter finns registrerade för hela året (sökning på Kollekttyp=Rikskollekt gav 144 träffar från 2015 och framåt, inkl. framtida datum 2026). Församlingen/pastoratet har **ingen möjlighet** att skapa eller redigera grunduppgifter på ett R/S-tillfälle – fälten under "Grunduppgifter" (Tillfällesdatum, Kollekttyp, Beslutat av=Kyrkostyrelsen/stiftsstyrelse, Kollektändamål, Kollektställe) visas som statisk information, och **Välj...-menyn på ett R/S-tillfälle innehåller bara "Nytt"** (dvs. skapa ett nytt eget tillfälle) – ingen redigerings- eller borttagningsfunktion. Detta bekräftar regeln 1:1: userscriptet får aldrig skapa/redigera R/S, bara komplettera belopp.

### 2.1 Navigering
- **Om tillfället redan syns i "ej registrerade belopp"-listan:** Meny **Kollekt → Kollektbelopp – registrera** → `GET /Collection/CollectionOccasionSearch/CollectionAmountReg` → tabell med kolumnerna Datum/Typ/Beslutat av/Kollektändamål → klick på rad → `GET /Collection/CollectionOccasion/Main?collectionOccasionid={GUID}`.
- **Annars (belopp redan delvis registrerat, eller tillfället ligger utanför 60-dagarsfönstret):** Meny **Sök → Kollekttillfälle** → `GET /Collection/CollectionOccasionSearch/Search` med filter Kollekttyp=Rikskollekt/Stiftskollekt, valfritt Kollektändamål (fritext) och Tillfällesdatum-intervall → resultatlista → klick på rad → samma `CollectionOccasion/Main?collectionOccasionid=...`-vy. Sökformuläret postar som GET-querystring (`?Type=...&Purpose=...&ReadyMarked=...&OccasionDateFrom=...&OccasionDateTo=...`) – **deep-linkbart**, dvs. ett userscript skulle kunna hoppa direkt dit om GUID för Kollekttyp (Rikskollekt/Stiftskollekt) är kända (dessa är statiska system-GUID:er, se fältordlistan).

### 2.2 Kollektbelopp-tabellens struktur (flera kyrkor/församlingar på samma tillfälle)
Detta är kärnan i R/S-flödet. På det kartlagda tillfället (Rikskollekt, "Svenska kyrkan i utlandet", 2026-05-24) visades EN tabell med rader för **båda församlingarna** i pastoratet och **båda kollektställena** i respektive församling:

```
Harbo församling     – Stenkyrkan
                      – Strandkyrkan
Östervåla församling  – Stenkyrkan
                      – Strandkyrkan
```

Samma fält/selektorer som i avsnitt 1.4 (Belopp, Nr kollektbok, Inbetalningsmetod, Kollekt ej upptagen, lägg-till-rad-ikon). Radernas identitet avgörs **enbart av text i cellerna** "Församling"/"Kollektställe" – inga unika id/GUID i DOM.

**Bekräftat live:** Registrerade 123,45 kr (Swish 1) på Harbo/Stenkyrkan och 50 000,00 kr (Swish 1) på Östervåla/Stenkyrkan i samma spardialog – båda sparades i en och samma POST (en klick på **Spara** sparar alla ifyllda rader i tabellen, oavsett församling). Gränsvärdesvarningen ("Ja"/"Nej") triggades korrekt på det för höga beloppet, och efter "Ja" sparades båda raderna (grön toast "Kollektbeloppen sparade", båda raderna fick E-badge).

### 2.3 "Lägg till rad" för flera inbetalningsmetoder på samma kollektställe
Samma mekanik som i 1.4: klick på den gröna +-ikonen i en rads sista kolumn lägger till en ny tom Belopp/Inbetalningsmetod-rad för **samma** Församling/Kollektställe (t.ex. om samma kollekt kom in både kontant och via Swish). Bekräftat live.

### 2.4 Klarmarkering – ej relevant för scriptet
R/S-tillfällen visades redan klarmarkerade ("Klarmarkerad: 2026-02-05 av super") av den nationella nivån. Handboken och UI:t bekräftar att belopp går att registrera/attestera även om ett R/S-tillfälle INTE är klarmarkerat – scriptet ska aldrig försöka klarmarkera ett R/S-tillfälle och har (bekräftat) ingen knapp för det heller på dessa tillfällen.

---

## 3. Insamling/gåva – månadssumma (per verksamhet)

### 3.1 Navigering
Meny **Insamling/gåva → Ny insamling/gåva** → `GET /Contributions/Contribution/Main` (tomt formulär). Efter sparat: `.../Contribution/Main?contributionId={GUID}` – deep-linkbar.
Komplettera/redigera befintlig: Meny **Insamling/gåva → Ej attesterade belopp** (`GET /Contributions/ContributionSearch/UnAttestedContributions`) eller **Sök → Insamling/gåva** (`GET /Contributions/ContributionSearch/Search`).

### 3.2 Fältlista
| Etikett | Typ | Selektor | Möjliga värden | Håven-fält |
|---|---|---|---|---|
| Tillfällesdatum | text, datepicker | `input#CollectedDate[name=CollectedDate]` | `YYYY-MM-DD` | månad (valfritt datum i månaden, t.ex. sista dagen) |
| Mottagare | native select | `select#Receiver[name=Receiver]` | Act Svenska kyrkan / Svenska kyrkan i utlandet / Extern kontakt / **Egna verksamheten** | mottagare (för månadssumma normalt "Egna verksamheten") |
| Typ | native select, **options beror på Mottagare** | `select[name=Type]` (dynamiskt ifylld) | Egna verksamheten→{Gåva, Insamlingsaktivitet}; Act/Utlandet→{Anslag, Insamlingsaktivitet} (INGEN Gåva); Extern kontakt→{Gåva, Insamlingsaktivitet} (INGEN Anslag) | typ = "Gåva" för normal månadssumma |
| Avsändare | native select | `select#CollectedBy[name=CollectedBy]` | Harbo församling / Östervåla församling / Östervåla-Harbo pastorat (beror på aktiv enhet) | församling |
| Belopp (summa, överst) | readonly-liknande, auto-räknad | `input#Amount[name=Amount]` | uppdateras automatiskt = summan av radernas Belopp | – (visningsfält, sätts ej direkt) |
| Typ av aktivitet / Beskrivning | text | `input#ActivityName[name=ActivityName]` | fritext | verksamhet/beskrivning (samma text som i KOB-exporten) |
| Notering för egen uppföljning | textarea | `textarea#Note[name=Note]` | fritext | – |
| Mottagare (endast Extern kontakt) | sök+autocomplete + knapp | eget "Sök mottagare"-fält + knapp "Lägg till" i egen "Mottagare"-sektion, plus utfällbar sektion "Lägg till ny kontakt" | sökning i kontaktregister, eller registrera ny kontakt | extern mottagare |
| Spara | knapp | `button.create_contribution` (Alt+S) | – | – |

Rad-tabell "Belopp / Inbetalningsmetod / Notering för egen uppföljning":
| Kolumn | Selektor | Värden |
|---|---|---|
| Belopp | `input.numeric[name="amount.Amount"]` | komma-decimal |
| Inbetalningsmetod | `select[name="amount.PaymentMethodId"]` | Kontant/Kort/Swish 1/Swish 2 (obligatoriskt) |
| Notering för egen uppföljning | textfält i samma rad | fritext |
| Lägg till rad (+) | grön ikon under tabellen | ny tom rad för ytterligare inbetalningsmetod |
| Ta bort rad | papperskorg per rad | – |

**Bekräftat live:** Belopp-summan högst upp (`#Amount`, "4 550,25 kr") uppdaterades **automatiskt i realtid** när radens Belopp-fält fylldes i – detta bekräftar att fältet är bundet till ett `input`/`keyup`-event, INTE bara `blur`. Ett userscript som sätter värdet med ren `.value =` utan att trigga `input`-event kan riskera att summan inte uppdateras visuellt (även om det troligen inte påverkar vad som faktiskt sparas server-side, eftersom raddata skickas separat) – trigga alltid ett `input`-event för säkerhets skull.

För **Mottagare = Egna verksamheten** (liksom för Kollekt "till egna verksamheten") fylls Mottagare-tabellen nedanför automatiskt med egen enhet, 100 % – inget extra steg krävs.

### 3.3 Spara / status
Vid Spara: grön toast **"Insamling/gåva skapad."**, ingen redirect (AJAX). Efter sparning visas extra knappar: **Attestera** och **Välj...**-meny med **Ny / Kopiera / Ta bort**. "Ta bort" är bara tillgänglig innan attest (bekräftat i menyn).

---

## 4. Särskild post (utbruten ur månadssumma)

Identisk formulärstruktur som avsnitt 3, men:
- **Typ** = `Insamlingsaktivitet` istället för `Gåva` (detta är exakt vad handboken kallar bössinsamling/loppmarknad/café/ljusbärare).
- **Typ av aktivitet/Beskrivning** (`#ActivityName`) sätts till den specifika beskrivningen (t.ex. "Loppis", "Ljus", "Konsert") istället för den generella verksamhetsnamnet.
- Övriga fält (Mottagare, Avsändare, Belopp-rader, Inbetalningsmetod=Swish) fylls i på samma sätt som i avsnitt 3.
- Detta blir alltså en **egen post** i KOB, separat från själva månadssumman för samma verksamhet – exakt som i Håvens modell ("utbruten ur en verksamhets månadssumma").

---

## 5. Insamling/gåva per ändamål (t.ex. Gåvomedelskassan)

Detta är **inte** en särskild KOB-funktion utan samma formulär som avsnitt 3, en post per ändamål:
- **Mottagare**: beror på fondens karaktär – "Egna verksamheten" om medlen stannar i församlingen, "Extern kontakt" om de vidarebefordras till en extern mottagare/fond. (Kunde inte verifieras mot ett konkret exempel för "Gåvomedelskassan" i övningssystemet eftersom inga sådana poster fanns registrerade – se osäkerheter nedan.)
- **Typ** = `Gåva` (normalfallet; `Anslag` endast om mottagaren är Act/Utlandet).
- **Typ av aktivitet/Beskrivning** (`#ActivityName`) = ändamålets namn, en post per ändamål/rad i Håvens underlag.
- Öronmärkning (`EarmarkAllId`-widgeten) finns **endast** på Kollekt-formuläret för "Församlingskollekt nationell organisation", inte på Insamling/gåva. Om Håvens "per ändamål"-poster egentligen ska in som öronmärkta nationella kollekter (t.ex. om "Gåvomedelskassan" är en nationell insamling) måste det hanteras via Kollekt-flödet (avsnitt 1) med rätt Mottagare+Öronmärkning istället för via Insamling/gåva. **Detta måste verifieras manuellt mot ett riktigt exempel ur Håvens underlag innan scriptet byggs för denna posttyp.**

---

## 6. Gemensam fältordlista: Håvens begrepp → KOB-fält → selektor

> **Not (Håven):** Denna tabell var avkapad i inklistringen och är kompletterad ur avsnitt 1–5 ovan (endast selektorer/fält som redan dokumenterats där; inget påhittat). Verifiera mot originalets svans om den finns.

### Kollekt (F och R/S)
| Håven-begrepp | KOB-etikett | Formulär | Selektor | Typ/kommentar |
|---|---|---|---|---|
| Församling (F) | Beslutat av | Kollekttillfälle | `select#DecidedBy[name=DecidedBy]` | vilken församling beslutet gäller |
| Kollektställe | Kollektställe | Kollekttillfälle | `select#CollectionLocationId[name=CollectionLocationId]` | specifik kyrka (GUID) eller "Alla" |
| Gudstjänstdatum | Tillfällesdatum | Kollekttillfälle | `input#OccasionDate[name=OccasionDate]` | `YYYY-MM-DD` (direktinmatning) |
| Ändamål (F) | Kollektändamål | Kollekttillfälle | `input#Purpose[name=Purpose]` | fritext (egna verksamheten/extern kontakt); auto-ifyllt för nationell org |
| Kollekttyp F | Kollekttyp | Kollekttillfälle | `select#Type[name=Type]` | `3`=egna verksamheten, `4`=extern kontakt, `5`=nationell organisation. R/S kan EJ väljas här |
| Mottagare (nationell org, t.ex. Act) | Mottagare | Kollekttillfälle | `select#FNOReceiver[name=FNOReceiver]` | Act Svenska kyrkan / Svenska kyrkan i utlandet |
| Öronmärkning | Öronmärkning | Kollekttillfälle | `select#EarmarkAllId[name=EarmarkAllId]` (jQuery UI-combo) | välj via synligt autocomplete-fält + klick i lista, ej `.value` |
| Belopp (kollekt) | Belopp | Kollektbelopp (radtabell) | `input.amount[name="amount.Amount"]` | matcha rad via Församling/Kollektställe-text; komma-decimal |
| Inbetalningsmetod (kollekt) | Inbetalningsmetod | Kollektbelopp (radtabell) | `select[name="amount.PaymentMethodID"]` | välj "Swish 1" (obs versal `ID`) |
| Nr kollektbok | Nr kollektbok | Kollektbelopp (radtabell) | `input[name="amount.VerificationNumber"]` | valfritt |
| Kollekt ej upptagen | Kollekt ej upptagen | Kollektbelopp (radtabell) | `input.notCollected[name="amount.NotCollected"]` | checkbox |
| Spara tillfälle | Spara / Spara och klarmarkera | Kollekttillfälle | `button.create_occasion` / `button.create_and_readymark_occasion` | Alt+S / Alt+K |
| Spara belopp | Spara | Kollektbelopp | `button.bla` (under tabellen) | Alt+S; sparar alla rader |
| R/S-tillfälle (sök) | Kollekttyp Rikskollekt/Stiftskollekt | Sök kollekttillfälle | `GET /Collection/CollectionOccasionSearch/Search?Type={GUID}&...` | deep-link; ALDRIG skapa, bara komplettera belopp |

### Insamling/gåva (månadssumma, särskild post, per ändamål)
| Håven-begrepp | KOB-etikett | Formulär | Selektor | Typ/kommentar |
|---|---|---|---|---|
| Månad | Tillfällesdatum | Insamling/gåva | `input#CollectedDate[name=CollectedDate]` | valfritt datum i månaden |
| Mottagare | Mottagare | Insamling/gåva | `select#Receiver[name=Receiver]` | Egna verksamheten (normalt) / Act / Utlandet / Extern kontakt |
| Typ | Typ | Insamling/gåva | `select[name=Type]` | "Gåva" (månadssumma/per ändamål), "Insamlingsaktivitet" (särskild post). Options beror på Mottagare |
| Församling | Avsändare | Insamling/gåva | `select#CollectedBy[name=CollectedBy]` | vilken församling |
| Verksamhet/beskrivning | Typ av aktivitet / Beskrivning | Insamling/gåva | `input#ActivityName[name=ActivityName]` | månadssummans verksamhet, särskild posts namn, eller ändamålets namn |
| Belopp (gåva) | Belopp | Insamling/gåva (radtabell) | `input.numeric[name="amount.Amount"]` | trigga `input`-event; summan `#Amount` räknas auto |
| Inbetalningsmetod (gåva) | Inbetalningsmetod | Insamling/gåva (radtabell) | `select[name="amount.PaymentMethodId"]` | "Swish 1" (obs gemen `d` i `Id` – skiljer sig från kollektens `PaymentMethodID`) |
| Spara insamling | Spara | Insamling/gåva | `button.create_contribution` | Alt+S |

---

## 7. Rekommendation för userscript

- **Injicera en knapp i KOB** (t.ex. i headern) som läser Håvens underlag från **urklipp som JSON** (Håven får en "kopiera underlag som JSON"-knapp i registreringskön). En post i JSON: `{posttyp: "F"|"R"|"S"|"insamling"|"sarskild"|"per_andamal", forsamling, kollektstalle, datum, andamal, beskrivning, oronmarkning, belopp, inbetalningsmetod: "Swish 1"}`.
- **Fyll ett formulär i taget**, aldrig batch över flera sidor utan granskning. Sätt fältvärden och **trigga `input`+`change`-event** på varje fält (särskilt belopp och native selects) så jQuery-bindningarna uppdateras.
- **Radmatchning** i belopps-tabeller: hitta rätt `<tr>` via textinnehåll i Församling/Kollektställe-cellerna, sätt sedan `input[name="amount.Amount"]` och `select[name="amount.PaymentMethod*"]` i den raden. För flera inbetalningsmetoder: klicka +-ikonen i radens sista `<td>` och fyll den nya raden.
- **Komplettera-vs-skapa (F):** sök först (deep-link Sök-URL med Type+datum+ändamål); komplettera vid träff, annars skapa. **R/S:** sök alltid, komplettera bara – skapa aldrig.
- **Stanna före Spara** i skarpt läge: markera de ifyllda fälten och låt människan granska och klicka Spara/hantera gränsvärdesvarningen. **Attestering och PIN sker alltid manuellt** - scriptet rör dem aldrig.
- **Gränsvärdesvarning:** upptäck `div.noty_bar.noty_type_warning`; i skarpt läge, låt människan klicka "Ja"/"Nej" (klicka inte automatiskt).

---

## 8. Osäkerheter att verifiera innan bygge

- **Gåvomedelskassan / per-ändamål:** rätt Mottagare (Egna verksamheten vs Extern kontakt) och om det ska vara öronmärkt nationell kollekt i stället för insamling/gåva – verifiera mot ett riktigt exempel.
- **PaymentMethod-GUID:er** för "Swish 1" (och skillnaden mellan kollektens `PaymentMethodID` och insamlingens `PaymentMethodId`) bör läsas ur `<option>`-värdena live, inte hårdkodas.
- **System-GUID för Kollekttyp** (Rikskollekt/Stiftskollekt/Församlingskollekt-undertyper) för deep-link-sökning – läs ur select-optionerna.
- **CSRF:** ingen token syntes i DOM, men verifiera på nätverksnivå (DevTools) innan man litar på att POST utan token fungerar.
- Kartlagt mot **övningssystemet 2025.3.2** – verifiera selektorer mot skarpa systemet (kan skilja i version/URL-prefix `KOB_Utb1` vs skarpt prefix).
- **Komplettera F-kollekt med Swish när kontanten redan är attesterad (avsnitt 1.7):** bekräftat via handboken men ej live-testat (inga F-kollekter i övning). Verifiera i övning: skapa F-tillfälle, registrera+attestera ett kontantbelopp, gå via Sök kollekttillfälle, och bekräfta att gröna + låter dig lägga till en Swish-rad på samma kollektställe utan att röra kontantraden. Fånga selektor/beteende för +-ikonen och den nya radens fält i det läget.
