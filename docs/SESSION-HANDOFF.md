# Session-handoff — Håven

Läs denna + `ROADMAP.md` + `CLAUDE.md` först i en ny session. Statusbild och lösa trådar per 2026-07-16.

## Läge i stort
- **Fas 0-2 är klara** (kärna, arbetskö, underlag, avstämning, justeringar/överstyrningar/särskilda poster/radval/historik, statusspårning, rapportregister+idempotens, redigerbar konfig, filuppladdning, kalendervy, temaväljare, mängder av UI-polish). Se `ROADMAP.md` (allt bockat t.o.m. Fas 2).
- **Fas 3 påbörjad:** KOB-inmatningskartläggningen är klar (`docs/KOB-INMATNING.md`, live-verifierad mot övningssystemet), och JSON-exporten ur registreringskön är byggd (`/ko/export.json` + "Kopiera underlag som JSON" på `/ko`, `bygg_export` i `ko_service.py`).
- **20 tester gröna** (`tests/test_maj2026.py`, facit maj 2026). Kör: `rm -f haven_test.db; HAVEN_DB=haven_test.db uv run --with pytest pytest -q`.

## NÄSTA UPPGIFT (Fas 3): bygg KOB-userscriptet
Tampermonkey/Violentmonkey-script som läser Håvens JSON-export och förifyller KOB enligt `docs/KOB-INMATNING.md`. Börja med **F-komplettera-flödet** (det mest kritiska och fullt live-verifierade):
1. Injicerad panel i KOB som läser underlag som JSON (urklipp/textarea). Schema: se KOB-INMATNING §9.1.
2. F: deep-linka Sök (`Search?Type={F-GUID}&Purpose=&OccasionDateFrom=&OccasionDateTo=`), **töm DataTables-Filtrera-rutan** (§2.2 - kritisk fälla), läs radantal → 1 träff komplettera / 0 skapa / >1 fråga användaren.
3. Fyll belopp: matcha rätt `<tr>` via Församling/Kollektställe-text, klicka **grönt +** (`img.RowExpander`) för Swish-rad, scope per rad (id:n ej unika), sätt `amount.Amount` + `amount.PaymentMethodID` (kollekt) resp. `PaymentMethodId` (insamling) + `change`.
4. **Stanna före Spara** (människan trycker). Gränsvärdesvarning (noty): lyft fram, auto-klicka inte "Ja".
5. R/S: sök+komplettera bara, **skapa aldrig**.
6. **Attest = opt-in-läge** (default av), sessions-PIN cachad i minnet, Enter bekräftar varje. Reversibelt via makulera. Se KOB-INMATNING §4.3/§4.4/§9.5/§10.

Lägg scriptet t.ex. i `userscript/haven-kob.user.js` (ny mapp). Ingen KOB-data lämnar webbläsaren.

## Lösa trådar / öppna punkter (mest i KOB-INMATNING §11)
- **Insamling/gåva Typ-alternativ avviker mot handboken** (Egna verksamheten visar "Anslag" i live men ej i handbok; "Gåva" saknas för Egna). Bekräfta manuellt vilken Typ era egna-verksamhets-/Act-poster ska ha (troligen Insamlingsaktivitet=3). Påverkar §7.5-mappningen.
- **Attest + makulera ej live-verifierat** - övningskontot (KOBAlla1) saknade attesträtt. PIN-modalens selektorer är fångade men makulera-knapp/dialog-selektorer saknas. Behöver ett kompletterande Claude-for-Chrome-pass av någon med attesträtt (prompt finns: `docs/kob-inmatning-prompt.md`).
- **"Attesterad kontant → komplettera Swish"** kunde inte köras end-to-end (samma attesträtt-spärr). Handboken säger att grönt + funkar oavsett status; verifiera för status A i övning.
- **GUID:er i KOB-INMATNING gäller Östervåla-Harbo/övningsmiljön** - userscriptet ska läsa select-options dynamiskt (matcha på synlig text, inte hårdkoda GUID) i skarp miljö. URL-prefix `KOB_Utb1` är övning; skarpt prefix skiljer.
- **Per-ändamål (Gåvomedelskassan)** mottagare/typ i KOB ej verifierad mot konkret exempel.
- **Gåva-mottagare i JSON-exporten** utelämnas medvetet (Håven vet inte KOB-mottagaren säkert) - userscriptet/handläggaren avgör.

## Miljö-noter från kartläggningen (i övningssystemet - ofarligt)
- PIN `1234` sattes på övningskontot KOBAlla1; testdata skapades (F-tillfälle 2026-07-16 GUID `5d94ca8e-1081-f111-9db2-005056a5bf31`, R-belopp tillagt). Endast övning. Se KOB-INMATNING §12.

## Drift / verifiering
- **Kör dev-servern själv** och ge klickbar `http://ubuntu-ai:PORT`-länk (se CLAUDE.md dev-serverflöde). Starta: `uv run uvicorn app.main:app --host 0.0.0.0 --port <svc port>`. Registrera i portalen (`svc register haven ...`). Städtillåtelse för egna orphanade haven-servrar.
- **Verifiera UI vid BÅDE mobil (~390px) och desktop (~1280px+)** - inte bara en bredd (se browser-verify-skillen; en headerbugg gömde sig annars).
- `haven.db` innehåller en genuin Stigsjö-överstyrning (05-23 Musikverksamheten, tx_ids-baserad) - den gör maj-avstämningen ren. Rör den inte.

## Nyckelfiler
- Kärna: `app/core/` (pipeline, reconcile, regler, aggregate, ingest_*). Tjänster: `app/services/` (ko_service med bygg_export, avstamning_service, status_service, import_service, konfig_service). Routes: `app/routes/web.py`. Mallar: `app/templates/`. Stil/JS: `app/static/`.
- Fas 3-underlag: `docs/KOB-INMATNING.md` (specen), `docs/kob-inmatning-prompt.md` (Claude-for-Chrome-prompt), `docs/kob-handbok.html` (handboken som HTML-referens).
- Data (gitignorat): `data/` - Swish maj 2026 + KOB-exporter + kalender.
