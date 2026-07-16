# Prompt till Claude for Chrome: kartlägg KOB:s inmatningsgränssnitt

Detta är en färdig prompt att klistra in i **Claude for Chrome** när du är inloggad
i KOB (Svenska kyrkans kollekt- och betalsystem). Syftet är att låta Claude
dokumentera exakt hur den manuella inmatningen går till - fält, DOM-selektorer och
flöde per posttyp - så att dokumentationen kan ligga till grund för ett
**userscript** som halvautomatiserar inmatningen från verktyget Håven.

Kör den gärna i flera pass (ett per posttyp). **Skicka aldrig in riktiga belopp
under kartläggningen** - utforska formulären, men avbryt före Spara, eller använd
ett känt testtillfälle om ett sådant finns.

---

## Prompten (klistra in nedan i Claude for Chrome)

Du hjälper mig att kartlägga inmatningsgränssnittet i KOB (Svenska kyrkans
kollekt- och betalsystem) som jag är inloggad i just nu i den här fliken. Målet
är att producera en teknisk specifikation som ska ligga till grund för ett
**userscript (Tampermonkey/Violentmonkey)** som förifyller inmatningsformulären
utifrån ett färdigt underlag. Du ska **dokumentera, inte mata in något skarpt** -
utforska formulären men avbryt före Spara/Skicka (eller använd ett testtillfälle
om jag pekar ut ett).

### Bakgrund (kontext du behöver)
- Jag har ett internt verktyg ("Håven") som läser månadens Swish-rapport och tar
  fram ett registreringsunderlag. Idag läser jag av underlaget på skärmen och
  skriver in det manuellt i KOB. Jag vill halvautomatisera inmatningen med ett
  userscript som fyller i fälten åt mig, medan jag granskar och sparar.
- **Inbetalningsmetod är alltid "Swish 1"** i vårt fall och ska kunna förifyllas.
- Belopp kan ha ören (decimaltal) och får aldrig avrundas.

### Posttyper som ska registreras (kartlägg var och en)
1. **Församlingskollekt (F)** - registreras per församling, per gudstjänstdatum,
   per ändamål. Handläggaren skapar tillfället själv om det saknas.
2. **Rikskollekt (R)** och **Stiftskollekt (S)** - registreras på ett
   **gemensamt tillfälle för hela riket/stiftet** per ändamål och datum, där varje
   församlings belopp matas in under samma tillfälle. **Dessa tillfällen ägs och
   skapas av andra (nationellt/regionalt) - handläggaren skapar dem ALDRIG, utan
   kompletterar bara belopp på befintliga tillfällen.**
3. **Insamling/gåva - månadssumma** - en summa per verksamhet och månad.
   Handläggaren skapar tillfället/insamlingen själv om det saknas.
4. **Insamling/gåva - per ändamål** (t.ex. Gåvomedelskassan) - en post per ändamål.
5. **Särskild post** (utbruten ur en verksamhets månadssumma, t.ex. loppis, ljus,
   konsert) - registreras separat som egen insamlingsaktivitet med egen
   beskrivning/öronmärkning.

### Detta ska du dokumentera för VARJE posttyp ovan
- **Navigering:** exakt väg i menyn/URL:erna för att nå rätt inmatningsvy
  (klickstig + resulterande URL:er, och om URL:en är parametriserbar).
- **Komplettera vs. skapa:** hur ser man i UI:t om ett tillfälle redan finns
  (då kompletteras bara belopp) kontra måste skapas? Vilka knappar/vyer skiljer sig?
  (Kom ihåg: R/S skapas aldrig av oss.)
- **Fältlista:** varje inmatningsfält i formuläret, med:
  - Etikett (svensk text i UI:t)
  - Fälttyp (text/select/datum/radio/checkbox/autocomplete)
  - En **robust selektor** (helst `id`, annars `name`, annars en stabil
    CSS-/XPath-selektor; notera om fältet ligger i en iframe eller genereras
    dynamiskt)
  - Möjliga värden för select/autocomplete (t.ex. lista över ändamål,
    kollekttyper, inbetalningsmetoder) och hur de väljs programmatiskt (sätta
    `.value` räcker sällan för ramverksbundna selects - notera om det krävs
    `input`/`change`-event eller tangentbordssimulering)
  - Vilket värde från underlaget som ska in i fältet (församling, datum, ändamål,
    kollekttyp F/R/S, belopp, inbetalningsmetod = "Swish 1")
- **Ordning och beroenden:** fyller man i uppifrån och ner? Låser val i ett fält
  upp/fyller i andra (t.ex. att välja församling filtrerar ändamål)? Finns
  autospar eller validering som triggar vid blur?
- **Spara-flödet:** vilken knapp sparar, vad händer efter (redirect, toast,
  radläggning i en lista), och hur ser man att det lyckades. Går det att spara
  flera poster i rad utan att lämna vyn (relevant för R/S där alla församlingars
  belopp matas på samma tillfälle)?
- **Fallgropar:** dynamiskt renderade fält, iframes, CSRF-tokens i formuläret,
  fält som kräver fokus/tab för att aktiveras, tidsgränser/utloggning.

### Format på leveransen
Producera en **Markdown-spec** (`KOB-INMATNING.md`) med en sektion per posttyp
enligt ovan, plus:
- En **gemensam fältordlista** (underlagets begrepp -> KOB-fält -> selektor).
- Ett kort avsnitt **"Rekommendation för userscript"**: hur skulle ett userscript
  praktiskt förifylla fälten (t.ex. en knapp som injiceras i KOB som läser ett
  underlag från urklipp/JSON och fyller i), hur hanteras komplettera-vs-skapa,
  och var det MÅSTE stanna för manuell granskning innan Spara.
- Notera allt du är osäker på eller inte kunde verifiera utan att spara skarpt.

### Viktiga regler (får inte brytas)
- **Mata inte in eller spara några skarpa belopp** under kartläggningen.
- **Föreslå aldrig att userscriptet ska skapa R- eller S-tillfällen** - bara
  komplettera befintliga.
- Userscriptet ska alltid **stanna för manuell granskning och kräva att en
  människa trycker Spara** - ingen tyst autoinmatning.
- Håll allt lokalt/i webbläsaren. Skicka inte KOB-data till någon extern tjänst.

Börja med att beskriva vad du ser i den nuvarande vyn, och fråga mig vilken
posttyp vi ska kartlägga först om det är oklart.

---

## Efter kartläggningen (för Håven-bygget)
Spara KOB-teamets svar som `docs/KOB-INMATNING.md` i det här repot. Den blir
underlaget för Fas 3: ett userscript plus ett exportformat från Håven (t.ex. en
"kopiera underlag som JSON"-knapp i registreringskön) som userscriptet läser.
Bekräfta särskilt fältmappningen som spec 12.2 lämnade öppen.
