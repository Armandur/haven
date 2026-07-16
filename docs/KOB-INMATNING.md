# KOB-INMATNING.md — Teknisk spec för userscript-förifyllnad

<!-- Framtagen med Claude for Chrome enligt docs/kob-inmatning-prompt.md, live mot KOB:s övningssystem. Underlag för Fas 3-userscriptet. -->

> Uppdaterad körning i KOB **övningssystem** (bas-URL: `http://kob-utb.svenskakyrkan.se/KOB_Utb1/Web`, version 2025.3.2).
> Live-verifierad 2026-07-16 mot inloggad enhet **Östervåla-Harbo pastorat** (användare KOBAlla1).
> Facit: KOB-handboken (HTML-referens, PDF-historik senast 14 maj 2025).
> Denna körning fokuserar på det som inte kunde live-verifieras tidigare: **församlingskollekt-flödet (Sök → komplettera via grönt +)**, samt R/S-komplettering och Insamling/gåva-fält.

---

## 0. Teknisk plattform (gäller alla vyer)

- **Serverrenderad ASP.NET MVC.** Formulär postas till samma URL. Inga SPA-router; navigering = riktiga sidladdningar.
- **jQuery + jQuery UI + DataTables** används. Sökresultat och beloppsrutnät är `<table>` med DataTables/tablesorter.
- **Deep-link:** både sökvyn och detalj/komplettera-vyn är deep-linkbara (se §2, §3).
- **Session-timeout:** ~60 min. En noty-dialog "Din inloggning upphör inom kort" med knapp "Fortsätt arbeta" kan dyka upp. Userscriptet bör inte klicka bort den automatiskt utan bara låta användaren se den.
- **Aktiv enhet** väljs i `select#global_unitselect` uppe till höger. Byte laddar om sidan. Userscriptet ska INTE byta enhet automatiskt.
- **Varningar/bekräftelser** ritas med **noty**-biblioteket: `div.noty_bar`, meddelande i `.noty_message`. Knappar i noty-dialog: `#button-0` (primär, t.ex. "Ja") och `#button-1` (t.ex. "Nej").
- **Success-toast** efter spara: grön noty med text (t.ex. "Kollektbeloppen sparade", "Kollekttillfället skapat", "Kollekttillfället klarmarkerat"). Faller bort efter någon sekund.
- **Datumformat:** `ÅÅÅÅ-MM-DD` (t.ex. 2026-07-16). Fälten är `input.datebox.hasDatepicker` (jQuery UI datepicker). Att sätta `.value` fungerade i test, men trigga gärna `change`.
- **Belopp:** decimalkomma, ören tillåts (t.ex. `342,75`, `150,50`). Fält `input.amount.numeric`.


---

## 1. Menyns direktlänkar (klickstig + URL)

| Åtgärd | Meny | URL (relativt /KOB_Utb1/Web) |
|---|---|---|
| Skapa nytt kollekttillfälle | Kollekt → Kollekttillfälle – skapa nytt | `/Collection/CollectionOccasion/Main` |
| Kollekttillfällen – klarmarkera | Kollekt → …klarmarkera | `/Collection/CollectionOccasionSearch/NotReadyMarkedCollectionOccasions` |
| Kollektbelopp – registrera (ej reg. lista) | Kollekt → Kollektbelopp – registrera | `/Collection/CollectionOccasionSearch/CollectionAmountReg` |
| Kollektbelopp – ej attesterade | Kollekt → …ej attesterade | `/Collection/CollectionOccasionSearch/UnAttestedCollectionAmounts` |
| Kollektbelopp – ej betalda | Kollekt → …ej betalda | `/Collection/CollectionOccasionSearch/UnPayedCollectionAmounts` |
| **Sök kollekttillfälle** | Sök → Kollekttillfälle | `/Collection/CollectionOccasionSearch/Search` |
| Kollekttillfälle (detalj/komplettera) | (öppnas från lista) | `/Collection/CollectionOccasion/Main?collectionOccasionid={GUID}` |
| Ny insamling/gåva | Insamling/gåva → Ny insamling/gåva | `/Contributions/Contribution/Main` |
| Sök insamling/gåva | Sök → Insamling/gåva | `/Contributions/ContributionSearch/Search` |
| Insamling/gåva – ej attesterade | Insamling/gåva → Ej attesterade belopp | `/Contributions/ContributionSearch/UnAttestedContributions` |

**Viktig detalj:** Ett öppnat kollekttillfälle har alltid `?collectionOccasionid={GUID}` i URL:en. Userscriptet kan därför deep-linka direkt till ett känt tillfälle och hoppa över sökningen om GUID redan är känt (t.ex. cachat från tidigare körning).


---

## 2. Sök kollekttillfälle — sökformulär, resultatlista, komplettera-flöde (F)

### 2.1 Sökformulär (`form#searchform`)

URL: `/Collection/CollectionOccasionSearch/Search` — **skickas via GET → deep-linkbar querystring.**

| UI-etikett | Fälttyp | Selektor (id=name) | Värden |
|---|---|---|---|
| Kollekttyp | select | `#Type` | `[Alla]`=(tom); `Förskollekt nationell org`=`0f2ebd4e-2981-43b9-ac08-eea25283b402`; **Församlingskollekt**=`cb0b0a3c-706a-4895-b2aa-91253565ec18`; **Stiftskollekt**=`7c73638d-9894-4417-9552-e72862d52afa`; **Rikskollekt**=`8f5709f1-757c-4818-b972-331062377cce` |
| Kollektändamål | text | `#Purpose` | fritext (delsträng) |
| Status | select | `#ReadyMarked` | `[Alla]`=(tom); `Klarmarkerade`=1; `Ej klarmarkerade`=2 |
| Tillfällesdatum från | text/datum | `#OccasionDateFrom` | ÅÅÅÅ-MM-DD |
| Tillfällesdatum till | text/datum | `#OccasionDateTo` | ÅÅÅÅ-MM-DD |
| (Sök) | submit | `#btnSubmit` | |
| (Rensa) | button | `#btnClear` | |
| (Nytt kollekttillfälle) | button | `#btnCreateNew` | → skapa-vyn |

**Deep-link exempel (verifierad):**
`/Collection/CollectionOccasionSearch/Search?Type=cb0b0a3c-706a-4895-b2aa-91253565ec18&Purpose=&ReadyMarked=&OccasionDateFrom=2026-07-16&OccasionDateTo=2026-07-16`
→ formuläret förifylls OCH sökningen körs automatiskt.

### 2.2 ⚠️ KRITISK FALLGROP: DataTables-filtret ("Filtrera:")

Ovanför resultattabellen finns en klientsidig DataTables-sökruta ("Filtrera:"). **Den förifylls ibland med ett gammalt datum (i test: `2026-07-12`)** som filtrerar bort giltiga serverträffar. Symptom: sidfoten säger *"Inga kollekttillfällen hittade (filtrerad från 1 totalt)"* — dvs servern hittade 1 rad men klientfiltret döljer den.

**Userscriptet MÅSTE tömma detta fält innan resultatet läses.** Fältet är den enda `input` utan id ovanför tabellen (`.dataTables_filter input`, alt. sök den `input` vars `value` ser ut som ett datum). Töm via:
```js
var f = document.querySelector('#collectionOccasionTable_filter input, .dataTables_filter input');
if (f) { f.value=''; f.dispatchEvent(new Event('keyup',{bubbles:true})); }
```

### 2.3 Resultatlista (`table#collectionOccasionTable`, class `tablesorter dataTable`)

Kolumner: **Datum | Typ | Beslutat av | Kollektändamål**. Sidfot: "Visar X till Y av Z". Paginering: Första/Föregående/Nästa/Sista; "Visa N rader".

- **Rader:** `#collectionOccasionTable tbody tr`. Radceller: `td[0]`=Datum, `td[1]`=Typ, `td[2]`=Beslutat av, `td[3]`=Kollektändamål.
- **Ingen href/onclick på raden** — klick hanteras av en delegerad jQuery-`click`-handler på `#collectionOccasionTable`. Öppna en rad genom att **klicka på raden** (t.ex. på en td). Detta navigerar till `/Collection/CollectionOccasion/Main?collectionOccasionid={GUID}`.
- Flera träffar på samma datum/ändamål KAN förekomma (handboken: "samma ändamål samma dag" tillåts). Identifiera med kombination Datum+Typ+Beslutat av+Kollektändamål; är det fortfarande tvetydigt → **fråga användaren** (gissa aldrig).

### 2.4 Beslutslogik som UI:t stödjer (verifierad)

1. Sök på Kollekttyp + Kollektändamål + tillfällesdatum (F: exakt gudstjänstdatum).
2. **Töm Filtrera-rutan.** Läs sidfoten/radantalet.
3. **1 träff → komplettera** (klicka raden, se §2.5). **0 träffar → skapa nytt** (§3). **>1 träff / tvetydigt → fråga användaren.**
4. För **R/S: alltid komplettera** befintligt tillfälle — userscriptet får ALDRIG skapa R/S (se §6).

### 2.5 Komplettera-flöde: lägg till Swish-rad via grönt + (verifierad, F och R/S)

Efter att tillfället öppnats visas panelen **Kollektbelopp** = `table#collectionAmountsDetailsTable`.

Radlayout (per kollektställe): `td0`=kryssruta(markera för attest), `td1`=Församling, `td2`=statusikon (E=ej attesterad röd / A=attesterad / M=makulerad / B=betald), `td3`=Kollektställe, `td4`=Kollekt ej upptagen (checkbox), `td5`=Belopp, `td6`=Nr kollektbok, `td7`=Inbetalningsmetod (select), `td8`=grönt + (`img.RowExpander`) och papperskorg.

- **Grönt +** = `img.RowExpander` (src `.../images/details_open.png`, `title="Lägg till ett nytt belopp för detta kollektställe"`). Klick lägger till en **ny tom rad direkt under** kollektstället, med **samma kollektställe**, tomt Belopp/Nr kollektbok och Inbetalningsmetod=`[Välj]`. Den befintliga (kontant/attesterade) raden lämnas **orörd**. Efter tillägg får ursprungsradens expander klassen `hiddenrowexpander`.
- **Fält i den nya raden** (⚠️ **id:n är duplicerade per rad** — `#amount_Amount`, `#amount_PaymentMethodID` osv. återkommer). **Scoping per `<tr>` är obligatoriskt.** Namn: `amount.Amount` (Belopp), `amount.VerificationNumber` (Nr kollektbok), `amount.PaymentMethodID` (Inbetalningsmetod), `amount.NotCollected` (Kollekt ej upptagen).
- **Inbetalningsmetod-select** (`select[name="amount.PaymentMethodID"]`): `[Välj]`=(tom); `Kontant`=`6b81b990-92e8-ef11-8392-0025b531002e`; `Kort`=`d5abe2f8-dab7-ef11-8141-0025b501007a`; **`Swish 1`=`d6abe2f8-dab7-ef11-8141-0025b501007a`**; **`Swish 2`=`d7abe2f8-dab7-ef11-8141-0025b501007a`**. ⚠️ Två Swish-alternativ finns — bestäm regel (default `Swish 1`) och gör konfigurerbart.
- **Spara:** `Spara`-knappen under rutnätet (button, kortkommando Alt+S).
- **Efter spara:** grön toast "Kollektbeloppen sparade"; nya raden persisteras med statusikon **E** och papperskorg. Ingen sidnavigering.

**Verifierat testfall (F):** Öppnade nyskapat F-tillfälle via Sök. Rad Harbo/Stenkyrkan hade redan 500,00/Kontant (status E). Grönt + → ny Stenkyrkan-rad. Fyllde 342,75 + valde Swish 1. Spara → båda raderna kvar, kontantraden orörd.
**Verifierat testfall (R):** Rikskollekt "Svenska kyrkans unga". Rad Harbo/Stenkyrkan hade 875,00/Swish 1. Grönt + → ny rad, fyllde 150,50 + Swish 2, Spara → gränsvärdesvarning (se §5) → Ja → sparat, ursprungsraden orörd.


---

## 3. Skapa nytt kollekttillfälle (F) — endast när sökningen är tom

URL: `/Collection/CollectionOccasion/Main`. Form: `#occasion_wrapper_form`.

⚠️ **Församlingsanvändare kan bara skapa Församlingskollekt** (`#Type` innehåller BARA F-undertyper). R/S går inte att skapa här → bekräftar regeln i §6.

### 3.1 Grunduppgifter

| UI-etikett | Fälttyp | Selektor | Värden / not |
|---|---|---|---|
| Tillfällesdatum | text/datum | `#OccasionDate` (name=OccasionDate) | ÅÅÅÅ-MM-DD |
| Kollekttyp | select | `#Type` | `[Välj]`=(tom); `Församlingskollekt nationell organisation`=5; `Församlingskollekt (till egna verksamheten)`=3; `Församlingskollekt (till extern kontakt)`=4 |
| Beslutat av | select | `#DecidedBy` | tom tills Type valts; sedan församlingarna (t.ex. `Harbo församling`=`585306b2-…`, `Östervåla församling`=`2a03bd5e-…`) |
| Kollektändamål | text (autocomplete på 10 senaste) | `#Purpose` | fritext. (För typ 5 nationell org: styrs av mottagare/öronmärkning, ej fritext.) |
| Kollektställe | select | `#CollectionLocationId` | `Alla`=(tom); populeras **dynamiskt efter Beslutat av** med enhetens kollektställen (t.ex. `Stenkyrkan`=`8eed7d51-…`, `Strandkyrkan`=`c5be94e7-…`) |
| Notering för egen uppföljning | textarea | `#Note` | valfritt |

### 3.2 Dynamiskt beteende (verifierat)

- När **Kollekttyp = egna verksamheten (3)** väljs: panelen **Mottagare** dyker upp automatiskt förifylld med egna enheten (t.ex. "Östervåla-Harbo pastorat", OrgNr 2520031994, 100 %). Ingen mottagarhantering behövs.
- När **Beslutat av** väljs: `#CollectionLocationId` fylls med den enhetens kollektställen.
- För **extern kontakt (4)** / **nationell org (5)** väljs mottagare i Mottagare-panelen (extern kontakt ur kontaktregister; nationell org = Act Svenska kyrkan / Svenska kyrkan i utlandet + ev. öronmärkning). Flera mottagare → procentfördelning måste summera till 100.

### 3.3 Klarmarkeringskrav + spara

- **Klarmarkering kräver:** mottagare valda **och** procentfördelning = 100 %. Uppfyllt automatiskt för egna verksamheten (100 %).
- Knappar (uppe till höger): `Spara` (button, aktiveras när minimifält satta) och `Spara och klarmarkera` (button, kortkommando **Alt+K**, titel "Spara och klarmarkera kollekttillfället").
- **Efter Spara och klarmarkera (verifierat):** två gröna toaster "Kollekttillfället skapat" + "Kollekttillfället klarmarkerat"; URL får `?collectionOccasionid={GUID}`; fältet **Klarmarkerad** visar "ÅÅÅÅ-MM-DD av {användare}"; panelen **Kollektbelopp** blir tillgänglig (en rad per kollektställe, redo för belopp).

> **Regel:** F-normalfallet är komplettera (§2). Skapa (§3) används bara när sökningen ger **0 träffar**.


---

## 4. Registrera belopp (F) & R/S — belopp-rutnätet i detalj

Samma rutnät (`table#collectionAmountsDetailsTable`) används både när man registrerar första beloppet och när man kompletterar. Statusradioknapparna överst (Alla / Ej attesterade / Attesterade / Makulerade / Betalda / Inbetalningsmetod / Noteringar / Datum) styr vilka kolumner/rader som visas; **"Alla" + "Inbetalningsmetod" ska vara på vid registrering/komplettering.**

### 4.1 Registrera ett förstabelopp (verifierat, kontant)
- I panelen finns en rad per kollektställe (Församling + Kollektställe fylls i av systemet).
- Fyll `amount.Amount`, välj `amount.PaymentMethodID`, ev. `amount.VerificationNumber`. `Spara`.
- "Kollekt ej upptagen" = `amount.NotCollected` (checkbox) per rad; kryssrutan i kolumnrubriken markerar alla rader utan belopp.

### 4.2 Lägg till ytterligare belopp / kollektställe
- **Ytterligare belopp på samma kollektställe** (t.ex. Swish utöver kontant): grönt + på raden (§2.5).
- **Flera kollektställen / flera kyrkors belopp på samma tillfälle** (R/S och "flera kyrkor samma ändamål"): rutnätet listar redan alla enhetens församlingar × kollektställen som separata rader (verifierat på Rikskollekt: Harbo/Stenkyrkan, Harbo/Strandkyrkan, Östervåla/Stenkyrkan, Östervåla/Strandkyrkan). Fyll belopp på respektive rad. Ingen "lägg till kollektställe"-knapp behövs — raderna finns.

### 4.3 Attestering (opt-in assisterat läge — se designbeslut nedan)
- Öppnas via `/…/UnAttestedCollectionAmounts` → klicka tillfället → panelen visar kryssrutekolumn + knapp **"Attestera valda rader"**.
- Klick på "Attestera valda rader" → **PIN-modal** `div#reveal-pin-container.reveal-modal`: rubrik "Ange din 4-siffriga PIN-kod", input `#PinCode` (type=password), submit-knapp "Klar", avbryt `#abortButton`.
- **Designbeslut (Håven):** attestering är **inte förbjuden** för scriptet, men den är **opt-in** - användaren måste aktivt slå på ett attest-läge (default AV). När det är på:
  - Scriptet markerar raderna och klickar "Attestera valda rader", fyller i PIN-modalen.
  - **Sessionens PIN kan cachas i skriptet (endast i minnet, aldrig till disk/localStorage)** så användaren slipper skriva den varje gång. Den enda bekräftelse användaren behöver göra är att **trycka Enter** (dvs människan har alltid sista handen på varje attest).
  - Riskuppvägning: **attestering är reversibel via makulera** (se §4.4), så ett felattesterat belopp kan ångras. Det gör opt-in-assistansen försvarbar.
  - ⚠️ **Säkerhetsnot:** att cacha en PIN i ett userscript är känsligt. Håll den bara i en modul-lokal variabel i sessionen, rensa vid sidladdning/utloggning, och exponera aldrig den i DOM/konsol/URL. Attest-läget ska vara tydligt av-som-default och kräva ett aktivt påslag per session.
- Kräver att kontot har attesträtt (registreras i Arkiv → Administrera användare). I övningskontot saknades attesträtt, så PIN-flödet kunde inte köras end-to-end (se §11).

### 4.4 Makulera (ångra en attestering)
- Ett redan attesterat belopp kan **makuleras** (status M) om det blev fel. Handbok: *"Har man attesterat ... men upptäcker att det var fel så går det att makulera."* Nås via Sök kollekttillfälle → öppna tillfället → markera beloppsraden → makulera-funktion (kräver också PIN på samma sätt som attest).
- Detta är den ångra-väg som gör opt-in-attestering (§4.3) rimlig. Userscriptet behöver inte automatisera makulering (den görs vid behov manuellt), men flödet dokumenteras här för fullständighet. **Ej live-verifierat denna körning** (kontot saknade attesträtt) - selektorer för makulera-knapp/dialog bör fångas i ett kompletterande pass av någon med attesträtt.


---

## 5. Klarmarkering, spara & varningar

- **Spara-knappar:** kollekttillfälle: `Spara` / `Spara och klarmarkera` (Alt+S / Alt+K). Belopp-rutnät: `Spara` (Alt+S). Insamling/gåva: knapp med class `create_contribution`.
- **Klarmarkeringskrav** syns via fältet **Klarmarkerad** (tomt = ej klarmarkerad; datum+användare = klarmarkerad). Belopp kan bara registreras när tillfället är klarmarkerat (gäller F; R/S kan ta emot belopp även ej klarmarkerat).
- **Gränsvärdesvarning (verifierad):** vid spara av belopp utanför enhetens gränsvärden visas en **noty-varning**:
  - Container: `div.noty_bar.noty_type_warning`, text i `.noty_message`: *"Formuläret innehåller N varning(ar) för belopp utanför gränsvärdena. Se markering vid registrerade belopp. Vill du spara ändå?"*
  - Knappar: **`#button-0`** = "Ja" (class `btn-primary`), **`#button-1`** = "Nej" (class `btn-danger`).
  - Raden med avvikande belopp markeras (gul indikator till vänster).
  - Systemet **tillåter** spara ändå → klick "Ja" sparar. (I test gav 150,50 varning; 342,75 och 500,00 gav ingen.)
  - **Rekommendation:** userscriptet ska INTE auto-klicka "Ja" i skarpt läge — det ska stanna och låta människan avgöra. (Kan valfritt detektera och lyfta fram varningen.)
- **Lyckad spara** signaleras med grön noty-toast (`.noty_bar` grön), t.ex. "Kollektbeloppen sparade". Ingen redirect; rutnätet uppdateras in-place.


---

## 6. R/S-kollekter — status i övningssystemet & komplettera-flöde

**R/S-tillfällen FINNS i övningssystemet** (verifierat via Sök/Ej attesterade):
- Rikskollekt 2026-07-12 — Beslutat av: Kyrkostyrelsen — Kollektändamål: **Svenska kyrkans unga**.
- Rikskollekt 2026-05-24 — Kyrkostyrelsen — **Svenska kyrkan i utlandet**.

Komplettera-flödet på ett R/S-tillfälle är **identiskt** med F-komplettering (§2.5/§4): öppna tillfället (via Sök eller lista), rutnätet visar alla församlingar × kollektställen, fyll belopp per rad och/eller grönt + för extra rad (t.ex. Swish utöver kontant), Spara.

**HÅRD REGEL (skarp drift):** userscriptet får **ALDRIG skapa** R- eller S-tillfällen (ägs av nationell nivå). Att skapa är dessutom UI-blockerat för församling (`#Type` i skapa-vyn saknar R/S). Userscriptet ska **bara komplettera belopp** på befintliga R/S. Att registrera belopp fungerar även om R/S-tillfället inte är klarmarkerat.

För R/S matas "alla församlingars belopp" in under **ett** tillfälle (en rad per församling/kollektställe), precis som handbokens "flera kyrkor på samma tillfälle".


---

## 7. Insamling/gåva — create-form (månadssumma, särskild post, per-ändamål)

URL: `/Contributions/Contribution/Main`. Form: `#contribution_wrapper_form` (postar till `/Contributions/Contribution/MainDetails`).

### 7.1 Grunduppgifter

| UI-etikett | Fälttyp | Selektor | Värden / not |
|---|---|---|---|
| Tillfällesdatum | text/datum | `#CollectedDate` | ÅÅÅÅ-MM-DD |
| Mottagare | select | `#Receiver` | `[Välj]`=(tom); `Act Svenska kyrkan`=`373a5d3e-346e-408c-b9b7-8655c60cf42e`; `Svenska kyrkan i utlandet`=`12719863-4da1-4e9d-aee8-f78a2758b3bf`; `Extern kontakt`=`3c66d49b-e82c-e411-8c98-e4115b10bbc6`; `Egna verksamheten`=`4066d49b-e82c-e411-8c98-e4115b10bbc6` |
| Typ | select | `#TypeKey` | tom tills Mottagare valts; se 7.2 |
| Avsändare | select | `#CollectedBy` | `[Välj]`=(tom); församlingar + pastorat (t.ex. Harbo, Östervåla, Östervåla-Harbo pastorat) |
| Belopp (rubrik-total) | (visning) | — | summeras från beloppsrader |
| Typ av aktivitet / Beskrivning | text | (fält i grunduppgifter) | verksamhet/beskrivning — **detta motsvarar fältet i KOB-exporten Håven läser** |
| Notering för egen uppföljning | textarea | `#Note` | valfritt |

### 7.2 Typ-alternativ per mottagare (verifierat live)

| Mottagare | `#TypeKey`-alternativ |
|---|---|
| Act Svenska kyrkan | Anslag=1, Insamlingsaktivitet=3 *(ingen Gåva — stämmer med handboken)* |
| Svenska kyrkan i utlandet | (som Act: Anslag=1, Insamlingsaktivitet=3) |
| Extern kontakt | **Gåva=5**, Insamlingsaktivitet=3 |
| Egna verksamheten | Anslag=1, Insamlingsaktivitet=3 |

⚠️ **Avvikelse mot handbok/kontext:** handboken säger att för *Egna verksamheten* finns INTE "Anslag" som val — men live-UI:t visar Anslag=1. Dessutom saknar Egna verksamheten "Gåva" i live-UI (kontexten antog Gåva där). **Verifiera med KOB-support / manuellt vilken Typ era egna-verksamhetsposter ska ha.** (Sannolikt Insamlingsaktivitet=3 för loppis/ljus/café/konsert = era "särskilda poster".)

### 7.3 Öronmärkning (endast Act / utlandet)

- När Mottagare = Act eller utlandet visas panel **Öronmärkning** = wrapper `div#earmarkAll_wrapper` med en **jQuery UI autocomplete-input** (`input.ui-autocomplete-input`, display-text "Ingen öronmärkning").
- Alternativen är förladdade; att skriva filtrerar en `ul.ui-autocomplete` (id `ui-id-N`) med `li.ui-menu-item > a` (t.ex. "Försörjning och klimaträttvisa", "P122 · Förebyggande klimatarbete i Etiopien").
- ⚠️ **Ramverksbundet:** `.value` räcker INTE. Userscriptet måste sätta input-värdet, trigga autocomplete (`keydown/input`), och **klicka rätt `li a`** i förslagslistan. Öronmärkning gäller Act (insamlingstema/projekt) och utlandet (utlandsförsamling).

### 7.4 Beloppsrutnät

- Tabell `table.contributionAmountsTable`. Kolumner: **Belopp | Inbetalningsmetod | Notering för egen uppföljning** + papperskorg.
- Fält (⚠️ id:n duplicerade per rad → scope per `<tr>`): `amount.Amount` (Belopp), `amount.PaymentMethodId` (**OBS: `Id`, inte `ID` som i kollekt**), `amount.Note` (Notering).
- Inbetalningsmetod-select: samma GUID:er som kollekt (`Kontant`, `Kort`, `Swish 1`=`d6abe2f8-…`, `Swish 2`=`d7abe2f8-…`). Obligatoriskt fält.
- **Lägg till rad** (flera inbetalningsmetoder): grönt + = `img.RowExpander` (title "Lägg till ett nytt belopp") längst ner till höger i rutnätet.
- **Spara:** knapp class `create_contribution`. Attestering separat med PIN (som §4.3) — userscriptet rör det inte.

### 7.5 Håvens posttyper → Insamling/gåva-inställning

| Håv-posttyp | Mottagare | Typ | Beskrivning-fält | Öronmärkning |
|---|---|---|---|---|
| Insamling/gåva – månadssumma (Act) | Act Svenska kyrkan | Insamlingsaktivitet=3 (verifiera) | verksamhet (t.ex. "Act") | ev. insamlingstema |
| Insamling/gåva – månadssumma (Diakoni/Musik = egna) | Egna verksamheten | Insamlingsaktivitet=3 (verifiera) | verksamhet | — |
| Särskild post (loppis/ljus/konsert) | Egna verksamheten | Insamlingsaktivitet=3 | beskrivning (loppis/ljus/konsert) | — |
| Per ändamål (t.ex. Gåvomedelskassan) | Egna verksamheten / Extern kontakt (verifiera) | Gåva=5 (om extern) el. Insamlingsaktivitet=3 | ändamål | — |

> Inbetalningsmetod = **Swish** i alla Håv-fall. En rad per metod; belopp kan ha ören.


---

## 8. Gemensam fältordlista: Håv-begrepp → KOB-fält → selektor

| Håv-underlag | KOB-vy | UI-etikett | Selektor | Not |
|---|---|---|---|---|
| församling/kollektställe (F) | Kollekttillfälle skapa | Beslutat av / Kollektställe | `#DecidedBy` / `#CollectionLocationId` | kollektställe-lista beror på Beslutat av |
| kollektställe (belopp) | Belopp-rutnät | (rad) Kollektställe | `tr` i `#collectionAmountsDetailsTable` | matcha på td-text (Församling+Kollektställe) |
| gudstjänstdatum | skapa / sök | Tillfällesdatum | `#OccasionDate` / `#OccasionDateFrom`+`#OccasionDateTo` | ÅÅÅÅ-MM-DD |
| ändamål | skapa / sök | Kollektändamål | `#Purpose` | fritext / delsträng-sök |
| kollekttyp F/R/S | sök | Kollekttyp | `#Type` | GUID-mappning i §2.1 |
| belopp | belopp-rutnät | Belopp | `[name="amount.Amount"]` (scope per rad) | decimalkomma, ören |
| inbetalningsmetod = Swish | belopp-rutnät | Inbetalningsmetod | `[name="amount.PaymentMethodID"]` (kollekt) / `[name="amount.PaymentMethodId"]` (insamling) | Swish 1=`d6abe2f8…`, Swish 2=`d7abe2f8…` |
| beskrivning/verksamhet | insamling | Typ av aktivitet / Beskrivning | text i grunduppgifter | motsvarar KOB-exportfält |
| öronmärkning | insamling | Öronmärkning | `#earmarkAll_wrapper input.ui-autocomplete-input` | jQuery UI autocomplete, klicka li |
| mottagare (insamling) | insamling | Mottagare | `#Receiver` | GUID:er i §7.1 |
| avsändare/församling (insamling) | insamling | Avsändare | `#CollectedBy` | |

**Kollektställen (Östervåla-Harbo, verifierade GUID):** Stenkyrkan=`8eed7d51-7654-4188-8fd1-75a3f95e3430`, Strandkyrkan=`c5be94e7-72fc-4c16-be31-dbf732dae813`. Församlingar: Harbo=`585306b2-6f0a-4f6c-a18e-8529de4aad49`, Östervåla=`2a03bd5e-3e28-40a9-8189-b830af27613a`. (GUID:er kan skilja per enhet/miljö — läs alltid options dynamiskt, hårdkoda inte.)


---

## 9. Rekommendation för userscript

### 9.1 Arkitektur
- **@match** `http://kob-utb.svenskakyrkan.se/*` (övning) och motsvarande skarp KOB-URL. **Allt lokalt** — ingen KOB-data lämnar webbläsaren.
- Underlag matas in som **JSON via urklipp** eller en liten textarea i en injicerad panel. Injicera en flytande knapp/panel ("Håven: förifyll") i KOB. Ingen extern tjänst.
- Underlagsschema (förslag): `{ typ:"F|R|S|insamling", datum, kollekttyp, andamal, forsamling, kollektstalle, belopp, inbetalningsmetod:"Swish 1", beskrivning?, oronmarkning?, mottagare? }`.

### 9.2 Komplettera-vs-skapa (F)
1. Deep-linka Sök: `Search?Type={F-GUID}&Purpose={ändamål}&OccasionDateFrom={datum}&OccasionDateTo={datum}`.
2. **Töm DataTables-Filtrera-rutan** (§2.2), läs radantal.
3. 1 rad → öppna (klicka raden) → komplettera. 0 rader → gå till skapa-vyn (`#btnCreateNew` / `/CollectionOccasion/Main`), förifyll grunduppgifter, **stanna för manuell Spara/klarmarkera**. >1 → visa träfflista och **be användaren välja**.

### 9.3 Fylla belopp / grönt +
- Hitta rätt `<tr>` i `#collectionAmountsDetailsTable` genom att matcha td-texten för Församling+Kollektställe.
- Har raden redan ett belopp (kontant, ev. status E/A): klicka radens `img.RowExpander` (grönt +), vänta tills ny `<tr>` dyker upp direkt under, och fyll DEN raden. **Rör aldrig den befintliga raden.**
- Sätt `amount.Amount` (skriv värdet, trigga `input`/`change`), välj Swish i `amount.PaymentMethodID`/`Id` (sätt `.value` till GUID + `change`). Standard-selects fungerar med `.value`+`change` (verifierat).
- **Öronmärkning:** använd autocomplete-simulering (skriv + klicka `li a`), inte `.value`.

### 9.4 R/S
- Sök/öppna befintligt R/S-tillfälle, fyll belopp per rad + grönt + för Swish-rad. **Aldrig skapa.** Om sökningen ger 0 R/S-träffar → **fråga användaren / avbryt**, skapa inte.

### 9.5 Där scriptet MÅSTE stanna för manuell granskning
1. **Före varje Spara** — människan trycker Spara själv (ingen tyst autospar).
2. **Gränsvärdesvarning (noty)** — visa/lyft fram, klicka inte "Ja" automatiskt.
3. **Attestering / PIN** — default AV. I opt-in-läge (§4.3) får scriptet klicka
   "Attestera valda rader" och fylla sessionens cachade PIN, men **människan
   bekräftar varje attest med Enter** (aldrig helt tyst). Reversibelt via makulera (§4.4).
4. **>1 sökträff eller tvetydig matchning** — fråga, gissa aldrig.
5. **Skapa R/S** — förbjudet.
6. **Byte av aktiv enhet** — gör inte automatiskt.

### 9.6 Robusthetsnoter
- Id:n i beloppsrutnäten är **inte unika** → alltid rad-scoping.
- Kollekt använder `PaymentMethodID`, insamling `PaymentMethodId` — hantera båda.
- DataTables-filtret kan dölja serverträffar → töm alltid.
- Läs select-options **dynamiskt** (GUID:er kan variera per enhet/miljö); matcha hellre på synlig text ("Swish 1", "Församlingskollekt") än hårdkodad GUID.
- Dynamiska paneler (Mottagare, Öronmärkning, Kollektställe-lista) renderas efter val → vänta in dem (MutationObserver) innan fältfyllnad.
- Sessionstimeout ~60 min; långa körningar kan avbrytas av inloggningsdialog.


---

## 10. Krav på det FÄRDIGA userscriptet (skarp drift)

1. Skapar **aldrig** R- eller S-tillfällen — bara kompletterar befintliga (ägs av nationell nivå).
2. Attesterar bara i **opt-in-läge** som användaren aktivt slår på (default av). I det läget cachas sessionens PIN endast i minnet och **människan bekräftar varje attest med Enter** — aldrig tyst massattest. Utan opt-in fyller scriptet bara i belopp och stannar. Attestering är reversibel via makulera, vilket motiverar assistansen; PIN får aldrig sparas till disk/localStorage eller exponeras.
3. Stannar **alltid** för manuell granskning; en människa trycker Spara. Ingen tyst autoinmatning i skarpt läge.
4. Allt sker lokalt i webbläsaren; **ingen KOB-data skickas till extern tjänst.**

---

## 11. Osäkerheter / ej fullständigt verifierat

- **Insamling/gåva Typ-alternativ per mottagare** avviker från handbok (Egna verksamheten visar Anslag i live men handboken säger nej; Gåva saknas för Egna i live). **Bekräfta korrekt Typ för era egna-verksamhets-/Act-poster manuellt.**
- **Öronmärkningens** exakta datakälla (förladdad lista vs ev. AJAX) bekräftades som klientfiltrerad lista i test, men verifiera för utlandsförsamlingar (kan vara stor lista).
- **Attesteringens** effekt på "ej registrerade belopp"-listan verifierades inte hela vägen (PIN-steget avbröts medvetet). Logiken "attesterat tillfälle syns ej i registrera-listan → nås via Sök" följer handboken.
- **Flera träffar samma datum/ändamål:** möjligt enligt handbok; sågs inte i test (övningssystemet hade få F). Userscriptet ska hantera det via användarfråga.
- GUID:er (kollektställen, mottagare, betalmetoder) gäller denna enhet/miljö; **läs dynamiskt i skarp miljö.**
- Datum-/decimalformat verifierat i testinmatning (ÅÅÅÅ-MM-DD; komma-decimal). Datepickerns exakta change-event-krav testades inte uttömmande — trigga `change` för säkerhets skull.

---

## 12. Testdata skapad i övningssystemet under denna körning

- **Nytt F-tillfälle:** 2026-07-16, Församlingskollekt (egna verksamheten), Beslutat av Harbo församling, ändamål "Testkollekt userscript-kartläggning". GUID `5d94ca8e-1081-f111-9db2-005056a5bf31`. Klarmarkerat. Belopp: Harbo/Stenkyrkan 500,00 Kontant (E) + 342,75 Swish 1 (E).
- **Rikskollekt (befintlig):** "Svenska kyrkans unga" (`c447113e-6afb-f011-9daa-005056a5bf31`), lade till Harbo/Stenkyrkan 150,50 Swish 2 (E) utöver befintlig 875,00 Swish 1.
- (Endast övningsdata — påverkar ingen skarp bokföring.)
