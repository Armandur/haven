# Backlog Export

## [P1][done] [haven] Userscriptet lyckas inte välja Inbetalningsmetod till Swish1

- ID: `01KY1QE7MKWASF55CESEBV9F24`
- Type: bug
- Actor: human:rasmus

---

## [P1][done] [haven] I sök kollekttillfälle finns fyra kollekttyper, inte tre

Församlingskollekt
Förskollekt nationell org (detta när det är kollekt till Act Svenska kyrkan eller till Svenska kyrkan i utlandet (SKUT)
Stiftskollekt
Rikskollekt

En bearbetning på ett tillfälle med kollekt till Act gör en sökning på fel kollekttyp och hittar således inte kollekten.


- ID: `01KY1QC35T2Z2SE5XW4DM5R0AR`
- Type: bug
- Actor: human:rasmus

---

## [P2][done] [haven] Filtrera KOB-rader utanför rapportens period ur avstämningens radjämförelse

## Context
Avstämningen jämför alla KOB-rader oavsett den valda rapportens period. Med en annan månads export listas KOB-tillfällen utanför rapportintervallet som "finns i KOB men ej i Swish (kontant, annat datum/ändamål?)" (22 sådana rader i maj-rapport/juni-export-fallet), och gåvosidan summerar KOB-belopp helt utan datumfilter så kontototalerna förorenas tyst. Bannern från TASK-1517 varnar för intervallglappet men radnivån vilseleder.

## Acceptance criteria
- [ ] avstam_kollekt tar rapportens Datumintervall; KOB-rader med tillfällesdatum utanför intervallet ingår varken i radjämförelsen eller i KOB-totalen. I stället redovisas antal och summa samlat (t.ex. fält utanfor_period_antal/utanfor_period_summa på KollektAvstamning).
- [ ] avstam_gava filtrerar insamlingsraderna till rapportens intervall före summering, med samma slags samlade redovisning.
- [ ] KOB-rader UTAN datum behandlas som idag (kan inte periodbestämmas - ingår i jämförelsen).
- [ ] Utan rapportintervall (None) är beteendet exakt som idag.
- [ ] Rader INOM perioden påverkas inte - kontant på samma tillfälle ska fortsatt synas som diff.
- [ ] avstamning.html visar notisen när antal > 0, under både kollekt- och gåvosektionen: i stil med "N KOB-rader (X kr) ligger utanför rapportens period och visas inte - annan månads export?" (hv-meta eller hv-badge varning, konsekvent med befintlig stil).
- [ ] Facittestet oförändrat grönt; nya tester för filtreringen (utanför/inom/utan datum/utan intervall).

## Implementation hints
- Signaturer: avstam_kollekt(transaktioner, kob_rader, rapport_intervall=None) och avstam_gava(underlag, kob_rader, rapport_intervall=None). kor_avstamning i app/services/avstamning_service.py räknar redan rapport_intervall - skicka in det.
- Datumintervall.innehaller finns redan i reconcile.py.
- Notisen i app/templates/avstamning.html nära intervallbannern per sektion.

## Verification
- `uv run --offline --with pytest --with httpx pytest tests/test_avstamning_intervall.py tests/test_maj2026.py`
- Manuellt: /avstamning (maj-rapport + juni-exporter i data/) visar inte längre 2026-05-31..06-28-raderna som diffar, utan summanotisen; intervallbannern står kvar.

- ID: `01M140B3EA6C7D6DFWHKPH8W04`
- Type: improvement
- Actor: ai:claude-fable-5

---

## [P2][done] [haven] Synliggör dold sidledsscroll i breda tabeller på mobil

## Context
Breda tabeller (Historik i Justeringar, församlingstabellen i Underlag, tabellerna i Status och Konfig) scrollar i en dold overflow-x-container - på mobil ser den viktigaste kolumnen ut att saknas helt eftersom inget indikerar att det går att dra i sidled. (UI/UX-fynd P2.)

## Acceptance criteria
- [ ] Breda tabeller får en synlig scroll-affordance på smala skärmar (t.ex. kantskugga/gradient när innehåll döljs, eller kortlayout under brytpunkt) - välj EN mekanism och tillämpa den konsekvent på alla fyra vyerna (justeringar, underlag, status, konfig).
- [ ] Underlagsvyn länkar till arbetskön för samma fil (korsnavigering, UI/UX-fyndet om saknad länk).
- [ ] Ingen sid-overflow vid 390px på någon av vyerna.
- [ ] Desktop 1280px opåverkad.

## Implementation hints
- tokens.css:67-69 är grundregeln (figure overflow-x auto). CSS-only-lösning föredras (scroll-skugga med background-attachment local är etablerat mönster i ren CSS).
- Berörda templates: justeringar.html (historiktabellen), underlag.html:8-15, status.html:38-53, konfig.html:11-32.

## Verification
- Browser: shot av alla fyra vyer vid 390px (skuggan/affordancen syns) och 1280px (opåverkad), ljust och mörkt läge på minst en vy.
- scrollWidth == 390 vid 390px på alla fyra.

- ID: `01M13YK1GEZEN6PKYS1A2DVDTD`
- Type: improvement
- Actor: ai:claude-fable-5

---

## [P2][done] [haven] Fäll ihop långa listor i Arbetskö och Avstämning med details-mönstret

## Context
Vid 390px blir /ko ca 7200px och /avstamning ca 8960px höga eftersom meddelandetabeller och alla församlingsblock alltid renderas utfällda. Kalendervyn visar att details/summary-mönstret redan finns i kodbasen. Arbetskön saknar dessutom en framåtlänk när alla poster är klara. (UI/UX-fynd P2 x2 + navfynd.)

## Acceptance criteria
- [ ] Meddelandetabellerna i ko.html (rad 44-64) fälls ihop bakom details/summary, konsekvent med transaktionslistorna som redan gör det (ko.html:67).
- [ ] Församlingsblocken i avstamning.html (rad 27-67) fälls ihop per församling; block med diff-rader är utfällda som default, ok-block ihopfällda.
- [ ] När alla köposter är bekräftade visar /ko en tydlig CTA vidare till /avstamning (med fil-parametern).
- [ ] Sidhöjden vid 390px för /ko och /avstamning minskar väsentligt (riktvärde: under ~halva nuvarande höjden med majdatan).
- [ ] Ingen sid-overflow i sidled vid 390px.

## Implementation hints
- Följ kalender.html:16 och ko.html:67 (details-mönstret). Rör INTE tokens.css - använd befintliga klasser; behövs ny CSS, lista den i slutrapporten.

## Verification
- Browser: mät document.documentElement.scrollHeight vid 390px före/efter på /ko och /avstamning; shot vid 390px och 1280px, ljust läge minst.
- Klicka upp ett ihopfällt block och verifiera innehållet (inte bara att summary renderas).

- ID: `01M13YJPNP91SQ963RABW4VPG5`
- Type: improvement
- Actor: ai:claude-fable-5

---

## [P2][done] [haven] Lägg till Översikt i huvudmenyn och ordna menyn efter arbetsflödet

## Context
Översikten (dashboarden med importen) nås idag bara via logotypklicket som inte ser klickbart ut, och menyn börjar med Status fast det logiskt är sista steget. En ny handläggare hittar inte månadsrutinens startpunkt. (UI/UX-fynd P1 x2, doc 01M13XZGP1NBZ99JMHYKPNY675.)

## Acceptance criteria
- [ ] "Översikt" (länk till /) ligger först i huvudnavigeringen och markeras som aktiv på /.
- [ ] Menyordningen följer arbetsflödet: Översikt, Arbetskö, Underlag, Avstämning, Justeringar, Status, Omatchade, Kalender, Konfig.
- [ ] fil-queryparametern följer med i Översikt-länken som för övriga länkar.

## Implementation hints
- app/templates/base.html:20 och navlank()-makrot rad 28-35.

## Verification
- Manuellt/browser: shot vid 390px och 1280px - menyn visar Översikt först, aktiv markering på /.
- `grep -n "Översikt" app/templates/base.html`

- ID: `01M13YHN6HVPS84BKXW4CTC0JG`
- Type: improvement
- Actor: ai:claude-fable-5

---

## [P2][done] [haven] Flagga avstämningsrader utanför KOB-exportens datumtäckning

## Context
Swish-rapporten (Uppdelad.xlsx) kan innehålla en extra dag utanför den aktuella månaden. Om KOB-exporterna inte täcker den dagen visar kollektavstämningen idag den tvetydiga orsaken "saknas i KOB - ej registrerad eller annat tillfälle", och gåvoavstämningen bara en oförklarad beloppsdiff - handläggaren letar fel på fel ställe i stället för att hämta om exporten med större datumintervall.

## Acceptance criteria
- [ ] KOB-kollektexportens datumtäckning härleds som min/max av tillfällesdatum ur raderna, insamlingsexportens som min/max av datum.
- [ ] En kollektrad i avstämningen vars datum ligger utanför kollektexportens täckning och saknar KOB-belopp får status "diff" med en orsak som säger att datumet ligger utanför exportens intervall och att exporten bör hämtas om (i stället för dagens "saknas i KOB - ej registrerad eller annat tillfälle").
- [ ] Avstämningssidan visar en varningsbanner när Swish-rapportens datumintervall inte omsluts av KOB-exportens täckning, med båda intervallen utskrivna.
- [ ] Gåvosidan får samma banner/upplysning när insamlingsexportens täckning inte omsluter rapportintervallet (avstam_gava jämför kontototaler utan datum, så diffen kan inte pekas ut per rad - bannern räcker).
- [ ] Befintliga facittester passerar oförändrat (maj 2026-datan täcks fullt av KOB-exporterna, inga nya diffar får uppstå där).

## Implementation hints
- app/core/reconcile.py: avstam_kollekt/_bedom_kollekt (orsakstexterna) och avstam_gava. Lägg täckningsintervallen i KollektAvstamning/GavaAvstamning eller i Avstamningsresultat.
- app/services/avstamning_service.py: kor_avstamning har både pipelineresultatet (res.rapport med transaktioner/datumintervall) och KOB-raderna - bra plats att räkna täckning.
- app/templates/avstamning.html: bannern (hv-badge varning-mönstret används redan i dashboard.html).
- Swish-rapportens intervall: min/max av trans_datum (datumintervall-strängen kan saknas).

## Verification
- `uv run --with pytest --with httpx pytest` - hela sviten grön.
- Nytt test i tests/: kollektavstämning där en Swish-transaktion ligger efter KOB-exportens sista datum ger utanför-intervallet-orsaken på raden; transaktion inom täckningen behåller den befintliga orsaken.
- Manuellt: öppna /avstamning för en rapport vars sista dag saknas i KOB-exporten - bannern med båda intervallen ska synas (alternativt template-/route-test som kontrollerar att bannern renderas).

- ID: `01M13XD3QPNXR6N8RZB8XJ712A`
- Type: improvement
- Actor: ai:claude-fable-5

---

## [P2][done] [haven] Förhindra att överstyrningar kan skapas utan markerade rader

Det ska inte gå att skicka in formuläret för att skapa en överstyrning (eller bryta ut en särskild post) om inga rader har markerats i listan.

- ID: `01KY24YAV84EBPXZAXWVQQ2KTN`
- Type: bug
- Actor: ai:antigravity

---

## [P2][done] [haven] Redigera ändamålsöverstyrning resettar vald fil

Att redigera en ändamålsöverstyrning verkar inte fungera, vid tryck på Ändra så resettas vald fil till den första i listan.

- ID: `01KY24QSDT78AVP6GACFCAFJWJ`
- Type: bug
- Actor: ai:antigravity

---

## [P2][todo] [haven] Userscript: dynamisk GUID-läsning + skarpt system-prefix/host

- ID: `01KXV99HY5CRBG9BA2J8CF8YB9`
- Type: improvement
- Actor: ai:claude-opus-4-8

---

## [P2][todo] [haven] Userscript: insamling/gåva-flöde

- ID: `01KXV99HY4V9PA3KBKHF6E7DVA`
- Type: feature
- Actor: ai:claude-opus-4-8

---

## [P2][todo] [haven] Userscript: R/S-komplettering (sök + komplettera, skapa aldrig)

- ID: `01KXV99HY3D87RFEYVAW7FZEYV`
- Type: feature
- Actor: ai:claude-opus-4-8

---

## [P2][todo] [haven] Userscript F-flöde: verifiera dedup kollektställe + Swish 1-ifyllnad mot KOB övning (v0.5.0)

- ID: `01KXV99HY0BB0DXM76VED3AG4Q`
- Type: chore
- Actor: ai:claude-opus-4-8

---

## [P3][done] [haven] Lägg bekräftelsesteg på Ta bort-knappar och förstora små touchytor

## Context
Ta bort-knapparna för överstyrningar, särskilda poster och mottagare skickar direkt utan bekräftelse - ett felklick raderar permanent. Ändra/Ta bort-knapparna och temaväxlaren (~25px) är dessutom små tumzoner på mobil. (UI/UX-fynd P3 x3.)

## Acceptance criteria
- [ ] Ta bort i justeringar.html (rad 41-44 och 160-163) och konfig.html (rad 23-26) kräver ett bekräftelsesteg. JS-confirm räcker, men formuläret ska fortsatt fungera utan JS (utan JS: skicka som idag).
- [ ] Ändra/Ta bort-knapparna får rimlig touchyta på mobil (minst ~34px höjd effektivt).
- [ ] Temaväxlaren får större klickyta (~40px) utan att navraden växer märkbart.

## Implementation hints
- Gemensam liten JS-hook (t.ex. data-bekrafta-attribut + en lyssnare i app.js) i stället för inline onclick per formulär.
- Temaväxlaren: tokens.css:48-52 och base.html.

## Verification
- Browser: klicka Ta bort med JS på - confirm-dialog visas, Avbryt raderar inget, OK raderar.
- shot av justeringar och konfig vid 390px - knappstorlekar.
- Befintliga tester gröna: `uv run --offline --with pytest --with httpx pytest tests/test_maj2026.py`

- ID: `01M13YKBWB3Y14WNKTX7KMP3MX`
- Type: improvement
- Actor: ai:claude-fable-5

---

## [P3][done] [haven] Ersätt engelska 'to' i datumintervallet med svenskt format

## Context
Översikten visar "period 2026-05 (2026-05-01 to 2026-05-31)" - enda engelska ordet i UI:t. Strängen byggs i ingest_swish.py:76. (UI/UX-fynd P3.)

## Acceptance criteria
- [ ] Intervallet visas som "2026-05-01 - 2026-05-31" (bindestreck) i alla vyer.
- [ ] Regexen som LÄSER rapportens "to"-format (ingest_swish._INTERVALL) fortsätter fungera - det är rapportens källformat och får inte röras.
- [ ] Facittestet och övriga tester gröna (kontrollera om någon assertion binder "to"-formatet och uppdatera i så fall).

## Implementation hints
- app/core/ingest_swish.py:76 (_las_metadata bygger visningssträngen) och ev. _harled_period som parsar den igen - håll parse och visning kompatibla.

## Verification
- `uv run --offline --with pytest --with httpx pytest tests/test_maj2026.py`
- `grep -rn " to " app/templates/ app/core/ingest_swish.py`

- ID: `01M13YJ5AWRQ1BH8PQ152HFMZF`
- Type: improvement
- Actor: ai:claude-fable-5

---

## [P3][done] [haven] Varna synligt när fil-parametern pekar på en rapport som inte finns

## Context
/avstamning?fil=finns-inte.xlsx (och övriga vyer) faller idag tyst tillbaka på senaste rapporten - en bokmärkt länk mot en borttagen fil visar fel månad utan att handläggaren märker det. (UI/UX-fynd, doc 01M13XZGP1NBZ99JMHYKPNY675.)

## Acceptance criteria
- [ ] När query-parametern fil anges men filen inte finns i data/ visas en hv-badge varning på den renderade vyn: att den begärda filen saknas och att senaste rapporten visas i stället.
- [ ] Beteendet gäller alla vyer som tar fil-parametern (via _aktuell_fil / gemensam mekanism, inte per-vy-kopior).
- [ ] Nytt prov anropar en route med okänt filnamn och verifierar att varningen renderas och att sidan fortfarande ger 200.

## Implementation hints
- app/routes/web.py:49 _aktuell_fil sväljer avvikelsen idag - låt den signalera (t.ex. returnera flagga eller lägg på request.state) och rendera i base.html.

## Verification
- `uv run --offline --with pytest --with httpx pytest tests/test_okand_fil.py` (nytt prov).
- Manuellt: /?fil=finns-inte.xlsx visar varningen.

- ID: `01M13YHXKT9KG37J9XABZMH5YB`
- Type: improvement
- Actor: ai:claude-fable-5

---

## [P3][done] [haven] Gör en övergripande UI/UX-översyn av de användarvända webbvyerna

## Context
Webbvyerna har vuxit fram funktion för funktion (dashboard, arbetskö, underlag, avstämning, kalender, justeringar, omatchade, status, konfig). En samlad översyn av flöde, konsekvens och begriplighet har inte gjorts. Userscriptet ingår INTE i denna översyn.

## Acceptance criteria
- [ ] Alla användarvända vyer genomgångna i browser (mobil ~390px och desktop ~1280px, ljust och mörkt läge).
- [ ] Fynd dokumenterade som backlog doc i haven-projektet: per vy, med konkret problem, varför det spelar roll och förslag, prioriterat.
- [ ] Fynden täcker minst: navigering/flöde mellan vyer, konsekvens i terminologi och komponenter, tomlägen/felmeddelanden, mobilanvändbarhet.
- [ ] Inga kodändringar i denna task - enbart granskning och dokumentation.

## Verification
- Manuellt: backlog doc finns i haven-projektet med prioriterade fynd per vy.

- ID: `01M13XFXP9SP3F0A22RGDMDY6D`
- Type: spike
- Actor: ai:claude-fable-5

---

## [P3][done] [haven] Varna när importerade Swish-rapporter delar transaktioner

## Context
Två Swish-rapportfiler med olika filnamn kan överlappa i innehåll (t.ex. en månadsfil och en korrigerad variant, eller en fil med extra dagar). Inget varnar idag. Bekräftelser i arbetskön delas per period + postnyckel (församling, datum, ändamål), så samma post kan se bekräftad ut i båda filerna, och samma underlag kan registreras dubbelt i KOB utan att det märks.

## Acceptance criteria
- [ ] Rapportregistret lagrar varje rapports tx_id-mängd (cachas i DB - jämförelsen får inte kräva omparsning av alla rapportfiler vid varje dashboardvisning).
- [ ] Dashboarden visar en varning när den valda rapporten delar minst en transaktion (tx_id) med en annan registrerad rapportfil, i stil med: "Rapporten delar N transaktioner med <fil> - risk för dubbelregistrering."
- [ ] Ingen varning när filerna är disjunkta.
- [ ] Befintliga tester passerar.

## Implementation hints
- tx_id sätts i app/core/ingest_swish.py (_satt_tx_id) - stabil innehållshash + dup-index i filordning.
- Rapportregistret: app/database.py (RapportRad, registrera_rapport). Ny kolumn läggs via raw ALTER TABLE-guard i database._migrera() - ingen Alembic. Lagra t.ex. som sorterad kommaseparerad/JSON-text.
- Registreringen sker via ladda_ko i app/services/ko_service.py; dashboarden i app/routes/web.py (dashboard) + app/templates/dashboard.html (hv-badge varning-mönstret finns redan för "ändrad").

## Verification
- `uv run --with pytest --with httpx pytest` - grön.
- Nytt test som anropar dashboard-routen (TestClient, jfr fixturmönstret i tests/test_import_stage.py): två registrerade rapporter med delvis samma transaktioner ger varningen i svaret; disjunkta rapporter ger ingen varning.
- Manuellt: importera samma Swish-fil under två olika filnamn - varningen ska synas på dashboarden för båda.

- ID: `01M13XD82W0T56HCRT3DP3HRYX`
- Type: improvement
- Actor: ai:claude-fable-5

---

## [P3][todo] [haven] Förhindra sparning av ändamålsöverstyrning utan Typ

När en ändamålsöverstyrning görs (t.ex. på en omatchad rad) ska den inte kunna sparas om ingen Kollekttyp är vald (eller om 'Behåll' är valt men raden saknar typ). Användaren måste få en varning, och formuläret bör kräva att en giltig typ skickas med. (Ev. även utreda om typen automatiskt kan plockas från kalendern för det angivna datumet).

- ID: `01KY29CN2X5WDAARHC9GYPGR38`
- Type: feature
- Actor: ai:antigravity

---

## [P3][done] [haven] Förhindra radbrytning av datum i /kalender

I kalendervyn (/kalender) radbryts datumkolumnen oönskat (exempelvis 2026-01-[ny rad]11). Kolumnen ska formateras så att datum inte tillåts radbrytas (t.ex. white-space: nowrap;).

- ID: `01KY2966YKZMRC027N33Y0000F`
- Type: bug
- Actor: ai:antigravity

---

## [P3][todo] [haven] Hjälp/Readme-flik i Håven

Skapa en hjälp/information/readme för Håven direkt i webbverktyget som en egen flik (route) för att användare enkelt ska kunna läsa instruktioner och dokumentation inifrån appen.

- ID: `01KY291WCSAQ724RN6M0EFRVHY`
- Type: feature
- Actor: ai:antigravity

---

## [P3][todo] [haven] Direkt export/import av KOB-avstämningsfiler via Userscript

Utreda möjlighet att direkt via Userscriptet exportera och sedan importera avstämningsfilerna (Kollekt respektive Gåva) från KOB in till Håven. Referens för redan byggt gränssnitt som exporterar filer för föregående månad eller datumintervall finns här: https://raw.githubusercontent.com/Armandur/svk-kob-enhancements/refs/heads/main/svk_kob_review_export.js

- ID: `01KY28W3C74ZY6M69FH0VNH6SM`
- Type: feature
- Actor: ai:antigravity

---

## [P3][todo] [haven] Drag-and-drop och automatisk identifiering av uppladdade filer på startsidan

Stöd drag-och-släpp (drag and drop) av filer på startsidan (/). Utred också möjligheten att ha en enda 'Välj fil'-knapp där systemet självt identifierar om det är en Swish-rapport, ändamålskalender eller KOB-export, utan att användaren behöver klicka på rätt specifik knapp.

- ID: `01KY28REBEETE0XCKKD97NFCZH`
- Type: feature
- Actor: ai:antigravity

---

## [P3][todo] [haven] Möjlighet att klistra in KOB-sökresultat för avstämning

Utöver att använda ändamålskalendern borde man kunna klistra in redan registrerade tillfällen från KOB (via 'Sök kollekttillfälle'). Detta ger ytterligare en avstämningspunkt för att se om någon redan skapat kollekttillfället för en kontantkollekt (eftersom Swish-transaktionerna redovisas först månaden efter). Formatet från KOB är: Datum | Typ | Beslutat av | Kollektändamål.

- ID: `01KY28N698BB7ZABRDE2A8BEVY`
- Type: feature
- Actor: ai:antigravity

---

## [P3][done] [haven] Knapp för att filtrera på 'Ej registrerade' i /o

I vyn /o ska det finnas en knapp (eller ett filter) som gör det möjligt att växla så att man enbart ser tillfällen som inte ännu är registrerade (d.v.s. saknar grön bock).

- ID: `01KY25BBAKD06RNPRY4EANF0B6`
- Type: feature
- Actor: ai:antigravity

---

## [P3][done] [haven] Förifyll tillfällesdatum vid överstyrning med transaktionsdatumet

När man överstyr ett datum borde Tillfälesdatum som standard fyllas i som transaktionsdatumet dvs Datum i listan på /justeringar

- ID: `01KY24WGNY4KG1F6XMN98K7VX1`
- Type: improvement
- Actor: ai:antigravity

---

## [P3][done] [haven] Visa matchade datum och dedupade meddelanden i kort-headern på /ko

I grupperingen av kollekter på /ko borde det visas i headern på respektive kort vilka datum som matchats till kollekten. Det borde också visas en dedupad lista över de meddelanden som finns på de transaktionerna. Den kan dedupas genom att omvandlas till gemener och sedan visas med Inledande versal.

- ID: `01KY24K7SM5BCSPCA59TCWAFA7`
- Type: improvement
- Actor: ai:antigravity

---

## [P3][todo] [haven] På sidan Status, Omatchade rader - klick på den borde göra att man kan se vilka rader det gäller.

- ID: `01KY1SKEVGFPT4ATKDZ5NM68JZ`
- Type: improvement
- Actor: human:rasmus

---

## [P3][done] [haven] Att klicka på bekräfta registrerad visar ingen indikation förrän sidan uppdateras

- ID: `01KY1Q7HFVCMRMMASRT528FERW`
- Type: bug
- Actor: human:rasmus

---

## [P3][todo] [haven] Userscript: per-ändamål-mottagare (Gåvomedelskassan)

- ID: `01KXV99HY8ZTNXCCS2HZN8Q1N1`
- Type: feature
- Actor: ai:claude-opus-4-8

---

## [P3][todo] [haven] Bekräfta KOB Typ för egna-verksamhets/Act-poster (Insamlingsaktivitet=3?)

- ID: `01KXV99HY7HNPVZ42BP9RRV9MM`
- Type: spike
- Actor: ai:claude-opus-4-8

---

## [P3][todo] [haven] Userscript: attest-DOM (PIN-modal + makulera)

- ID: `01KXV99HY6015A9KV4SSF24CHE`
- Type: feature
- Actor: ai:claude-opus-4-8

---

## [P3][todo] [haven] Userscript: skapa-vy-förifyllnad vid 0 träffar

- ID: `01KXV99HY6015A9KV4SGTF9JSZ`
- Type: feature
- Actor: ai:claude-opus-4-8

---

## [P4][done] [haven] Enhetlig versalisering på statusbadges mellan vyerna

## Context
Avstämningens badges är gemener ("diff", "notis") medan Status-vyns tillståndsbadges är versalinledda ("Ej påbörjad", "Registrerad"). Kosmetiskt men inkonsekvent när båda vyerna används samtidigt. (UI/UX-fynd P3/kosmetiskt.)

## Acceptance criteria
- [ ] Badge-etiketter är versalinledda konsekvent: avstämningens "diff" blir "Diff" och "notis" blir "Notis" (checkmarken för ok behålls som den är).
- [ ] Inga andra vyers badge-texter ändras (typ-bokstäverna F/R/S/N och gåva-badgen är koder, inte ord - rör dem inte).
- [ ] Befintliga tester gröna; uppdatera assertions som binder gemener om sådana finns.

## Implementation hints
- app/templates/avstamning.html (status-badgen i tabellraderna). Grep efter "notis" i templates/ för att hitta alla ställen.

## Verification
- `grep -rn ">notis<\|>diff<" app/templates/` ger inga träffar efteråt.
- `uv run --offline --with pytest --with httpx pytest tests/test_avstamning_intervall.py tests/test_maj2026.py`

- ID: `01M13ZTSVVT6B4ZB17XQZ6X48K`
- Type: improvement
- Actor: ai:claude-fable-5

---

## [P4][done] [haven] Minska chrome-till-innehåll i arbetskön på mobil

## Context
Vid 390x900 upptar logotyp+nav (tre rader) plus JSON- och userscript-knapparna nästan hela första skärmen på /ko - användaren ser ingen registreringspost före scroll, i den vy som används mest. (UI/UX-fynd P3, doc 01M13XZGP1NBZ99JMHYKPNY675.)

## Acceptance criteria
- [ ] Vid 390px bredd syns första registreringspostens kort (eller åtminstone flikraden + progressbaren + kortets överkant) utan scroll på en 390x800-viewport.
- [ ] JSON-export- och userscript-knapparna finns kvar och fungerar, men tar väsentligt mindre höjd ovanför kön (t.ex. bakom details, i en kompakt rad, eller flyttade under kön).
- [ ] Desktop 1280px: ingen försämring, knapparna fortsatt lätta att hitta.
- [ ] Ingen sid-overflow i sidled vid 390px.

## Implementation hints
- app/templates/ko.html (knappraden hv-export m.m.), ev. tokens.css för kompaktare nav-rad på mobil (media query). base.html får röras om navkompression behövs, men börja med ko.html - det räcker sannolikt.

## Verification
- Browser: shot vid 390x800 - första postkortet/flikraden synlig utan scroll; shot vid 1280px - oförändrat användbart.
- Klicka JSON-knappen och userscript-länken efter flytten - båda fungerar.

- ID: `01M13ZTGH0PZ5FV2WPC9X7NWFD`
- Type: improvement
- Actor: ai:claude-fable-5

---

## [P4][todo] [haven] Arkivering av gammalt underlag

- ID: `01KXV99HY9XQJRFB3WG5WW2GV2`
- Type: feature
- Actor: ai:claude-opus-4-8

---

