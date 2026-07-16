# KOB-INMATNING.md
**Underlag för Tampermonkey/Violentmonkey-userscript – halvautomatisk registrering av Håvens Swish-underlag i KOB**
Baserat på: KOB-handboken (HTML-referens, uppdaterad enligt egen historik 14 maj 2025) + live-verifiering i KOB:s övningssystem (`kob-utb.svenskakyrkan.se`, KOB-version 2025.3.2) den 16 juli 2026, inloggad som Lars Martinsson (KOBAlla1), enhet Östervåla-Harbo pastorat.

> **Viktigt om denna körning:** Fokus har legat på församlingskollekt-flödet (Sök kollekttillfälle, komplettera, gröna +) samt Riks-/Stiftskollekt-komplettering, eftersom detta inte kunde live-verifieras i en tidigare kartläggning. Insamling/gåva-formuläret har verifierats översiktligt live denna gång. Allt nedan är antingen (a) **live-verifierat** i övningssystemet idag, eller (b) markerat **[handbok, ej live-verifierat denna körning]**.

> **Not (Håven) om provenance:** Under kartläggningen i övningssystemet (a) sattes en PIN-kod (`1234`) på övningskontot KOBAlla1 när systemet krävde det för attest-test, och (b) skapades testdata (nytt F-tillfälle 2026-07-19 "Diakoni - test Håven", samt tillagda belopp på ett F- och ett R-tillfälle). Attesteringen misslyckades ("Användaren saknar attesträtt") - kontot är registrerare men inte attesterare i miljön - så scenariot "attesterad kontant → komplettera Swish" kunde INTE köras end-to-end (kontantraden förblev i status E). Se öppen punkt i 1.3.
>
> **Not (Håven) om denna fil:** Den live-verifierade inklistringen kapades mitt i avsnitt 2.4. Avsnitt 3 och framåt (Insamling/gåva, fältordlista, rekommendation, öppna punkter) är därför tills vidare **den föregående passets version** (märkt som bilaga längst ned) och ersätts när svansen på den nya körningen klistras in.

---

## 0. Allmänt om KOB:s tekniska ramverk

- Klassisk server-renderad ASP.NET MVC-app (URL-mönster `/KOB_Utb1/Web/<Kontroller>/<Action>`), **inga iframes** påträffade i kollekt-/insamlingsflödet.
- jQuery + jQuery UI genomgående. Dropdown-fält är i huvudsak **native `<select>`** (kan sättas med `.value` + `change`-event) – **utom** sök-fält för mottagare/öronmärkning som är **jQuery UI Autocomplete** (`class="ui-autocomplete-input"`) och kräver riktig tangentbordsinmatning (skriv text → vänta på förslagslista → klicka/piltangent+Enter på ett `<li>` i `.ui-autocomplete`-menyn). Att bara sätta `.value` fyller INTE i den dolda id-referensen som krävs för att spara.
- Tabeller i sök-/inkorgslistor är **jQuery DataTables** (`class="... dataTable"`). Varje rad har ofta ett **dolt datafält** (t.ex. tillfällets GUID) som inte visas som kolumn men finns i DataTables interna data-array – hämtas med `$('#tabellId').DataTable().row(rowEl).data()` (sista elementet i arrayen). Rader saknar `href`/`onclick`-attribut i DOM:en; klick hanteras av en delegated jQuery-handler på tabellen.
- Bekräftelse-/varningsdialoger (gränsvärdesvarning, PIN-dialog, felmeddelanden) renderas med **noty.js** – knappar får dynamiska id:n (`button-0`, `button-1` osv.) men ligger i en `.noty_buttons`-container och kan identifieras på synlig text ("Ja"/"Nej"/"OK").
- **Ingen `__RequestVerificationToken`** hittades i formulären vi undersökte – detta talar för att scriptet ska agera genom att fylla i fält och klicka riktiga knappar (som en människa), INTE genom egna AJAX/fetch-anrop, vilket också är i linje med kravet att en människa ska granska och trycka Spara.
- Belopp: decimalkomma (`1500,75`), autoformateras vid visning med mellanslag som tusentalsavgränsare (`1 500,75`). Fältet accepterar ören direkt vid inmatning.
- Datum: fritextfält med jQuery UI-datepicker-ikon; `ÅÅÅÅ-MM-DD` fungerar utmärkt vid direkt typing (handboken nämner även `ÅÅMMDD` som kortkommando-genväg).
- Automatisk utloggning: enligt handboken 60 minuter av inaktivitet [handbok]. En session-timeout-dialog ("Fortsätt arbeta" / "Till inloggningssidan", id:n `#continue`/`#home`) finns färdigrenderad dold på varje sida.
- **Gränsvärdesvarning** (live-verifierad flera gånger): vid Spara av ett kollektbelopp utanför församlingens gränsvärde visas dels en inline-varning i tabellraden ("Kollektbeloppet är högre än det angivna gränsvärdet på 500,00"), dels en noty-modal: *"Formuläret innehåller 1 varning(ar) för belopp utanför gränsvärdena. Se markering vid registrerade belopp. Vill du spara ändå?"* med knappar **Ja**/**Nej**. Scriptet måste kunna identifiera och klicka **Ja** (eller lämna kvar dialogen synlig för användaren att bekräfta manuellt – rekommenderas, se avsnitt "Rekommendation för userscript").

---

## 1. Församlingskollekt (F) — huvudflödet i denna körning

### 1.1 Navigering
| Vy | URL | Metod |
|---|---|---|
| Skapa nytt kollekttillfälle | `/KOB_Utb1/Web/Collection/CollectionOccasion/Main` | GET (tomt formulär) |
| Öppna befintligt tillfälle | `/KOB_Utb1/Web/Collection/CollectionOccasion/Main?collectionOccasionid=<GUID>` | **Deep-linkbart** – live-verifierat: navigerar direkt till rätt tillfälle utan extra klick. |
| Sök kollekttillfälle | `/KOB_Utb1/Web/Collection/CollectionOccasionSearch/Search` | GET, **deep-linkbart via querystring** (se 1.2) |
| Registrera kollektbelopp (inkorg) | `/KOB_Utb1/Web/Collection/CollectionOccasionSearch/CollectionAmountReg` | Lista över tillfällen med ej registrerade belopp (idag + 60 dgr bakåt) |
| Kollekttillfällen – klarmarkera | `/KOB_Utb1/Web/Collection/CollectionOccasionSearch/NotReadyMarkedCollectionOccasions` | Lista över ej klarmarkerade tillfällen |
| Kollektbelopp – ej attesterade | `/KOB_Utb1/Web/Collection/CollectionOccasionSearch/UnAttestedCollectionAmounts` | |

Menyväg: **Kollekt → Kollekttillfälle – skapa nytt / Kollektbelopp – registrera** samt **Sök → Kollekttillfälle**.

### 1.2 Sök kollekttillfälle — sökformulär (live-verifierat i detalj)

URL: `GET /KOB_Utb1/Web/Collection/CollectionOccasionSearch/Search`

Formuläret är **fullt deep-linkbart via querystring**, men **auto-kör inte sökningen** – querystring-parametrar förifyller bara fälten; ett klick på `#btnSubmit` krävs fortfarande (bekräftat: navigering till `?Type=<guid>` prefyllde dropdownen men visade ingen resultatlista förrän Sök klickades).

| Etikett | Fälttyp | Selector | Värden / beteende |
|---|---|---|---|
| Kollekttyp | `<select>` | `#Type` (name=`Type`) | `""`=[Alla], `0f2ebd4e-2981-43b9-ac08-eea25283b402`=Församlingskollekt nationell org, `cb0b0a3c-706a-4895-b2aa-91253565ec18`=Församlingskollekt, `7c73638d-9894-4417-9552-e72862d52afa`=Stiftskollekt, `8f5709f1-757c-4818-b972-331062377cce`=Rikskollekt |
| Kollektändamål | text | `#Purpose` (name=`Purpose`) | Fritext, "innehåller"-sökning (ej live-verifierat exakt matchningsalgoritm) |
| Status | `<select>` | `#ReadyMarked` (name=`ReadyMarked`) | `""`=[Alla], `1`=Klarmarkerade, `2`=Ej klarmarkerade |
| Tillfällesdatum från/till | text+datepicker | `#OccasionDateFrom`, `#OccasionDateTo` (name samma) | Format `ÅÅÅÅ-MM-DD` |
| Sök-knapp | `<input type=submit>` | `#btnSubmit` (value="Sök") | Kör den faktiska GET/AJAX-sökningen |
| Rensa-knapp | `<input type=button>` | `#btnClear` | Nollställer formuläret |
| Nytt kollekttillfälle-knapp | `<input type=button>` | `#btnCreateNew` | Går till skapa-nytt-formuläret (samma som menyn) |

**Deep-link-exempel (live-verifierat):**
`.../CollectionOccasionSearch/Search?Type=cb0b0a3c-706a-4895-b2aa-91253565ec18&Purpose=&ReadyMarked=&OccasionDateFrom=&OccasionDateTo=`

**Resultatlista** (tabell `#collectionOccasionTable`, DataTables):
- Kolumner: **Datum, Typ, Beslutat av, Kollektändamål** (endast dessa fyra syns).
- Ett **dolt 5:e datafält per rad = tillfällets GUID** (`collectionOccasionId`), hämtningsbart via `$('#collectionOccasionTable').DataTable().row(idx).data()[4]`. Detta är den enda robusta vägen att få tag i ID:t programmatiskt utan att klicka.
- Klick på raden (delegerad handler, ingen `href`/`onclick` i DOM) navigerar till `.../CollectionOccasion/Main?collectionOccasionid=<GUID>`.
- Extra klientfilter: `Filtrera:`-textfält ovanför tabellen filtrerar redan hämtade rader lokalt (inte en ny sökning mot servern) – nyttigt för att i en stor lista (t.ex. 144 Rikskollekt-poster) snabbt hitta rätt datum utan omsökning.
- Paginering: "Visa 25/50/… rader", "Första/Föregående/[sidnr]/Nästa/Sista".
- **Flera träffar samma datum/ändamål kan förekomma** – live bekräftat att Rikskollekt-sökningen (144 träffar från 2015 och framåt) fungerar med denna lista; F-sökningen gav exakt 1 träff i vårt testfall.

**Beslutslogik för scriptet (bekräftad i UI:t):**
- **0 träffar** → inget kollekttillfälle finns; föreslå att skapa nytt (endast för F – **aldrig** för R/S, se 2.4).
- **1 träff** → öppna direkt (klicka raden eller navigera till dess GUID) → komplettera-flöde.
- **≥2 träffar** → **fråga användaren** vilket tillfälle som avses (t.ex. visa datum+ändamål+beslutat av för varje träff) – gissa aldrig.

### 1.3 Komplettera-flöde från en träff (live-verifierat, inkl. "grön +" utan att röra kontantraden)

Öppnad detaljvy: `/Collection/CollectionOccasion/Main?collectionOccasionid=<GUID>`, tre hopfällbara paneler: **Grunduppgifter**, **Mottagare**, **Kollektbelopp**.

**Kollektbelopp-tabellen** (en rad per kollektställe × redan registrerat belopp):

| Kolumn | Fälttyp | Selector |
|---|---|---|
| Församling | text (läsvärde) | – |
| Status-badge (E/A/M/B) | – | Bokstavskod: **E**=Ej attesterade, **A**=Attesterade, **M**=Makulerade, **B**=Betalda |
| Kollektställe | text (läsvärde) | – |
| Kollekt ej upptagen | checkbox | per rad |
| Belopp | text | inuti raden, ett `<input type=text>` |
| Nr kollektbok | text | frivilligt referensnummer |
| Inbetalningsmetod | `<select>` | Options **live-verifierade**: `6b81b990-92e8-ef11-8392-0025b531002e`=Kontant, `d5abe2f8-dab7-ef11-8141-0025b501007a`=Kort, `d6abe2f8-dab7-ef11-8141-0025b501007a`=Swish 1, `d7abe2f8-dab7-ef11-8141-0025b501007a`=Swish 2 |
| **Lägg till rad (grön +)** | `<img>` | `img.RowExpander[title="Lägg till ett nytt belopp för detta kollektställe"]` |
| **Ta bort rad (papperskorg)** | `<div>` | `div.trashcan[title="Ta bort detta kollektbelopp"]` – syns bara på rader som redan har ett sparat belopp |
| Spara (för hela beloppsformuläret) | `<button>` | text "Spara", klass `button slight gron` (ej unikt id – identifiera via närmaste `<button>` med den texten inom Kollektbelopp-panelen) |

**Live-testat scenario ("komplettera med Swish via grön + utan att röra kontantraden"):**
1. Ett kollektställe (Strandkyrkan) hade inget belopp → fyllde i 500,00 kr, Kontant → Spara → bekräftade gränsvärdesvarning ("Ja") → toast **"Kollektbeloppen sparade"**.
2. Försökte attestera → **misslyckades** ("Användaren saknar attesträtt") – kontantraden förblev i status **E** (ej attesterad) genom hela testet, se öppen punkt i avsnitt 6.
3. Gick via **Sök kollekttillfälle** (Kollekttyp=Församlingskollekt) → 1 träff → öppnade tillfället igen.
4. Klickade grönt + **på just Strandkyrkan-radens ikon** → en ny tom rad för **samma kollektställe** dök upp direkt under, med tomt Belopp och `[Välj]` i Inbetalningsmetod.
5. Fyllde i 300,25 kr, valde Swish 1 → Spara → gränsvärdesvarning → Ja → **"Kollektbeloppen sparade"**.
6. **Verifierat**: den ursprungliga kontantraden (500,00 / Kontant) var oförändrad; den nya Swish-raden (300,25 / Swish 1) tillkom som en separat rad på samma kollektställe. Ingen data i kontantraden skrevs över.

Detta bekräftar exakt handbokens beskrivning: *"Lägg till ytterligare belopp: Om man vill lägga till ett belopp där det redan finns ett registrerat, makulerat, attesterat eller utbetalt belopp klickar man på gröna pluset till höger på raden."*

> **Öppen punkt:** Jag kunde inte verifiera beteendet när kontantraden verkligen har status **A** (attesterad) eftersom mitt testkonto saknar attesträtt i övningssystemet. Handboken säger uttryckligen att grön-plus-mekaniken fungerar oavsett status (registrerat/makulerat/attesterat/utbetalt), men den exakta visuella/DOM-skillnaden för en attesterad rad (t.ex. om beloppsfältet blir read-only) är **inte live-bekräftad**. Rekommendera att en människa med attesträtt kompletterar detta test innan scriptet driftsätts skarpt.

### 1.4 Skapa nytt F-tillfälle (endast när sökningen ger 0 träffar) — fullt live-verifierat end-to-end

URL: `GET /Collection/CollectionOccasion/Main` (tomt formulär, ID-fält `#ID` är hidden/tomt).

**Grunduppgifter-fält:**

| Etikett | Fälttyp | Selector | Möjliga värden / beteende |
|---|---|---|---|
| Tillfällesdatum | text+datepicker | `#OccasionDate` (name samma) | `ÅÅÅÅ-MM-DD` |
| Kollekttyp | `<select>` | `#Type` (name samma) | `3`=Församlingskollekt (till egna verksamheten), `4`=Församlingskollekt (till extern kontakt), `5`=Församlingskollekt nationell organisation. **Endast dessa tre** finns i skapa-nytt-formuläret – Riks- och Stiftskollekt kan **inte** väljas här, vilket bekräftar att församlingen aldrig kan skapa R/S. |
| Beslutat av | `<select>` | `#DecidedBy` (name samma) | Lista över församlingarna i det aktiva pastoratet (t.ex. "Harbo församling", "Östervåla församling") |
| Kollektändamål | text (autocomplete-liknande, men fritext) | `#Purpose` (name samma) | Fritext. Vid typ "nationell organisation" blir detta istället en **read-only label** som fylls automatiskt av vald Mottagare/Öronmärkning (kan inte skrivas manuellt – bekräftat live) |
| Kollektställe | `<select>` | `#CollectionLocationId` (name samma) | `[Alla]` eller specifikt kollektställe (t.ex. "Stenkyrkan", "Strandkyrkan") – lista beror på vilken församling som valts i Beslutat av |
| Notering för egen uppföljning | textarea | `#Note` (name samma) | Fritext, enbart lokal uppföljning |
| Spara | `<button>` | klass `.create_occasion` | Sparar utan klarmarkering |
| Spara och klarmarkera | `<button>` | klass `.create_and_readymark_occasion` | Sparar + klarmarkerar i ett steg (kräver Mottagare valda + 100 %) |

**Mottagare-sektionen beror på Kollekttyp (alla tre live-testade idag):**

- **Till egna verksamheten** (`Type=3`): Mottagare fylls **automatiskt** av systemet med egen ekonomisk enhet (t.ex. "Östervåla-Harbo pastorat", 100 %) – bekräftat live, ingen manuell inmatning möjlig/nödvändig.
- **Till extern kontakt** (`Type=4`): Ett sökfält `#input_search_mottagare` (`class="search_mottagare ui-autocomplete-input"`, **jQuery UI Autocomplete – kräver riktig tangentbordsinmatning**) + knapp `#collectionoccasion_contacts_add` ("Lägg till", inaktiv tills en kontakt är vald ur förslagslistan). Ett hopfällbart "Lägg till ny kontakt"-formulär finns också om mottagaren inte redan finns i kontaktregistret (fält: `#Name`, `#COAddress`, `#Address`, `#Zip`, `#City`, `#Country`, `#URL`, `#Note`, `#ForeignContact` m.fl. – ej djupdykt då detta inte behövs för Håvens Swish-flöde).
- **Nationell organisation** (`Type=5`): Mottagare blir ett enkelt `<select>` (id ej fångat separat men hittad via `find`, options "Act Svenska kyrkan"/"Svenska kyrkan i utlandet"). Vid val visas ett extra fält **Öronmärkning** – en jQuery UI Autocomplete utan `id`/`name` (troligen kopplad till ett dolt companion-fält för valt id) med hjälptext-ikon bredvid (info-knapp `title`/tooltip som "översätter" ord till giltiga val, enligt handbok). Kollektändamål-fältet blir automatiskt = vald mottagare/öronmärkning (read-only).

**Live-genomfört helt scenario (dokumenterat steg för steg):**
1. Tillfällesdatum `2026-07-19`, Kollekttyp = "Församlingskollekt (till egna verksamheten)" → Mottagare auto-ifylld (Östervåla-Harbo pastorat, 100 %).
2. Beslutat av = "Östervåla församling" → Kollektställe-listan uppdaterades till att visa "Stenkyrkan"/"Strandkyrkan" för den församlingen.
3. Kollektändamål = fritext "Diakoni - test Håven", Kollektställe = "Stenkyrkan" (specifikt, ej "Alla"), Notering ifylld.
4. Klick **Spara och klarmarkera** → toasts **"Kollekttillfället skapat."** och **"Kollekttillfället klarmarkerat."** i följd → sidan laddade om med `?collectionOccasionid=<nytt GUID>` och visade automatiskt Kollektbelopp-panelen med en rad (Stenkyrkan, tom).
5. Fyllde Belopp `1500,75`, Inbetalningsmetod = Swish 1 → Spara → gränsvärdesvarning (beloppet var högre än gränsvärdet 500,00 för denna kombination) → Ja → **"Kollektbeloppen sparade."**

Detta täcker fullständigt kravet "skapa → välj mottagare/ändamål/kollektställe → klarmarkera → registrera belopp med Swish".

### 1.5 "Välj…"-menyn på ett öppnat F-tillfälle (live-verifierat)
Knapp `#`-lös, textinnehåll "Välj…" högst upp till höger. På vårt egenskapade F-tillfälle innehöll dropdownen: **Nytt**, **Avklarmarkera**, **Kopiera**. (Bokföringsunderlag syns först när något är attesterat, enligt handbok – ej synligt här eftersom inget var attesterat.)

---

## 2. Riks- och Stiftskollekt (R/S)

### 2.1 Live-fynd: R-tillfällen finns rikligt, S saknas helt
- Sökning Kollekttyp=Rikskollekt gav **144 träffar**, från 2015-01-18 till minst 2026, återkommande ändamål: "Svenska kyrkan i utlandet", "Act Svenska kyrkan", "Svenska kyrkans unga", "Evangeliska Fosterlandsstiftelsen". Alla "Beslutat av: Kyrkostyrelsen".
- Sökning Kollekttyp=Stiftskollekt gav **0 träffar** i övningssystemet. **Bekräftat: Stiftskollekt saknas i övningsmiljön.** Komplettera-flödet för S kunde därför inte live-testas på riktig data, men eftersom UI:t för R och S delar samma formulär/vy-struktur (samma sök-typ-lista, samma detaljvy-layout) förväntas S bete sig identiskt med R när/om ett S-tillfälle finns.

### 2.2 Struktur på ett R-tillfälle (live-verifierat: 2026-07-12, "Svenska kyrkans unga")
- **Grunduppgifter**: Beslutat av = "Kyrkostyrelsen", Klarmarkerad = redan satt (i vårt exempel `2026-02-05 av super` – dvs klarmarkerad av ett nationellt systemkonto långt innan vår registrering), Kollektställe = "Alla".
- **Mottagare-panelen var tom** (inga rader) för Rikskollekt – till skillnad från F, där mottagare/procent visas explicit. Öronmärkning/mottagare för R/S tycks hanteras helt nationellt och exponeras inte som redigerbara fält lokalt.
- **Kollektbelopp-panelen visar EN rad per kombination av församling × kollektställe för HELA pastoratet**, grupperat: t.ex. "Harbo församling / Stenkyrkan", "/ Strandkyrkan", "Östervåla församling / Stenkyrkan", "/ Strandkyrkan" — exakt så som handboken beskriver för "flera kyrkors belopp på samma tillfälle" / R-S-inmatning: ett tillfälle, alla församlingars belopp under.

### 2.3 Komplettera-belopp-flödet på ett befintligt R-tillfälle — live-verifierat
1. Sök kollekttillfälle → Kollekttyp = Rikskollekt → 144 träffar → använde det inbyggda **Filtrera**-fältet (klientside) för att hitta `2026-07-12` → öppnade raden "Svenska kyrkans unga".
2. Fyllde i Belopp `875,00` på raden "Harbo församling / Stenkyrkan", Inbetalningsmetod = Swish 1.
3. Spara → samma gränsvärdesvarning (500,00) → Ja → **"Kollektbeloppen sparade."**
4. Detta fungerade **trots att tillfället klarmarkerades av ett nationellt konto** och utan att vi rörde klarmarkeringsstatus – exakt i linje med handbokens uppgift: *"Det går att registrera och attestera belopp även om en riks- eller stiftskollekt inte är klarmarkerad."*

### 2.4 "Välj…"-menyn på ett R-tillfälle (live-verifierat, viktig skillnad mot F)
Endast **ett** alternativ: **Nytt** (dvs genväg till skapa-nytt-formuläret för egna F-tillfällen). **Ingen Avklarmarkera, ingen Kopiera** var tillgänglig – till skillnad från vårt egna F-tillfälle som hade båda. Detta bekräftar tekniskt (inte bara via handbokstext) att en pastorats-/församlingsanvändare **inte har någon redigeringsrätt** över R/S-tillfällets grunduppgifter – endast rätt att lägga till belopp på befintliga rader.

> **[INKLISTRINGEN KAPADES HÄR]** - den nya körningens svans (resten av 2.4 samt avsnitt 3 Insamling/gåva, fältordlista, rekommendation och öppna punkter) kom inte med. Sista ofullständiga meningen löd: *"→ Krav för userscriptet (bekräftat i UI:t): skapa-nytt-formuläret för Kollekttillfälle exponerar överhuvudtaget inte Rikskollekt/Stiftskollekt som valbara typer. Scriptet kan alltså aldrig av misstag skapa ett R/S-tillfälle via detta formulär ... Scriptet bör ändå explicit blockera/varna om R/S..."*
>
> Avsnitten nedan är **BILAGA från föregående (mindre detaljerade) pass** och ersätts när svansen klistras in. GUID:er och DataTables-detaljer i den nya körningen ovan gäller framför bilagan vid konflikt.

---

<!-- ================= BILAGA: FÖREGÅENDE PASS (ersätts av nya körningens svans) ================= -->

</content>
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
- **Komplettera-vs-skapa (F):** normalfallet är komplettera (vi jobbar månaden
  efter, tillfället finns oftast redan). Sök alltid först (deep-link Sök-URL med
  Type+datum+ändamål): **1 träff** → komplettera (lägg till Swish-rad via +);
  **0 träffar** → skapa nytt; **flera/tvetydigt** → fråga användaren vilket
  tillfälle (eller om nytt ska skapas), gissa aldrig. **R/S:** sök alltid,
  komplettera bara – skapa aldrig.
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
