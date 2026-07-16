# Testa KOB-userscriptet mot utbildningsmiljön

Övnings-KOB är inloggad som **Östervåla-Harbo pastorat** (församlingar Harbo +
Östervåla, kollektställen Stenkyrkan/Strandkyrkan). Håvens skarpa export gäller
Härnösands församlingar och matchar därför inte övningen. Använd i stället
test-underlaget här.

## Test-underlag

`userscript/test-underlag-utb.json` - härlett ur den riktiga exportstrukturen men
med Harbo/Östervåla-församlingar och ändamål. Serveras av Håven på:

    http://ubuntu-ai:8003/kob-test-underlag.json

Peka userscriptets **"Håven export-URL"** dit och klicka **"Hämta från Håven"**
(eller klistra in filen manuellt). Innehåller två F-poster som testar båda grenarna:

| # | Församling | Datum | Ändamål | Belopp | Väntad gren |
|---|---|---|---|---|---|
| 1 | Harbo församling | 2026-07-16 | Testkollekt userscript-kartläggning | 150,25 | **komplettera** (1 träff) |
| 2 | Östervåla församling | 2026-07-15 | Diakonala hjälpfonden | 275,50 | **skapa** (0 träffar) |

## Förutsättning i KOB övning

Post 1 kräver att F-tillfället från kartläggningen finns kvar (KOB-INMATNING §12):
Församlingskollekt 2026-07-16, beslutat av Harbo församling, ändamål
"Testkollekt userscript-kartläggning", klarmarkerat. Finns det → post 1 hittar
det och kompletterar med en Swish-rad via grönt +.

Saknas det (t.ex. rensat) → skapa ett nytt likadant, eller ändra datum/ändamål i
`test-underlag-utb.json` så det pekar på ett tillfälle som finns.

Post 2 (Östervåla 2026-07-15) förväntas ge 0 träffar → scriptet erbjuder
skapa-vyn (semi-manuell). Vill du testa **komplettering** för Östervåla också:
skapa först ett F-tillfälle i KOB övning (2026-07-15, egna verksamheten, beslutat
av Östervåla församling, ändamål "Diakonala hjälpfonden", klarmarkera) så blir
post 2 en komplettera-träff i stället.

## Testgång

1. Installera/uppdatera scriptet via http://ubuntu-ai:8003/ko → "Installera KOB-userscript".
2. Öppna en KOB-utbildningssida, öppna Håven-panelen, sätt URL:en ovan, "Hämta från Håven".
3. **Post 1 (Harbo):** "Bearbeta" → sök körs, filtret töms, tillfället öppnas,
   grönt + klickas, ny rad fylls 150,25 / Swish 1. Kontrollera att kontant-/
   befintlig rad är orörd. Scriptet stannar före Spara - spara själv.
4. **Post 2 (Östervåla):** "Bearbeta" → 0 träffar → panelen erbjuder skapa-vyn.

Detta är endast övningsdata. Ingen skarp bokföring påverkas.
