# Prompt till Claude for Chrome: kartlägg KOB:s inmatningsgränssnitt

Färdig prompt att klistra in i **Claude for Chrome** när du är inloggad i KOB
(Svenska kyrkans kollekt- och betalsystem). Syftet är att dokumentera **exakta
DOM-selektorer och det faktiska flödet** för inmatningen, som underlag för ett
**userscript** som halvautomatiserar inmatningen från verktyget Håven.

Prompten är nu **grundad i KOB-handboken** (`docs/kob-handbok.html` i det här
repot, konverterad ur den officiella PDF:en, uppdaterad 14 maj 2025). Flödet och
terminologin nedan är hämtade därifrån - Claudes jobb blir därför främst att
fånga **selektorer**, verifiera att flödet stämmer mot live-UI:t och notera vad
som ändrats sedan handboken.

**Kör den mot KOB:s övningssystem.** Där spelar det ingen roll vad Claude gör -
den får skapa, spara, klarmarkera och attestera fritt för att fullt exercera
flödet. En begränsning i övningsmiljön: **det finns inga registrerade
församlingskollekter** där, så för att kartlägga F-flödet måste Claude **själv
skapa ett kollekttillfälle** (skapa -> klarmarkera -> registrera belopp).
Riks-/stiftskollekter (nationell data) kan finnas eller saknas - be Claude
kontrollera. De hårda reglerna längst ned (aldrig skapa R/S, aldrig auto-attestera)
beskriver hur det **färdiga userscriptet ska bete sig i skarp drift** - de gäller
alltså inte Claudes utforskning i övningssystemet, som är fri.

---

## Prompten (klistra in nedan i Claude for Chrome)

Du hjälper mig att kartlägga inmatningsgränssnittet i KOB (Svenska kyrkans
kollekt- och betalsystem) som jag är inloggad i i den här fliken. Målet är en
teknisk specifikation som ska ligga till grund för ett **userscript
(Tampermonkey/Violentmonkey)** som förifyller inmatningsformulären utifrån ett
färdigt underlag.

**KOB-handboken finns i en annan flik.** Jag har öppnat KOB:s handbok som HTML i
en annan flik i den här webbläsaren, som du har åtkomst till. Byt gärna till den
fliken och läs själv när du behöver - den innehåller hela handboken med
skärmdumpar av formulären och en innehållsförteckning (avsnitt som
"Kollekttillfälle", "Kollektbelopp", "Insamling/gåva"). Använd den som facit för
hur flödet är tänkt att fungera, och jämför mot vad du faktiskt ser i KOB:s UI.

**Miljö: detta är KOB:s övningssystem** - du får skapa, fylla i, spara,
klarmarkera och attestera fritt för att fullt kartlägga flödet, med riktiga
klick och riktig inmatning (inga skarpa data påverkas). Utforska hela vägen, men
**dokumentera noggrant vad varje steg gör**. Två saker att veta:
- **Det finns inga registrerade församlingskollekter** i övningssystemet. För att
  kartlägga F-flödet behöver du därför **själv skapa ett kollekttillfälle** och
  gå hela vägen: skapa -> välj mottagare/ändamål/kollektställe -> klarmarkera ->
  registrera belopp med inbetalningsmetod Swish.
- **Riks-/stiftskollekter** (R/S) registreras nationellt "för hela året" - kolla
  om sådana tillfällen finns i övningssystemet. Finns de: kartlägg
  komplettera-belopp-flödet på ett befintligt R/S-tillfälle. Saknas de: notera det
  och beskriv komplettera-flödet så långt UI:t tillåter.

### Kontext: verktyget Håven
Jag har ett internt verktyg ("Håven") som läser månadens Swish-rapport och tar
fram ett registreringsunderlag per månad. Idag läser jag av underlaget och
skriver in det manuellt i KOB. Jag vill halvautomatisera inmatningen med ett
userscript som fyller i fälten åt mig, medan jag granskar och sparar. Underlaget
har fyra sorters poster:
- **Församlingskollekt (F)** - per församling/kollektställe, per gudstjänstdatum, per ändamål.
- **Riks- (R) och stiftskollekt (S)** - alla församlingars belopp på ett gemensamt tillfälle per ändamål/datum.
- **Insamling/gåva - månadssumma** - en summa per verksamhet och månad (t.ex. Act, Diakoni, Musik).
- **Särskild post** - utbruten ur en verksamhets månadssumma (loppis, ljus, konsert).
- **Insamling/gåva per ändamål** - t.ex. Gåvomedelskassan, en post per ändamål.

**Inbetalningsmetoden är alltid "Swish"** i vårt fall. Belopp kan ha ören.

### Så här fungerar KOB (bekräftat ur handboken - verifiera mot live-UI:t)
Detta är redan känt; din uppgift är att fånga selektorerna och bekräfta/korrigera:

**Kollekt**
- Kollekttillfället måste finnas och vara **klarmarkerat** innan ett kollektbelopp
  kan registreras. Klarmarkering kräver att mottagare är valda och att
  procentfördelningen är 100 %.
- **Riks- och stiftskollekter registreras och klarmarkeras av den nationella nivån
  och finns redan i systemet för hela året.** Församlingen/pastoratet skapar dem
  ALDRIG - de kompletteras bara med belopp. (Det går att registrera belopp även om
  ett R/S-tillfälle inte är klarmarkerat.)
- **Församlingskollekter** skapas av församlingen. Undertyper: "till egna
  verksamheten", "till extern kontakt", och **"Församlingskollekt nationell
  organisation"** (för Act Svenska kyrkan / Svenska kyrkan i utlandet - nettas).
- **Flera kyrkors belopp på samma tillfälle:** om flera kyrkor tagit upp kollekt
  till samma ändamål fyller man i beloppen för de olika kyrkorna **på samma
  tillfälle** (välj kollektställe eller "Alla"). Detta är exakt hur våra R/S ska
  matas in - ett tillfälle, alla församlingars belopp under.
- **Registrera tillfälle:** Meny Kollekt → "Kollekttillfälle - skapa nytt".
  Knappar "Spara" resp. "Spara och klarmarkera".
- **Registrera belopp:** startsidans ikon "Kollekter, ej registrerade belopp",
  eller Meny Kollekt → "Kollektbelopp - registrera" (lista över tillfällen med ej
  registrerade belopp, idag + 60 dagar bakåt). Finns inte tillfället i listan:
  **"Sök kollekttillfälle"** för att komplettera ett befintligt, annars skapa nytt.
- När belopp registreras väljs **inbetalningsmetod** (kontant/kort/Swish). Har man
  fått in samma kollekt både kontant och Swish **läggs Swish till som en egen rad**.
- **"Kollekt ej upptagen"** - kryssruta per kollektställe som saknar belopp.
- **Gränsvärdesvarning:** systemet varnar (men tillåter spara) när ett belopp ligger
  utanför församlingens gränsvärden. Userscriptet måste kunna hantera/passera denna varning.
- **Attestering är ett separat steg** (kräver attesteringsbehörighet och **PIN-kod**).

**Insamling/gåva**
- Meny "Insamling/gåva" → **"Ny insamling/gåva"**.
- **Mottagare:** Act Svenska kyrkan, Svenska kyrkan i utlandet (båda nettas),
  Extern kontakt, eller Egna verksamheten.
- **Typ:** Anslag, **Gåva**, **Insamlingsaktivitet** (bössinsamling, loppmarknad,
  café, ljusbärare - alltså våra "särskilda poster"). Obs: för Act finns bara
  Anslag och Insamlingsaktivitet, inte Gåva.
- Fältet **"typ av aktivitet / beskrivning"** anger verksamhet/beskrivning (samma
  fält som syns i KOB-exporten vi läser). **Öronmärkning** till insamlingstema/projekt.
- **Avsändare** = vilken församling insamlingen gäller.
- **Inbetalningsmetod obligatorisk** (Swish), egen rad per metod.
- Attestering separat (PIN-kod). "Markera som utbetald" och "Kopiera" finns också.

### Detta ska du dokumentera för VARJE posttyp (F, R/S, insamling månadssumma, särskild post, per-ändamål)
1. **Navigering:** exakt klickstig och resulterande URL:er (och om URL:en är
   parametriserbar/deeplink-bar till rätt inmatningsvy).
2. **Komplettera vs. skapa:** exakt hur man i UI:t når "komplettera belopp på
   befintligt tillfälle" (Sök kollekttillfälle / listan över ej registrerade
   belopp) kontra "skapa nytt tillfälle". För R/S: bekräfta att tillfällena redan
   finns och att man bara kompletterar - userscriptet får ALDRIG skapa R/S.
3. **Fältlista** för varje formulär, med:
   - Etikett (svensk UI-text), fälttyp (text/select/datum/radio/checkbox/autocomplete).
   - **Robust selektor** (helst `id`, annars `name`, annars stabil CSS/XPath). Notera
     om fältet ligger i **iframe**, renderas dynamiskt, eller byggs av ett
     JS-ramverk (React/Angular/Vue) - för ramverksbundna `select`/autocomplete
     räcker sällan att sätta `.value`; notera om det krävs `input`/`change`-event,
     tangentbordssimulering eller att man öppnar dropdownen och klickar ett alternativ.
   - Möjliga värden (kollektställe inkl. "Alla", ändamål, mottagare, typ,
     öronmärkning, inbetalningsmetod) och hur de väljs programmatiskt.
   - Vilket värde ur Håvens underlag som ska in (församling/kollektställe, datum,
     ändamål, kollekttyp F/R/S, belopp, inbetalningsmetod = Swish, beskrivning,
     öronmärkning).
4. **"Lägg till rad"-mekaniken:** hur man lägger till en Swish-rad under
   inbetalningsmetod, och (för R/S och "flera kyrkor på samma tillfälle") hur man
   lägger till ytterligare kollektställe/belopp på samma tillfälle. Selektor för
   "lägg till rad"-knappen och för fälten i den nya raden.
5. **Klarmarkering, spara och varningar:** selektorer för "Spara" / "Spara och
   klarmarkera", hur klarmarkeringskravet (mottagare + 100 %) syns, och hur
   gränsvärdesvarningen ser ut i DOM:en (så scriptet kan passera den). Vad händer
   efter spara (redirect/toast/radläggning) och hur ser man att det lyckades.
6. **Fallgropar:** dynamiskt renderade fält, iframes, CSRF-token i formulär, fält
   som kräver fokus/tab, autocomplete som kräver riktig tangentbordsinmatning,
   tidsgräns/utloggning, och **allt som skiljer sig från handbokens beskrivning
   (14 maj 2025)** - notera ändringar.

### Format på leveransen
Producera en **Markdown-spec** (`KOB-INMATNING.md`) med:
- En sektion per posttyp enligt ovan.
- En **gemensam fältordlista:** Håvens begrepp -> KOB-fält (UI-etikett) -> selektor.
- Ett avsnitt **"Rekommendation för userscript":** hur scriptet praktiskt förifyller
  fälten (t.ex. en injicerad knapp i KOB som läser ett underlag från urklipp/JSON),
  hur komplettera-vs-skapa avgörs, hur "lägg till rad" hanteras för R/S, och exakt
  var scriptet MÅSTE stanna för manuell granskning.
- Notera allt du är osäker på eller inte kunde verifiera utan att spara skarpt.

### Regler för det FÄRDIGA userscriptet (dokumentera dessa som krav - de gäller skarp drift, inte din utforskning i övningssystemet)
- **Userscriptet ska aldrig skapa R- eller S-tillfällen** - bara komplettera
  befintliga (de ägs av nationella nivån). (Du får däremot titta på hur ett
  R/S-tillfälle ser ut i övningssystemet.)
- **Userscriptet ska aldrig attestera eller mata in PIN-kod** - attestering är ett
  separat, manuellt behörighetssteg. Scriptet fyller bara i belopp och stannar.
- Userscriptet ska alltid **stanna för manuell granskning och kräva att en människa
  trycker Spara** - ingen tyst autoinmatning i skarpt läge.
- Allt lokalt/i webbläsaren; ingen KOB-data till extern tjänst.

Börja med att beskriva vad du ser i nuvarande vy och fråga vilken posttyp vi ska
kartlägga först om det är oklart. Slå upp KOB-handboken i den andra fliken när du
behöver referens för hur ett flöde eller fält är tänkt att fungera.

---

## Efter kartläggningen (för Håven-bygget)
Spara svaret som `docs/KOB-INMATNING.md`. Nästa steg i Fas 3:
1. **Export ur Håven:** en "kopiera underlag som JSON"-knapp i registreringskön,
   med fälten userscriptet behöver (posttyp F/R/S/insamling, församling/kollektställe,
   datum, ändamål/beskrivning, öronmärkning, belopp, inbetalningsmetod=Swish).
2. **Userscriptet** som läser JSON:en och förifyller KOB enligt specen, med
   komplettera-vs-skapa-logik (aldrig skapa R/S), "lägg till rad" för R/S-gruppering,
   och stopp för manuell granskning + Spara. Attestering görs alltid manuellt.
