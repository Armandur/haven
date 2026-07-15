# Kravspecifikation: Verktyg för Swish-kollekt och gåvoavstämning

Härnösands pastorat, Svenska kyrkan
Utkast v0.1 (underlag för vidare arbete, ej färdig)

---

## 1. Syfte och bakgrund

Varje månad tar Rasmus emot Swish-rapporter från ekonomiassistenten. Rapporterna
innehåller kollekter och gåvor som swishats in till pastoratets församlingar och
verksamheter. Beloppen ska registreras i KOB (Svenska kyrkans kollekt- och
betalsystem) och därefter stämmas av mot KOB-exporter för att fånga eventuella
missar.

Idag sker allt i en omfattande Excel-arbetsbok (`Samlade_Inkommande_Swishrapporter.xlsx`)
med Power Query, pivottabeller, utsnitt (slicers) och manuell avstämning. Lösningen
fungerar men är skör, tidskrävande och svår att lita på när något ändras (till exempel
när servicebyrån nyligen bytte rapportformat).

Målet med det här dokumentet är att beskriva arbetet så uttömmande att en ny,
ändamålsbyggd applikation kan byggas i Claude Code. Ingen kod skrivs i det här
dokumentet.

---

## 2. Aktörer och roller

• **Ekonomiassistenten** producerar och skickar månadens Swish-rapport (Excel).
  Använder inte verktyget.
• **Rasmus** och **Carina** delar arbetet mellan sig. I regel tar den ena vissa
  mottagare och den andra övriga, men det är en informell och rörlig uppdelning: är någon
  frånvarande gör den andra allt. Rapportens två flikar ("Act mm", "Musik mm") speglar
  ungefär den vanliga uppdelningen.
• **KOB** är målsystemet där registrering sker. Har (i nuläget) inget öppet API,
  registrering görs manuellt i webbgränssnittet, och underlag hämtas som Excel-exporter.

Verktyget behöver inte härleda eller styra vem som ansvarar för vad. Ansvarsdelningen är
en mänsklig överenskommelse, och alla funktioner ska vara tillgängliga för båda. Rapportens
flikar hanteras bara som en del av filstrukturen vid inläsning, inte som en tilldelning per person.

---

## 3. Nuvarande arbetsflöde (som det ser ut idag)

1. **Mottagning.** Ekonomiassistenten skickar en Swish-rapport per månad. Nya formatet
   har två flikar (en per ansvarsområde), metadatablock överst, delsummerings- och
   totalsummerader, samt belopp med ören.
2. **Normalisering.** Power Query läser en mapp med "formaterade" filer och bygger en
   platt transaktionstabell (bladet `formaterade`, i nuläget ca 12 000 historiska rader).
3. **Ändamålsmatchning.** En uppslagning fyller i kolumnen `Ändamål` för de rader som är
   församlingskollekter, baserat på transaktionsdatum och ändamålskalendern.
4. **Utforskning.** Pivottabeller med utsnitt (`Mottagarnamn`, `Meddelande`, `Source.Name`)
   används för att summera belopp per datum och ändamål.
5. **Registrering i KOB (manuellt):**
   • Kollekter registreras per församling, per gudstjänstdatum, per ändamål och per
     kollekttyp (Församlings-, Riks- eller Stiftskollekt).
   • Gåvor registreras som en insamling per verksamhet och månad.
6. **KOB-export.** Två exporter hämtas: `KOB_ParishCollectionReport` (kollekter) och
   `KOB_Accounts_Contributions` (insamlingar/gåvor). Dessa läses in via Power Query.
7. **Avstämning** (bladet `Kladdblad`, se skärmdump): Swish-summa per mottagare jämförs
   mot vad som registrerats i KOB. En diff-kolumn flaggar avvikelser. Delsummor per
   person (Rasmus/Carina) beräknas.
8. **Statusspårning** (bladet `Registreringar`): en matris med månad × verksamhet/församling
   där det manuellt markeras vad som är klart ("06-komp", initialer, anteckningar).

---

## 4. Problem med nuvarande lösning

• Skört format. Ny rapportstruktur bröt inläsningen och kräver handpåläggning i M-kod.
• Ändamålsmatchningen är svår att verifiera. Endast en delmängd av raderna får ändamål,
  och det går inte lätt att se vad som blev omatchat eller felmatchat.
• Avstämningen är manuell ögonkontroll av diffar mellan pivottabeller.
• Namnnormalisering saknas. Samma församling stavas olika i olika källor.
• Belopp typas som heltal i den gamla frågan, vilket krockar med ören i nya formatet.
• Statusen (vem har gjort vad, vilken månad) lever i en handmatad matris.
• Mycket tyst kunskap sitter i huvudet snarare än i verktyget.

---

## 5. Mål och avgränsningar

### 5.1 Mål
• Läsa in månadens Swish-rapport (nya formatet, flera flikar) robust.
• Klassificera varje transaktion som kollekt eller gåva.
• För kollekter: automatiskt föreslå rätt ändamål och kollekttyp via ändamålskalendern,
  med tydlig markering av det som inte kunde matchas.
• Aggregera till exakt de registreringsenheter KOB behöver.
• Stämma av mot de två KOB-exporterna och tydligt visa diffar.
• Spåra status per månad, verksamhet och församling.
• Visa meddelandefältet så att handläggaren kan upptäcka när en givare avsett något
  annat än det nummer som swishats till.

### 5.2 Icke-mål (åtminstone i första versionen)
• Ingen automatisk registrering i KOB. Verktyget tar fram underlag, en människa registrerar.
  (Kan bli en senare fas om KOB-automation via userscript återanvänds.)
• Ingen molndrift. Verktyget körs lokalt.
• Ingen hantering av andra betalsätt än Swish i MVP (rapporterna är redan Swish-avgränsade).

---

## 6. Domänmodell och begrepp

### 6.1 Två kategorier av mottagare
Varje `Mottagarnamn` i Swish-rapporten hör till en av två kategorier. Mappningen ska vara
konfigurerbar (mottagare kan tillkomma/utgå), men utgångsläget är:

**Kollektmottagare (församlingar) → registreras som kollekt per tillfälle**
• Domkyrkoförsamlingen
• Hemsö Församling
• Häggdångers Församling
• Högsjö Församling
• Stigsjö Församling
• Säbrå Församling
• Viksjö Församling

**Gåvomottagare (verksamheter) → registreras normalt som insamling per månad**
• ACT Svenska Kyrkan
• Barn & Unga
• Diakoni
• Musik
• Gåvomedelskassan

Observera att gåvokontona i praktiken är uppsamlingsnummer. Varje gåvokonto har ett
**registreringssätt**:
• **Månadssumma** (standard för de flesta): den vanliga gåvoströmmen klumpas ihop till en
  summa per verksamhet och månad. Samma konton tar ibland emot andra typer av betalningar
  som ska brytas ut och registreras var för sig (se avsnitt 6.5).
• **Per ändamål:** hela kontots flöde grupperas i stället per ändamål, och varje ändamål
  registreras separat. **Gåvomedelskassan** hanteras så. Ändamålet läses här ur meddelandet
  eller känd kontext, inte ur kollektkalendern (Gåvomedelskassan är inte en församling med
  gudstjänstkollekter).

Allt på ett gåvokonto blir alltså inte per automatik en enda månadssumma, och
registreringssättet ska vara konfigurerbart per konto.

### 6.2 Kollekttyp
Ändamålskalendern kodar typ som en bokstav som mappar till KOB:s kollekttyp:
• `F` = Församlingskollekt
• `R` = Rikskollekt
• `S` = Stiftskollekt

### 6.3 Ändamål och framåtfyllningsregel
Ett kollektändamål beslutas per gudstjänsttillfälle (oftast söndag eller annan helgdag).
En Swish-inbetalning ska tillhöra ändamålet för det **senaste kollekttillfället på eller
före betalningsdatumet**, och det ändamålet gäller framåt tills nästa tillfälle.

Formellt, för en kollekttransaktion till församling P med betalningsdatum D:

    ändamål(P, D) = Ändamål för den rad i P:s ändamålskalender
                    där Datum = max(Datum) för alla rader med Datum <= D

Anmärkningar:
• Ankardatum är **transaktionsdatum** (när givaren betalade), inte bokföringsdatum.
  Exempel: någon swishar måndag efter söndagens gudstjänst; transaktionsdatum är måndag,
  senaste tillfälle <= måndag är söndagen, alltså söndagens ändamål. (Fastställt.)
• Flera tillfällen samma vecka (helgdag på vardag) hanteras automatiskt av max-regeln.
• Transaktioner före årets/periodens första tillfälle blir omatchade och ska flaggas,
  inte tyst släppas.

### 6.4 Namnnormalisering
Samma församling förekommer med olika stavning i olika källor. Verktyget behöver en
kanonisk lista och alias:

| Kanoniskt namn            | Förekommer även som                                  | Kortkod (ändamålsfil) |
|---------------------------|------------------------------------------------------|-----------------------|
| Domkyrkoförsamlingen      | Härnösands domkyrkoförsamling                         | DK                    |
| Hemsö Församling          | Hemsö församling                                      | HE                    |
| Häggdångers Församling    | Häggdångers församling                                | HÄ                    |
| Högsjö Församling         | Högsjö församling                                     | HÖ                    |
| Stigsjö Församling        | Stigsjö församling                                    | ST                    |
| Säbrå Församling          | Säbrå församling                                      | SÄ                    |
| Viksjö Församling         | Viksjö församling                                     | VI                    |

### 6.5 Särskilda poster på gåvokonton
Ett gåvokonto tar emot både vanliga gåvor och ibland andra betalningar som ska
specificeras separat, till exempel intäkter från loppis, ljusförsäljning, semmelförsäljning
eller en särskild aktivitet eller konsert. Sådana poster ska inte ingå i den allmänna
månadssumman utan brytas ut och registreras var för sig i KOB (typiskt som egen
insamlingsaktivitet med egen beskrivning eller öronmärkning).

Månadens flöde på ett gåvokonto delas därför upp i:
• **Allmän gåva** (standardhinken): summeras och registreras som en månadssumma per verksamhet.
• **Särskild post** (noll eller flera): varje sådan post namnges och registreras separat.

Det är handläggaren som avgör uppdelningen. Posterna identifieras på två sätt:
• **Utifrån meddelandet** (t.ex. att meddelandet nämner loppis, ljus eller semlor).
• **Utifrån ett känt datum eller datumintervall** (handläggaren vet att en viss aktivitet
  ägde rum en viss dag eller period, och att inbetalningar då hör till den posten).

Verktyget behöver ingen automatik för att gissa posterna, men det ska gå snabbt att välja
ut transaktioner genom att filtrera på meddelandetext och/eller på datum/datumintervall,
och sedan knyta urvalet till en namngiven särskild post. Historiskt är det just den här
uppdelningen som ger de diffar som synts i avstämningen (till exempel "Act exkl loppis"
mot totalen på Act-kontot).

### 6.6 Hur registrering sker i KOB
Registreringen i KOB följer ett par regler som påverkar både underlaget och avstämningen:

• **Inbetalningsmetod är alltid Swish 1** i pastoratets fall och kan förifyllas.
• **Komplettera eller skapa.** Finns kollekttillfället redan i KOB kompletteras det bara
  med rätt belopp (och inbetalningsmetod). Finns det inte skapar handläggaren tillfället
  efter församling, datum och ändamål.
• **Vem äger tillfället:**
  • **Församlingskollekter (F) och insamlingar/gåvor:** handläggaren skapar tillfället
    själv om det saknas.
  • **Stiftskollekter (S) och rikskollekter (R):** tillfällena registreras i systemet av
    andra (nationellt/regionalt). Handläggaren skapar dem aldrig, utan kompletterar bara
    belopp på befintliga tillfällen.

• **Gruppering per tillfälle för R och S.** Församlingskollekter (F) registreras
  församlingsvis, vilket är enklast att hålla ordning på och är så det görs idag. För
  stifts- (S) och rikskollekter (R) registreras däremot alla församlingars kollekter på
  samma tillfälle (ett gemensamt tillfälle för hela stiftet/riket per ändamål och datum).
  Där ska verktyget gruppera ihop registreringarna: en grupp per (kollekttyp, ändamål,
  datum) med varje församlings belopp under, så att allt kan matas in på en gång medan man
  står på det tillfället i KOB.

Konsekvens för verktyget: i det manuella läget behöver verktyget inte hålla reda på om ett
tillfälle ska kompletteras eller skapas. Handläggaren ser det direkt i KOB och avgör där.
Underlaget behöver bara visa typ (F/R/S) som sammanhang, så att det framgår att R- och
S-poster bara ska kompletteras. Själva komplettera/skapa-logiken blir relevant för verktyget
först vid en eventuell halvautomatisering (fas 3), då den behöver veta att den aldrig ska
försöka skapa R- eller S-tillfällen.

---

## 7. Datakällor och format

### 7.1 Swish-rapport (indata, nytt format)
• Excel med **en eller flera flikar** (t.ex. "Act mm", "Musik mm"). Bladnamn varierar
  och ska inte hårdkodas.
• Metadatablock överst per blad: titel, `Clearingnummer:`, `Kontonummer:`,
  `Swish-nummer:`, datumintervall, samt en sammandragsruta (antal, inkommande, totalt).
• Rubrikrad någonstans efter metadata med kolumnerna:
  `Bokföringsdatum, Transaktionsdatum, Valutadatum, Mottagarnummer, Mottagarnamn,
  Meddelande, Orderreferens, Tid, Belopp`.
• Datarader följer, grupperade per mottagarnummer, med insprängda
  `<nummer> Summa`-rader, tomma skiljerader och en avslutande `Totalsumma`-rad.
  **Alla summeringsrader saknar bokföringsdatum**, vilket är en pålitlig filtergrund.
• Belopp kan ha ören (decimaltal).
• Meddelandefältet är valfri fritext som givaren själv väljer att fylla i. Det används
  bara som en visuell koll för att ibland se om någon avsett något annat än det nummer
  som swishats till. Ingen särskild logik eller tolkning behövs, det räcker att visa det.

### 7.2 Ändamålskalender (indata)
Originalfilen `2026_-_Kollektändamål.xlsx` har **ett blad per församling** (kortkoderna
ovan) med kolumnerna:
`Datum, Tema, Veckodag, Kyrklig helgdag, Typ av kollekt (F/R/S), Ändamål`.

I den konsoliderade arbetsboken finns samma data i bladet `Ändamål 2026` med kolumnerna:
`Församling, Datum, Veckodag, Kyrklig helgdag, Typ, Ändamål, Nyckel` där
`Nyckel = Församling|Datum`.

Verktyget läser **originalets per-blad-struktur** som sanningskälla. Det är den tabell
Rasmus underhåller och uppdaterar år för år (en fil per år, ett blad per församling), och
det är där ändamålen beslutas. Den konsoliderade tabellen i arbetsboken behövs inte som
källa.

### 7.3 KOB-export: kollekter
`KOB_ParishCollectionReport` (.xls). Relevanta kolumner:
`Församling, Tillfällesdatum, Kollekttyp, Kollektändamål, Inbetalningsmetod, Belopp`.
En rad per registrerad kollekt (församling + datum + typ + ändamål).

### 7.4 KOB-export: insamlingar/gåvor
`KOB_Accounts_Contributions` (.xls). Relevanta kolumner:
`Församling, Mottagare, Datum, Insamlingstyp, Typ av aktivitet/Beskrivning,
Öronmärkning, Notering, Inbetalningsmetod, Belopp`.
En rad per registrerad insamling (verksamhet + månad).

---

## 8. Funktionella krav

### 8.1 Import och normalisering
• Läsa in en Swish-rapport med godtyckligt antal flikar.
• Hitta rubrikraden dynamiskt (leta efter `Bokföringsdatum`) per blad.
• Ta bort summerings-, tom- och totalrader (filtrera på saknat bokföringsdatum).
• Läsa ut clearing- och kontonummer ur metadatablocket och koppla till varje rad.
• Behålla vilken flik/vilket ansvarsområde en rad kom ifrån.
• Belopp som decimaltal. Datum och tid korrekt typade (svensk lokal).
• Deduplicera/känna igen om samma rapport läses in två gånger (idempotens).

### 8.2 Klassificering
• Slå varje rad mot mottagarmappningen (avsnitt 6.1) och märk som kollekt eller gåva.
• Okända mottagare flaggas för manuell klassning i stället för att gissas.
• Visa meddelandet intill varje rad så att handläggaren kan upptäcka om en givare
  avsett något annat än numret som swishats till. Ingen automatik, bara synligt fält.

### 8.3 Ändamålsmatchning (endast kollekter)
• Tillämpa framåtfyllningsregeln (avsnitt 6.3) per församling.
• Sätt både `Ändamål` och `Kollekttyp` från den matchande kalenderraden.
• Markera omatchade rader tydligt (t.ex. betalning före första tillfället, eller
  saknat ändamål i kalendern) och lyft dem för åtgärd.
• Låta användaren manuellt överstyra ett föreslaget ändamål, och spara överstyrningen.

### 8.4 Aggregering till registreringsunderlag
• **Kollektunderlag** summeras per (församling, tillfällesdatum, ändamål, kollekttyp), men
  grupperas och presenteras olika beroende på kollekttyp (avsnitt 6.6):
  • **Församlingskollekter (F):** församlingsvis. En post per (församling, datum, ändamål),
    ordnat så att man registrerar en församling i taget.
  • **Riks- och stiftskollekter (R/S):** grupperade per tillfälle. En grupp per
    (kollekttyp, ändamål, datum) med varje församlings belopp under och en tillfällessumma,
    så att alla församlingars belopp kan matas in på samma tillfälle i ett svep.
• **Gåvounderlag** beror på kontots registreringssätt (avsnitt 6.1):
  • **Månadssumma-konton:** summera per (verksamhet, månad), men låt handläggaren bryta ut
    särskilda poster (avsnitt 6.5) först. Kontot ger då en allmän månadssumma på det som är
    kvar plus en rad per särskild post med eget namn/beskrivning.
  • **Per ändamål-konton (t.ex. Gåvomedelskassan):** gruppera månadens transaktioner per
    ändamål (ändamålet läses ur meddelandet eller känd kontext) och ge en rad per ändamål
    att registrera separat.
• Uppdelningen och grupperingen ska gå att göra genom att filtrera transaktioner på
  meddelandetext och/eller datum/datumintervall, markera urvalet och knyta det till en
  namngiven post eller ett ändamål. Det sparas så att avstämningen går ihop (delarna ska
  motsvara totalen på kontot).
• Presentera underlaget som en tydlig läsvy på skärmen, eftersom registreringen i KOB sker
  genom att handläggaren tittar på underlaget och skriver in manuellt (det går fortast).
  Kopiera/klistra-flöde eller filexport är inte nödvändigt i MVP, men kan finnas som tillägg.

### 8.5 Registreringsflöde (arbetskö)
• Presentera registreringsunderlaget som en styrd arbetskö, inte bara en statisk lista, så
  att handläggaren leds igenom posterna en i taget och slipper tappa räkningen.
• För varje post: visa allt som behövs för att registrera i KOB (församling eller
  tillfällesgrupp, datum, ändamål, typ, belopp, Swish 1), låt handläggaren registrera
  manuellt i KOB och sedan **bekräfta** posten, varpå kön går vidare till nästa.
• Ordna kön logiskt: församlingskollekter församlingsvis, riks- och stiftskollekter
  grupperade per tillfälle (avsnitt 8.4), och gåvor per konto.
• Visa fortlöpande hur många poster som är klara och hur många som återstår.
• Det ska gå att hoppa över en post, ångra en bekräftelse och återuppta kön senare utan att
  börja om. En redan bekräftad månad ska inte kunna dubbelregistreras av misstag.

### 8.6 KOB-avstämning
• Läsa in de två KOB-exporterna.
• Normalisera församlings- och mottagarnamn (avsnitt 6.4) innan jämförelse.
• Avstämningen ska göras **per församling och tillfälle**, inte bara per mottagare/kategori:
  • Per kollekttillfälle: Swish-summa per (församling, tillfällesdatum, ändamål) jämförs
    mot KOB per samma nyckel. Detta är den avgörande nivån.
  • Per gåvokonto: kontots total ska motsvara allmän månadssumma plus utbrutna särskilda
    poster.
• Flagga varje avvikelse med belopp och trolig orsak (omatchad rad, ej registrerad,
  dubbelregistrering, namnmissmatch, ej utbruten särskild post). För R- och S-poster
  tolkas ett saknat belopp som "ej kompletterad" snarare än "tillfälle saknas", eftersom
  de tillfällena ägs av andra (avsnitt 6.6).
• Visa totaler, och gärna delsummor per rapportflik så att de kan stämmas mot rapportens
  egna delsummeringar. Ingen koppling till person behövs.

### 8.7 Statusspårning
• Ersätta matrisen `Registreringar`: för varje månad och varje verksamhet/församling
  hålla ett tillstånd, t.ex. `Ej påbörjad → Registrerad i KOB → Avstämd`.
• Visa vad som återstår för innevarande månad, per verksamhet och församling.
• Statusen hänger ihop med arbetskön (avsnitt 8.5): när alla poster för en enhet är
  bekräftade räknas den som registrerad, och efter avstämning som avstämd.

### 8.8 Rapporter/utdata
Den viktigaste utdatan är en tydlig läsvy på skärmen, eftersom registreringen i KOB sker
genom att titta och skriva in manuellt. Vyerna som behövs:
• Registreringsunderlag (kollekt respektive gåva) att läsa av vid inmatning i KOB, med
  församling, datum, ändamål, typ (F/R/S) och belopp, samt inbetalningsmetod förifylld som
  Swish 1. Handläggaren avgör själv i KOB om ett tillfälle ska kompletteras eller skapas;
  någon skapa/komplettera-markering i verktyget behövs inte förrän vid halvautomatisering
  (avsnitt 6.6).
• Avstämningsvy med diffar per församling och tillfälle.
• Lista över omatchade/oklassade rader att åtgärda.
Filexport (Excel/CSV) och utskrift kan finnas som tillägg men är inte nödvändigt i MVP.

---

## 9. Icke-funktionella krav

• **Drift i homelabben.** Verktyget körs i Rasmus homelab och nås över Tailscale från
  arbetsdatorn. Det innebär i praktiken en liten webbtjänst som bara är åtkomlig i det
  privata nätet, inte publikt. Underlaget stannar därmed lokalt och skickas inte till
  tredje part. Ingen särskild personuppgiftslogik behövs kring meddelandefältet.
• **Belopp med ören.** KOB kan registrera ören, så belopp hanteras som decimaltal hela
  vägen utan avrundning.
• **Robusthet mot formatändringar.** Rubrik- och kolumnigenkänning ska vara tolerant.
  Byter servicebyrån igen ska felet vara begripligt, inte tyst fel.
• **Idempotens.** Att köra samma månad två gånger ska inte dubbelräkna.
• **Spårbarhet.** Det ska gå att se varför en rad fick ett visst ändamål (vilken
  kalenderrad som matchade) och historik för överstyrningar.
• **Enkel drift.** Få rörliga delar, tydlig installation, en liten webbtjänst i homelabben.

---

## 10. Föreslagen teknisk arkitektur

Förslaget utgår från Rasmus befintliga mönster (Python, FastAPI, SQLite, drift i homelabben
över Tailscale).

**Rekommendation: en kärnpipeline i Python + en webbvy i homelabben som nås över Tailscale,
med SQLite som tillstånds- och historiklager.** Eftersom registreringen sker genom att läsa
av på skärmen och skriva in i KOB är webbvyn det primära gränssnittet, inte en eftertanke.

• **Kärna (bibliotek):** ren Python som gör import, normalisering, klassning,
  ändamålsmatchning, aggregering och avstämning. Testbar utan gränssnitt. Pandas eller
  polars för tabellbearbetning, openpyxl/xlrd för inläsning.
• **Lagring:** SQLite. Tabeller för transaktioner, ändamålskalender, mottagarmappning,
  särskilda poster, registreringsposter (arbetskön), överstyrningar, KOB-exportrader,
  avstämningsresultat och månadsstatus. Ger idempotens, historik och spårbarhet.
• **Webbvy (FastAPI + enkel HTML):** kan återanvända mönster från tidigare projekt.
  Flöde: läs in rapport → granska klassning/ändamål och åtgärda flaggat → bryt ut
  särskilda poster (filtrera på meddelande/datum) → gå igenom registreringskön post för
  post och bekräfta allt eftersom det matas in i KOB → läs in KOB-export → se avstämning
  per församling och tillfälle → markera status. Åtkomst begränsas till det privata
  Tailscale-nätet.
• **Första steg:** börja med kärnan plus registreringskön för underlaget och en lista över
  omatchade rader. Avstämning, utbrytning av särskilda poster och statusspårning byggs på
  därefter (se faserna nedan).

Motiv: kärnan bär logiken och är enkel att testa; SQLite ger den spårbarhet och
idempotens som Excel saknar; webbvyn i homelabben gör avläsningen inför KOB-inmatning
snabb och håller allt underlag i det privata nätet.

---

## 11. Preliminär datamodell (SQLite)

• `mottagare` (namn, kategori [kollekt/gava], församling/verksamhet,
  registreringssatt [manadssumma/per_andamal, endast för gåva], aktiv)
• `forsamling` (kanoniskt_namn, kortkod, alias[])
• `andamalskalender` (forsamling, datum, veckodag, helgdag, typ [F/R/S], andamal)
• `transaktion` (id, rapportfil, flik/ansvar, bokf_datum, trans_datum, valuta_datum,
  mottagarnamn, meddelande, tid, belopp, orderreferens, clnr, kontonr,
  kategori, andamal, kollekttyp, matchad_kalenderrad, overstyrd [bool],
  sarskild_post_id [null om allmän gåva])
• `sarskild_post` (id, verksamhet, period, namn/beskrivning, oronmarkning, av_vem)
• `registreringspost` (id, period, typ [kollekt_F/kollekt_R/kollekt_S/insamling/sarskild],
  grupp_nyckel [för R/S: kollekttyp+ändamål+datum], forsamling [null för grupperad R/S],
  datum, andamal, belopp, kostatus [att_registrera/registrerad/bekraftad], av_vem, tidpunkt)
  med koppling till de transaktioner som ingår
• `overstyrning` (transaktion_id, gammalt_andamal, nytt_andamal, av_vem, tidpunkt, orsak)
• `kob_kollekt` (forsamling, tillfallesdatum, kollekttyp, andamal, belopp, kalla)
• `kob_insamling` (forsamling, mottagare, datum, typ, beskrivning, belopp, kalla)
• `manadsstatus` (period, enhet [verksamhet/forsamling], tillstand, av_vem, tidpunkt)
• `avstamning` (period, nyckel, swish_summa, kob_summa, diff, orsak, status)

---

## 12. Designbeslut

### 12.1 Fastställt
• **Ansvarsdelning:** verktyget härleder inte ansvar. Uppdelningen mellan Rasmus och Carina
  är informell; är någon frånvarande gör den andra allt. Alla funktioner öppna för båda.
• **Avstämningsnivå:** per församling och tillfälle (den finkorniga jämförelsen), inte bara
  per mottagare/kategori.
• **KOB-registrering:** verktyget tar fram underlag för manuell inmatning nu. Halvautomatisk
  inmatning (t.ex. via återanvänd KOB-userscript) är ett mål på sikt.
• **Historik:** ingen komplett migrering. Vi startar med aprilrapporten 2026 (nytt format).
• **Utdata:** ingen kopiera/klistra behövs. Handläggaren läser av underlaget på skärmen och
  skriver in i KOB manuellt, det går fortast. Webbvyn är därför det primära gränssnittet.
• **Ören:** KOB kan registrera ören, så belopp hanteras som decimaltal utan avrundning.
• **Drift:** körs i homelabben, nås över Tailscale från arbetsdatorn.
• **Datumankare:** transaktionsdatum (transaktionsdag). Fastställt.
• **Gåvomedelskassan:** hanteras som ett gåvokonto men med registreringssätt "per ändamål",
  där ändamålet läses ur meddelandet eller känd kontext (avsnitt 6.1).
• **Ändamålskälla:** originalfilen med ett blad per församling, som Rasmus underhåller och
  uppdaterar år för år. Den konsoliderade tabellen behövs inte som källa.
• **Särskilda poster, identifiering:** görs utifrån meddelandet och/eller ett känt datum
  eller datumintervall. Verktyget stödjer urval via filter på meddelandetext och datum;
  ingen automatisk gissning krävs.
• **Registrering i KOB:** inbetalningsmetod alltid Swish 1. Befintliga tillfällen
  kompletteras med belopp, saknade skapas efter församling, datum och ändamål, men bara
  för F-kollekter och insamlingar. R- och S-tillfällen ägs och skapas av andra och
  kompletteras enbart med belopp (avsnitt 6.6). I det manuella läget behöver verktyget inte
  hantera komplettera/skapa, det gör handläggaren i KOB. Distinktionen blir relevant för
  verktyget först vid halvautomatisering (fas 3).
• **Kontering:** struken. `Blad1` var sidoanteckningar och ingår inte i verktyget.
• **Gruppering av registreringar:** F-kollekter registreras församlingsvis (som idag),
  medan R- och S-kollekter grupperas per tillfälle (kollekttyp, ändamål, datum) med alla
  församlingars belopp under, eftersom de registreras på ett gemensamt tillfälle i KOB.
• **Registreringsflöde:** verktyget ska ha en styrd arbetskö redan i det manuella läget, där
  man går post för post, registrerar i KOB och bekräftar innan man går vidare till nästa,
  med synlig progress.

### 12.2 Kvarstår att bekräfta
• **Exakt fältmappning i KOB:s formulär** för de olika posttyperna (F/R/S-kollekt,
  månadssumma-insamling, per-ändamål-insamling, särskild post). Bekräftas enklast när vi
  ser inmatningsvyn i KOB under bygget, och behövs på allvar först i fas 3 (halvautomatik).

---

## 13. Föreslagen faslös utrullning

Utrullningen sker i homelabben. Aprilrapporten 2026 (nytt format) är första skarpa månaden.

• **Fas 0, kärna + registreringskö:** import + normalisering + klassning +
  ändamålsmatchning + aggregering till registreringsunderlag (församlingsvis för F,
  grupperat per tillfälle för R/S) + lista över omatchade rader, presenterat som en styrd
  arbetskö där man går post för post och bekräftar allt eftersom det matas in i KOB.
  Bevisar kärnlogiken mot aprilrapporten.
• **Fas 1, särskilda poster + avstämning:** utbrytning av särskilda poster (filter på
  meddelande/datum), inläsning av de två KOB-exporterna, namnnormalisering och avstämning
  per församling och tillfälle med tydliga diffar.
• **Fas 2, tillstånd och status:** SQLite för idempotens, historik, överstyrningar och
  beständig kö-status; statusspårning per verksamhet och församling som ersätter matrisen.
• **Fas 3, bekvämlighet:** arkivering av gammalt underlag och halvautomatisk KOB-inmatning
  via återanvänd userscript. Det är först här verktyget behöver skilja på att komplettera
  befintliga tillfällen och att skapa nya, och veta att R- och S-tillfällen aldrig skapas.

---

## 14. Överlämning till Claude Code

När specen är fastställd:
• Detta dokument fungerar som kravunderlag och kan ligga i repo som `SPEC.md`.
• Konventioner (FastAPI-mönster, svensk lokal, svenska commit-meddelanden,
  delegeringsregler) läggs i `CLAUDE.md` enligt Rasmus vanliga uppsättning.
• Rekommenderat att starta med Fas 0 och validera mot aprilrapporten 2026 tillsammans med
  `2026_-_Kollektändamål.xlsx`, med en känd facit-avstämning. `1948_26-06_Uppdelad.xlsx`
  kan användas som ytterligare testfall.

### 14.1 Filer som ska följa med
Redan framtagna (referens och testdata):
• `2026_-_Kollektändamål.xlsx` — ändamålskalender, ett blad per församling. Sanningskälla.
• `1948_26-06_Uppdelad.xlsx` — Swish-rapport juni 2026 i nytt format. Extra testfall.
• `Samlade_Inkommande_Swishrapporter.xlsx` — nuvarande arbetsbok, domänreferens.

Behöver tillhandahållas till Claude Code:
• Aprilrapporten 2026 (Swish, nytt format) — första skarpa månad att validera fas 0 mot.
• KOB-export `ParishCollectionReport` (.xls) för samma månad — själva filen, för att bygga
  import och avstämning av kollekter.
• KOB-export `Accounts_Contributions` (.xls) för samma månad — likaså, för insamlingar/gåvor.
• Gärna en känd facit-avstämning för testmånaden (t.ex. Kladdblad för den månaden).

Att bekräfta (inte filer): mottagarmappningen (mottagare → kollekt/gåva, och vilka
gåvokonton som är "per ändamål") samt församlingsaliasen. Kan fröas ur specen och filerna
men bör stämmas av mot verkligheten en gång.

---

Detta är ett arbetsdokument, men alla designbeslut är nu fastställda (avsnitt 12.1) och
konteringen är struken som sidoanteckning. Specen är därmed redo att tas in i Claude Code.
Det enda som återstår att bekräfta i detalj är exakt hur en post ska registreras i KOB:s
formulär, vilket enklast görs när vi ser inmatningsvyn under bygget.
