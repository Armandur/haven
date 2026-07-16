// ==UserScript==
// @name         Håven KOB-förifyllnad
// @namespace    haven.svenskakyrkan
// @version      0.2.0
// @description  Läser Håvens JSON-export och förifyller KOB (F-komplettering först). Ingen KOB-data lämnar webbläsaren.
// @author       Håven
// @match        http://kob-utb.svenskakyrkan.se/*
// @match        https://kob-utb.svenskakyrkan.se/*
// SKARP DRIFT: avkommentera raden nedan och sätt din EXAKTA skarpa KOB-host
// (verifiera host + prefix, se KOB-INMATNING §9.1/§11). Gissa inte hela domänen:
// // @match     https://KOB-SKARP-HOST/*
// @connect      ubuntu-ai
// @connect      localhost
// @grant        GM_xmlhttpRequest
// @grant        GM_getValue
// @grant        GM_setValue
// @run-at       document-idle
// ==/UserScript==

/*
 * Fas 3-userscript. Bygger på docs/KOB-INMATNING.md (live-verifierad mot övning).
 * DENNA VERSION: endast F-komplettering (Församlingskollekt). R/S + insamling/gåva
 * kommer i senare pass när F-flödet verifierats mot skarp/övnings-KOB.
 *
 * Flödet spänner över RIKTIGA sidladdningar (serverrenderad ASP.NET MVC). Därför
 * hålls arbetsläget i sessionStorage (Håvens egen export, ingen KOB-data), medan
 * attest-PIN ENDAST hålls i en modul-lokal variabel (aldrig disk/localStorage,
 * rensas vid sidladdning) enligt KOB-INMATNING §4.3.
 *
 * Allt sker lokalt i webbläsaren. Ingen data skickas till extern tjänst.
 */
(function () {
  'use strict';

  // ---------------------------------------------------------------------------
  // Konstanter
  // ---------------------------------------------------------------------------
  const STATE_KEY = 'haven_kob_state';
  const HAVEN_URL_KEY = 'haven_export_url';
  const HAVEN_URL_DEFAULT = 'http://ubuntu-ai:8003/ko/export.json';
  const KOLLEKTTYP_TEXT = { F: 'Församlingskollekt', R: 'Rikskollekt', S: 'Stiftskollekt' };

  // GM-API kan saknas beroende på userscript-manager/grants.
  const harGM = typeof GM_xmlhttpRequest !== 'undefined';
  function havenUrl() {
    try { return (typeof GM_getValue !== 'undefined' && GM_getValue(HAVEN_URL_KEY)) || HAVEN_URL_DEFAULT; }
    catch (e) { return HAVEN_URL_DEFAULT; }
  }
  function sättHavenUrl(url) {
    try { if (typeof GM_setValue !== 'undefined') GM_setValue(HAVEN_URL_KEY, url); } catch (e) { /* ignoreras */ }
  }

  // ---------------------------------------------------------------------------
  // Rena hjälpfunktioner (DOM-oberoende - testbara i isolering)
  // ---------------------------------------------------------------------------

  // Håvens belopp är punkt-decimal ("342.75"); KOB vill komma-decimal.
  function beloppTillKomma(s) {
    return String(s).trim().replace('.', ',');
  }

  // Normalisering för tolerant textmatchning (församling/ändamål).
  function normalisera(s) {
    return String(s || '')
      .toLowerCase()
      .replace(/[.,;:/½()·]/g, ' ')
      .replace(/\b(församling|pastorat|kollekt)\b/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  }

  // Jämför två fritextfält tolerant: substring åt något håll, annars ordöverlapp.
  function textMatch(a, b) {
    const na = normalisera(a), nb = normalisera(b);
    if (!na || !nb) return false;
    if (na === nb || na.includes(nb) || nb.includes(na)) return true;
    const orda = new Set(na.split(' ').filter(w => w.length > 2));
    const ordb = new Set(nb.split(' ').filter(w => w.length > 2));
    if (!orda.size || !ordb.size) return false;
    let gemensamma = 0;
    for (const w of orda) if (ordb.has(w)) gemensamma++;
    const union = new Set([...orda, ...ordb]).size;
    return gemensamma / union >= 0.4;
  }

  // Validera Håven-underlaget. Returnerar {ok, fel, underlag}.
  function validateUnderlag(text) {
    let data;
    try { data = JSON.parse(text); } catch (e) { return { ok: false, fel: 'Ogiltig JSON: ' + e.message }; }
    if (!data || typeof data !== 'object') return { ok: false, fel: 'Förväntade ett JSON-objekt.' };
    if (data.kalla !== 'Håven') return { ok: false, fel: 'Fältet "kalla" är inte "Håven".' };
    if (!Array.isArray(data.poster)) return { ok: false, fel: 'Saknar "poster"-lista.' };
    return { ok: true, underlag: data };
  }

  // Matcha en resultatrad (sökträff) mot en F-post. Kolumner enligt §2.3:
  // td0=Datum, td1=Typ, td2=Beslutat av, td3=Kollektändamål.
  // OBS: söker med TOM Purpose (§2.2), så disambiguering sker här klientsidan.
  function matchaResultatrad(tds, post) {
    const beslutatAv = tds[2] || '';
    const andamal = tds[3] || '';
    return textMatch(beslutatAv, post.forsamling) && textMatch(andamal, post.andamal);
  }

  // Hämta underlaget direkt från Håven via GM_xmlhttpRequest (kringgår CORS;
  // Håven behöver inte vara öppen som flik, bara nås över nätet). onOk(text)/onErr(msg).
  function hamtaFranHaven(url, onOk, onErr) {
    if (!harGM) { onErr('GM_xmlhttpRequest saknas - kontrollera @grant/manager.'); return; }
    GM_xmlhttpRequest({
      method: 'GET', url: url, timeout: 15000,
      onload: r => (r.status >= 200 && r.status < 300)
        ? onOk(r.responseText)
        : onErr('Håven svarade ' + r.status + '.'),
      onerror: () => onErr('Kunde inte nå Håven (' + url + '). Nätverk/host?'),
      ontimeout: () => onErr('Timeout mot Håven (' + url + ').'),
    });
  }

  // ---------------------------------------------------------------------------
  // DOM-hjälp
  // ---------------------------------------------------------------------------
  const q = (sel, root) => (root || document).querySelector(sel);
  const qa = (sel, root) => Array.from((root || document).querySelectorAll(sel));

  function synligText(el) { return (el && el.textContent || '').replace(/\s+/g, ' ').trim(); }

  // Vänta tills predikatet ger truthy (returneras) eller timeout (null).
  function waitFor(predikat, timeout = 8000, intervall = 120) {
    return new Promise(resolve => {
      const start = Date.now();
      const tick = () => {
        let v = null;
        try { v = predikat(); } catch (e) { v = null; }
        if (v) return resolve(v);
        if (Date.now() - start >= timeout) return resolve(null);
        setTimeout(tick, intervall);
      };
      tick();
    });
  }

  // Sätt värde på en <select> genom att matcha SYNLIG optionstext (GUID:er är
  // miljöspecifika - hårdkoda aldrig, §9.6). Returnerar true om satt.
  function valjOptionViaText(select, text) {
    if (!select) return false;
    const mål = normalisera(text);
    let träff = Array.from(select.options).find(o => normalisera(o.textContent) === mål);
    if (!träff) träff = Array.from(select.options).find(o => normalisera(o.textContent).includes(mål) && mål);
    if (!träff) return false;
    select.value = träff.value;
    select.dispatchEvent(new Event('change', { bubbles: true }));
    return true;
  }

  function sättFält(input, värde) {
    if (!input) return false;
    input.value = värde;
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
    return true;
  }

  function basePath() {
    const m = location.pathname.match(/^(.*?\/Web)(\/|$)/i);
    return m ? m[1] : '';
  }

  // ---------------------------------------------------------------------------
  // Arbetsläge (sessionStorage) + PIN (endast i minnet)
  // ---------------------------------------------------------------------------
  let sessionPin = null;       // ALDRIG till disk/localStorage. Rensas vid sidladdning.
  let attestLage = false;      // opt-in, default AV (§4.3). Hålls i minnet per sidladdning.

  function laddaState() {
    try { return JSON.parse(sessionStorage.getItem(STATE_KEY) || 'null'); }
    catch (e) { return null; }
  }
  function sparaState(s) { sessionStorage.setItem(STATE_KEY, JSON.stringify(s)); }
  function uppdateraState(delta) {
    const s = laddaState() || {};
    Object.assign(s, delta);
    sparaState(s);
    return s;
  }
  function nollställState() { sessionStorage.removeItem(STATE_KEY); ritaPanel(); }

  function tillämpaUnderlag(text, källa) {
    const r = validateUnderlag(text);
    if (!r.ok) { alert('Kunde inte läsa underlaget:\n' + r.fel); return false; }
    sparaState({ underlag: r.underlag, index: null, step: null, active: false });
    ritaPanel();
    logga(`Underlag laddat (${källa}): period ${r.underlag.period}, ${r.underlag.poster.length} poster.`);
    return true;
  }

  // ---------------------------------------------------------------------------
  // Injicerad panel
  // ---------------------------------------------------------------------------
  let panelEl = null, loggEl = null, väntarEl = null;

  function css() {
    if (q('#haven-kob-style')) return;
    const s = document.createElement('style');
    s.id = 'haven-kob-style';
    s.textContent = `
      #haven-kob-fab{position:fixed;right:16px;bottom:16px;z-index:2147483646;
        background:#2d6a4f;color:#fff;border:none;border-radius:24px;padding:10px 16px;
        font:600 14px system-ui;cursor:pointer;box-shadow:0 2px 8px rgba(0,0,0,.3)}
      #haven-kob-panel{position:fixed;right:16px;bottom:64px;z-index:2147483646;width:340px;
        max-height:78vh;overflow:auto;background:#fff;color:#111;border:1px solid #ccc;
        border-radius:10px;box-shadow:0 4px 20px rgba(0,0,0,.25);font:13px/1.4 system-ui;display:none}
      #haven-kob-panel.open{display:block}
      #haven-kob-panel h3{margin:0;padding:10px 12px;background:#2d6a4f;color:#fff;font-size:14px;
        border-radius:10px 10px 0 0;display:flex;justify-content:space-between;align-items:center}
      #haven-kob-panel .kropp{padding:10px 12px}
      #haven-kob-panel textarea{width:100%;height:64px;box-sizing:border-box;font:11px monospace}
      #haven-kob-panel button{font:12px system-ui;cursor:pointer;border-radius:6px;
        border:1px solid #bbb;background:#f3f3f3;padding:4px 8px}
      #haven-kob-panel button.primar{background:#2d6a4f;color:#fff;border-color:#2d6a4f}
      #haven-kob-panel .post{border-top:1px solid #eee;padding:6px 0;display:flex;
        justify-content:space-between;gap:6px;align-items:center}
      #haven-kob-panel .post small{color:#555;display:block}
      #haven-kob-panel .disabled{opacity:.45}
      #haven-kob-panel .status{font-weight:600;margin:6px 0}
      #haven-kob-logg{background:#111;color:#8f8;font:11px/1.4 monospace;padding:6px;
        border-radius:6px;max-height:120px;overflow:auto;white-space:pre-wrap}
      #haven-kob-vantar{margin:6px 0}
      #haven-kob-vantar button{display:block;width:100%;text-align:left;margin:3px 0}
      #haven-kob-attest{border-top:1px solid #eee;margin-top:8px;padding-top:8px}
      #haven-kob-attest input[type=password]{width:80px}
      @media (prefers-color-scheme: dark){
        #haven-kob-panel{background:#1d1f22;color:#eee;border-color:#333}
        #haven-kob-panel button{background:#33363b;color:#eee;border-color:#555}
        #haven-kob-panel .post small{color:#aaa}
      }`;
    document.head.appendChild(s);
  }

  function logga(msg) {
    const rad = new Date().toLocaleTimeString('sv-SE') + '  ' + msg;
    if (loggEl) { loggEl.textContent += (loggEl.textContent ? '\n' : '') + rad; loggEl.scrollTop = loggEl.scrollHeight; }
    console.log('[Håven]', msg);
  }

  function byggHamtaSektion(harUnderlag) {
    const box = document.createElement('div');
    box.style.cssText = 'border-bottom:1px solid #eee;padding-bottom:8px;margin-bottom:6px';
    const lbl = document.createElement('label');
    lbl.style.cssText = 'display:block;font-size:11px;color:#666;margin-bottom:2px';
    lbl.textContent = 'Håven export-URL';
    const url = document.createElement('input');
    url.type = 'text';
    url.value = havenUrl();
    url.style.cssText = 'width:100%;box-sizing:border-box;font:11px monospace;margin-bottom:4px';
    url.onchange = () => sättHavenUrl(url.value.trim());
    const btn = document.createElement('button');
    btn.className = 'primar';
    btn.textContent = harUnderlag ? 'Hämta igen från Håven' : 'Hämta från Håven';
    btn.onclick = () => {
      const u = url.value.trim();
      sättHavenUrl(u);
      btn.disabled = true; btn.textContent = 'Hämtar...';
      hamtaFranHaven(u,
        text => { btn.disabled = false; tillämpaUnderlag(text, 'Håven'); },
        msg => { btn.disabled = false; btn.textContent = harUnderlag ? 'Hämta igen från Håven' : 'Hämta från Håven'; alert('Hämtning misslyckades:\n' + msg); logga('Hämtning misslyckades: ' + msg); });
    };
    box.appendChild(lbl);
    box.appendChild(url);
    box.appendChild(btn);
    if (!harGM) {
      btn.disabled = true;
      const n = document.createElement('small');
      n.style.cssText = 'display:block;color:#b45309;margin-top:4px';
      n.textContent = 'GM_xmlhttpRequest saknas i denna manager/grant - använd inklistring nedan.';
      box.appendChild(n);
    }
    return box;
  }

  function ritaPanel() {
    css();
    if (!q('#haven-kob-fab')) {
      const fab = document.createElement('button');
      fab.id = 'haven-kob-fab';
      fab.textContent = 'Håven';
      fab.onclick = () => panelEl.classList.toggle('open');
      document.body.appendChild(fab);
    }
    if (!panelEl) {
      panelEl = document.createElement('div');
      panelEl.id = 'haven-kob-panel';
      document.body.appendChild(panelEl);
    }
    const state = laddaState();
    const u = state && state.underlag;
    const fPoster = u ? u.poster.map((p, i) => ({ p, i })).filter(x => x.p.typ === 'F') : [];

    panelEl.innerHTML = '';
    const h = document.createElement('h3');
    h.innerHTML = '<span>Håven → KOB (F)</span>';
    const stäng = document.createElement('button');
    stäng.textContent = '✕';
    stäng.style.cssText = 'background:transparent;border:none;color:#fff;font-size:16px';
    stäng.onclick = () => panelEl.classList.remove('open');
    h.appendChild(stäng);
    panelEl.appendChild(h);

    const kropp = document.createElement('div');
    kropp.className = 'kropp';
    panelEl.appendChild(kropp);

    // Hämta-från-Håven-sektion (visas alltid; låter dig ladda/uppdatera underlag).
    kropp.appendChild(byggHamtaSektion(!!u));

    if (!u) {
      const p = document.createElement('p');
      p.style.margin = '8px 0 4px';
      p.innerHTML = '...eller klistra in JSON manuellt (<code>/ko</code> → "Kopiera underlag som JSON"):';
      kropp.appendChild(p);
      const ta = document.createElement('textarea');
      ta.placeholder = '{ "kalla": "Håven", "poster": [...] }';
      kropp.appendChild(ta);
      const btn = document.createElement('button');
      btn.textContent = 'Ladda inklistrat';
      btn.onclick = () => tillämpaUnderlag(ta.value, 'inklistrat');
      kropp.appendChild(btn);
    } else {
      const info = document.createElement('div');
      info.className = 'status';
      const antalF = fPoster.length;
      info.textContent = `Period ${u.period} · ${u.poster.length} poster (${antalF} F)`;
      kropp.appendChild(info);

      väntarEl = document.createElement('div');
      väntarEl.id = 'haven-kob-vantar';
      kropp.appendChild(väntarEl);

      if (state.active && typeof state.index === 'number') {
        const akt = u.poster[state.index];
        const s = document.createElement('div');
        s.className = 'status';
        s.textContent = `Aktiv: #${state.index + 1} ${akt.forsamling} ${akt.datum} (${state.step})`;
        kropp.appendChild(s);
      }

      fPoster.forEach(({ p, i }) => {
        const rad = document.createElement('div');
        rad.className = 'post';
        const v = document.createElement('div');
        v.innerHTML = `<strong>${p.forsamling}</strong><small>${p.datum} · ${p.andamal} · ${beloppTillKomma(p.belopp)} kr</small>`;
        const b = document.createElement('button');
        b.textContent = 'Bearbeta';
        b.onclick = () => startaFPost(i);
        rad.appendChild(v);
        rad.appendChild(b);
        kropp.appendChild(rad);
      });

      const övriga = u.poster.length - fPoster.length;
      if (övriga > 0) {
        const not = document.createElement('div');
        not.className = 'post disabled';
        not.innerHTML = `<small>${övriga} R/S- och insamling/gåva-poster hanteras inte i denna version (kommer senare).</small>`;
        kropp.appendChild(not);
      }

      // Attest opt-in
      const at = document.createElement('div');
      at.id = 'haven-kob-attest';
      const lbl = document.createElement('label');
      const cb = document.createElement('input');
      cb.type = 'checkbox';
      cb.checked = attestLage;
      cb.onchange = () => {
        attestLage = cb.checked;
        if (!attestLage) sessionPin = null;
        ritaPanel();
      };
      lbl.appendChild(cb);
      lbl.appendChild(document.createTextNode(' Attest-läge (opt-in, default av)'));
      at.appendChild(lbl);
      if (attestLage) {
        const pinWrap = document.createElement('div');
        pinWrap.style.marginTop = '6px';
        pinWrap.innerHTML = 'PIN (endast i minnet): ';
        const pin = document.createElement('input');
        pin.type = 'password';
        pin.value = sessionPin || '';
        pin.oninput = () => { sessionPin = pin.value || null; };
        pinWrap.appendChild(pin);
        const varn = document.createElement('small');
        varn.style.cssText = 'display:block;color:#b45309;margin-top:4px';
        varn.textContent = 'Attest-DOM (PIN-modal/makulera) är EJ live-verifierad (§11). Du bekräftar varje attest med Enter.';
        at.appendChild(pinWrap);
        at.appendChild(varn);
      }
      kropp.appendChild(at);

      const rad2 = document.createElement('div');
      rad2.style.marginTop = '8px';
      const åter = document.createElement('button');
      åter.textContent = 'Återställ underlag';
      åter.onclick = () => { if (confirm('Rensa inläst underlag?')) nollställState(); };
      rad2.appendChild(åter);
      kropp.appendChild(rad2);
    }

    loggEl = document.createElement('div');
    loggEl.id = 'haven-kob-logg';
    kropp.appendChild(loggEl);
  }

  function visaVal(titel, val) {
    if (!väntarEl) return;
    väntarEl.innerHTML = '';
    const t = document.createElement('div');
    t.className = 'status';
    t.textContent = titel;
    väntarEl.appendChild(t);
    val.forEach(v => {
      const b = document.createElement('button');
      b.textContent = v.text;
      b.onclick = v.onclick;
      väntarEl.appendChild(b);
    });
    panelEl.classList.add('open');
  }
  function rensaVal() { if (väntarEl) väntarEl.innerHTML = ''; }

  // ---------------------------------------------------------------------------
  // F-flöde: sök → (töm filter) → komplettera via grönt +
  // ---------------------------------------------------------------------------

  function startaFPost(index) {
    const state = laddaState();
    if (!state || !state.underlag) return;
    const post = state.underlag.poster[index];
    if (post.typ !== 'F') { alert('Endast F-poster stöds i denna version.'); return; }
    uppdateraState({ index, step: 'sok', active: true });
    logga(`Startar F #${index + 1}: ${post.forsamling} ${post.datum} ${post.andamal}`);
    // Navigera till sökvyn (formuläret fylls + submitas när sidan laddat).
    location.href = basePath() + '/Collection/CollectionOccasionSearch/Search';
  }

  async function körSok(post) {
    logga('Fyller sökformuläret (Typ + datum, TOM Purpose).');
    const typeSel = await waitFor(() => q('#Type'));
    if (!typeSel) { logga('FEL: hittade inte #Type på sökvyn.'); return; }
    if (!valjOptionViaText(typeSel, KOLLEKTTYP_TEXT[post.typ])) {
      logga(`FEL: kunde inte välja kollekttyp "${KOLLEKTTYP_TEXT[post.typ]}".`); return;
    }
    const purpose = q('#Purpose'); if (purpose) purpose.value = '';   // tom med flit (§2.2)
    sättFält(q('#OccasionDateFrom'), post.datum);
    sättFält(q('#OccasionDateTo'), post.datum);
    uppdateraState({ step: 'resultat' });
    logga('Skickar sökning...');
    (q('#btnSubmit') || q('#searchform [type=submit]')).click();
  }

  function tomDataTablesFilter() {
    const f = q('#collectionOccasionTable_filter input, .dataTables_filter input');
    if (f && f.value) {
      logga(`Tömmer DataTables-filter (var: "${f.value}").`);
      f.value = '';
      f.dispatchEvent(new Event('keyup', { bubbles: true }));
      f.dispatchEvent(new Event('input', { bubbles: true }));
    }
  }

  function synligaResultatrader() {
    return qa('#collectionOccasionTable tbody tr').filter(tr => {
      if (tr.offsetParent === null) return false;                // dold av DataTables
      const tds = qa('td', tr);
      if (!tds.length) return false;
      if (tds.length === 1 && /Inga|hittade/i.test(synligText(tr))) return false; // "Inga rader"-rad
      return true;
    });
  }

  async function utvarderaResultat(post) {
    await waitFor(() => q('#collectionOccasionTable'));
    tomDataTablesFilter();
    await waitFor(() => true, 400);   // låt DataTables rita om efter filtertömning
    const rader = synligaResultatrader();
    logga(`Sökträffar efter filtertömning: ${rader.length}.`);

    const träffar = rader.filter(tr => matchaResultatrad(qa('td', tr).map(synligText), post));

    if (träffar.length === 1) {
      logga('1 matchande träff → öppnar för komplettering.');
      uppdateraState({ step: 'fyll' });
      träffar[0].click();
      return;
    }
    if (rader.length === 0) {
      logga('0 sökträffar → förslag: skapa nytt (semi-manuellt).');
      visaVal(`Inga tillfällen ${post.datum}. Skapa nytt?`, [{
        text: 'Öppna skapa-vyn (förifylls, du sparar själv)',
        onclick: () => { uppdateraState({ step: 'skapa' }); location.href = basePath() + '/Collection/CollectionOccasion/Main'; }
      }]);
      return;
    }
    // 0 exakta matchningar men rader finns, ELLER flera matchningar → låt användaren välja.
    logga(`${träffar.length} exakta matchningar, ${rader.length} rader totalt → be användaren välja (gissar aldrig).`);
    const kandidater = träffar.length ? träffar : rader;
    visaVal(`Välj rätt tillfälle för ${post.forsamling} ${post.datum}:`,
      kandidater.map(tr => {
        const c = qa('td', tr).map(synligText);
        return {
          text: `${c[0]} · ${c[2]} · ${c[3]}`,
          onclick: () => { rensaVal(); uppdateraState({ step: 'fyll' }); tr.click(); }
        };
      }).concat([{ text: 'Ingen passar - hoppa över', onclick: () => { rensaVal(); avslutaPost('Hoppade över (ingen träff valdes).'); } }]));
  }

  // ---------------------------------------------------------------------------
  // Fyll belopp på tillfället via grönt + (RowExpander), rad-scopat
  // ---------------------------------------------------------------------------

  function beloppsrader() {
    return qa('#collectionAmountsDetailsTable tbody tr').filter(tr => q('img.RowExpander', tr) || q('[name="amount.Amount"]', tr));
  }

  async function fyllTillfalle(post) {
    const grid = await waitFor(() => q('#collectionAmountsDetailsTable'));
    if (!grid) { logga('FEL: hittade inte beloppsrutnätet.'); return; }
    // Rader vars Församlings-cell (td1) matchar posten. Kollektställe okänt i Håven → be välja vid flera.
    const rader = beloppsrader().filter(tr => {
      const tds = qa('td', tr);
      return tds[1] && textMatch(synligText(tds[1]), post.forsamling) && q('img.RowExpander', tr);
    });
    if (rader.length === 0) {
      logga(`FEL: ingen rad matchar församlingen "${post.forsamling}". Kontrollera manuellt.`);
      return;
    }
    if (rader.length === 1) { await fyllRad(rader[0], post); return; }
    logga(`${rader.length} kollektställen för ${post.forsamling} → be användaren välja rad.`);
    visaVal(`Vilket kollektställe ska ${beloppTillKomma(post.belopp)} kr bokas på?`,
      rader.map(tr => {
        const tds = qa('td', tr);
        return { text: `${synligText(tds[1])} / ${synligText(tds[3])}`, onclick: () => { rensaVal(); fyllRad(tr, post); } };
      }));
  }

  async function fyllRad(rad, post) {
    const expander = q('img.RowExpander', rad);
    if (!expander) { logga('FEL: saknar grönt + på raden.'); return; }
    const föreAntal = beloppsrader().length;
    logga('Klickar grönt + (lägger ny Swish-rad, rör inte befintlig).');
    expander.click();
    // Ny tom rad dyker upp direkt under; identifiera den (ny + tomt beloppsfält).
    const nyRad = await waitFor(() => {
      if (beloppsrader().length <= föreAntal) return null;
      let n = rad.nextElementSibling;
      while (n) {
        const inp = q('[name="amount.Amount"]', n);
        if (inp && !inp.value) return n;
        n = n.nextElementSibling;
      }
      return null;
    });
    if (!nyRad) { logga('FEL: ny beloppsrad dök inte upp efter grönt +.'); return; }

    sättFält(q('[name="amount.Amount"]', nyRad), beloppTillKomma(post.belopp));
    const metod = q('[name="amount.PaymentMethodID"]', nyRad) || q('[name="amount.PaymentMethodId"]', nyRad);
    if (!valjOptionViaText(metod, post.inbetalningsmetod)) {
      logga(`VARNING: kunde inte välja inbetalningsmetod "${post.inbetalningsmetod}" - välj manuellt.`);
    }
    logga(`KLART: ${beloppTillKomma(post.belopp)} kr / ${post.inbetalningsmetod} ifyllt. Granska och tryck SPARA själv (Alt+S).`);
    logga('Stannar före Spara med flit. Auto-klickar aldrig Spara eller gränsvärdesvarning ("Ja").');
    if (attestLage) logga('Attest-läge PÅ: attestera manuellt efter Spara (attest-DOM ej verifierad i denna version).');
    avslutaPost(null);
    panelEl.classList.add('open');
  }

  function avslutaPost(msg) {
    if (msg) logga(msg);
    uppdateraState({ active: false, step: null });
    ritaPanel();
    panelEl.classList.add('open');
  }

  // ---------------------------------------------------------------------------
  // Dispatch: körs vid varje sidladdning
  // ---------------------------------------------------------------------------
  function dispatch() {
    ritaPanel();
    const state = laddaState();
    if (!state || !state.active || !state.underlag || typeof state.index !== 'number') return;
    const post = state.underlag.poster[state.index];
    const p = location.pathname;
    if (/\/CollectionOccasionSearch\/Search/i.test(p)) {
      if (state.step === 'sok') körSok(post);
      else if (state.step === 'resultat') utvarderaResultat(post);
    } else if (/\/CollectionOccasion\/Main/i.test(p)) {
      if (state.step === 'fyll') fyllTillfalle(post);
      else if (state.step === 'skapa') logga('Skapa-vyn öppen. Förifyllnad av skapa-formuläret kommer i senare version - fyll och spara manuellt.');
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', dispatch);
  else dispatch();
})();
