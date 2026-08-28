// Progressiv async for arbetskon: utan JS postar formularen och sidan laddas om;
// med JS bekraftas/angras via fetch utan omladdning, med synlig progress.
(function () {
  "use strict";

  function postForm(form) {
    return fetch(form.action, {
      method: "POST",
      headers: { "X-Requested-With": "fetch" },
      body: new FormData(form),
    }).then(function (r) {
      if (!r.ok) throw new Error("Serverfel " + r.status);
      return r.json();
    });
  }

  function uppdateraProgress(klara, totalt) {
    var bar = document.getElementById("hv-progressbar");
    var txt = document.getElementById("hv-klara");
    if (bar) bar.value = klara;
    if (txt) txt.textContent = klara;
  }

  function markeraAktuell() {
    var poster = document.querySelectorAll(".hv-post[data-nyckel]");
    var hittat = false;
    poster.forEach(function (post) {
      post.classList.remove("hv-aktuell");
      if (!hittat && !post.classList.contains("hv-klar")) {
        post.classList.add("hv-aktuell");
        hittat = true;
      }
    });
  }

  function uppdateraFlikar() {
    var par = [["koll-klara", ".hv-panel-koll"], ["gava-klara", ".hv-panel-gava"]];
    par.forEach(function (p) {
      var span = document.querySelector('[data-roll="' + p[0] + '"]');
      var panel = document.querySelector(p[1]);
      if (span && panel) {
        span.textContent = panel.querySelectorAll(".hv-post.hv-klar").length;
      }
    });
  }

  function sattTillstand(post, bekraftad) {
    post.classList.toggle("hv-klar", bekraftad);
    var bekr = post.querySelector('[data-roll="bekrafta-form"]');
    var angra = post.querySelector('[data-roll="angra-form"]');
    var marke = post.querySelector('[data-roll="klarmarke"]');
    if (bekr) bekr.hidden = bekraftad;
    if (angra) angra.hidden = !bekraftad;
    if (marke) marke.hidden = !bekraftad;
  }

  document.addEventListener("submit", function (ev) {
    var form = ev.target;
    var roll = form.getAttribute("data-roll");
    if (roll !== "bekrafta-form" && roll !== "angra-form") return;
    ev.preventDefault();

    var post = form.closest(".hv-post");
    form.querySelectorAll("button").forEach(function (b) { b.setAttribute("aria-busy", "true"); });

    postForm(form).then(function (data) {
      sattTillstand(post, data.bekraftad);
      uppdateraProgress(data.klara, data.totalt);
      uppdateraFlikar();
      markeraAktuell();
      if (data.bekraftad) {
        var next = document.querySelector(".hv-post.hv-aktuell");
        if (next) next.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    }).catch(function (e) {
      alert("Kunde inte spara: " + e.message);
    }).finally(function () {
      form.querySelectorAll("button").forEach(function (b) { b.removeAttribute("aria-busy"); });
    });
  });
})();

// Bekraftelsesteg pa Ta bort-knappar: data-bekrafta="fraga" pa formularet.
// Progressiv: utan JS skickas formuläret direkt som idag.
(function () {
  "use strict";
  document.addEventListener("submit", function (ev) {
    var form = ev.target;
    var fraga = form.getAttribute("data-bekrafta");
    if (fraga && !window.confirm(fraga)) {
      ev.preventDefault();
    }
  });
})();

// Justeringsvyn: live-filtrering av radtabeller, markera-alla-synliga och
// lopande rakning av markerade rader + summa. Progressiv: utan JS visas alla
// rader med kryssrutor och kan bockas manuellt.
(function () {
  "use strict";
  function fmt(n) { return n.toFixed(2).replace(".", ","); }

  function initBox(box) {
    var table = box.querySelector(".hv-radtabell");
    if (!table) return;
    var rows = Array.prototype.slice.call(table.querySelectorAll("tbody tr.hv-rad"));
    var fran = box.querySelector(".hv-f-fran");
    var till = box.querySelector(".hv-f-till");
    var medd = box.querySelector(".hv-f-medd");
    var antal = box.querySelector(".hv-antal");
    var markantal = box.querySelector(".hv-markantal");
    var marksumma = box.querySelector(".hv-marksumma");
    var allC = box.querySelector(".hv-markera-alla");
    var datumInput = box.querySelector("input[name='ny_tillfallesdatum']");
    if (datumInput) {
      datumInput.addEventListener("input", function() { datumInput.dataset.manuell = "true"; });
    }

    function synlig(r) {
      var d = r.dataset.datum;
      if (fran.value && d < fran.value) return false;
      if (till.value && d > till.value) return false;
      if (medd.value && r.dataset.meddelande.indexOf(medd.value.toLowerCase()) < 0) return false;
      return true;
    }
    function uppdatera() {
      var vis = 0, mark = 0, summa = 0;
      var forstaDatum = null;
      rows.forEach(function (r) {
        var s = synlig(r);
        r.hidden = !s;
        if (s) vis++;
        var cb = r.querySelector(".hv-valj");
        if (cb.checked) { 
          mark++; 
          summa += parseFloat(r.dataset.belopp) || 0; 
          if (!forstaDatum) forstaDatum = r.dataset.datum;
        }
      });
      antal.textContent = vis;
      markantal.textContent = mark;
      marksumma.textContent = fmt(summa);
      
      if (datumInput && forstaDatum && !datumInput.dataset.manuell) {
        datumInput.value = forstaDatum;
      }
      
      var form = box.querySelector("form");
      if (form) {
        var btn = form.querySelector('button[type="submit"]');
        if (btn) btn.disabled = (mark === 0);
      }
    }
    [fran, till, medd].forEach(function (el) { el.addEventListener("input", uppdatera); });
    table.addEventListener("change", function (e) {
      if (e.target.classList.contains("hv-valj")) uppdatera();
    });

    // Hela raden ar klickbar (storre tumzon). Skift+klick markerar intervallet
    // av synliga rader mellan senaste och nuvarande.
    var sistaIdx = null;
    table.addEventListener("click", function (e) {
      var tr = e.target.closest("tr.hv-rad");
      if (!tr) return;
      var cb = tr.querySelector(".hv-valj");
      if (!cb) return;
      var idx = rows.indexOf(tr);
      // Klick pa sjalva kryssrutan har redan togglat den; radklick togglar manuellt.
      if (e.target !== cb) {
        cb.checked = !cb.checked;
      }
      if (e.shiftKey && sistaIdx !== null && idx !== -1) {
        var lo = Math.min(sistaIdx, idx), hi = Math.max(sistaIdx, idx);
        for (var i = lo; i <= hi; i++) {
          if (!rows[i].hidden) rows[i].querySelector(".hv-valj").checked = cb.checked;
        }
      }
      sistaIdx = idx;
      uppdatera();
    });
    if (allC) allC.addEventListener("change", function () {
      rows.forEach(function (r) {
        if (!r.hidden) r.querySelector(".hv-valj").checked = allC.checked;
      });
      uppdatera();
    });
    uppdatera();
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".hv-radfilter").forEach(initBox);
  });
})();

// Avstämning: "Visa bara diffar" - döljer rena församlingskort och rader utan diff.
(function () {
  "use strict";
  var cb = document.getElementById("bara-diff");
  if (!cb) return;
  function applicera() {
    var on = cb.checked;
    document.querySelectorAll(".hv-avst-fors[data-hardiff]").forEach(function (a) {
      a.hidden = on && a.dataset.hardiff !== "true";
    });
    document.querySelectorAll("tr[data-diff]").forEach(function (tr) {
      tr.hidden = on && tr.dataset.diff !== "true";
    });
  }
  cb.addEventListener("change", applicera);
})();

// Arbetskö: kopiera registreringsunderlaget som JSON (för KOB-userscriptet).
// Fallback till execCommand eftersom Clipboard-API:t blockeras på icke-secure origin.
(function () {
  "use strict";
  var btn = document.getElementById("export-json");
  if (!btn) return;
  var ta = document.getElementById("export-textarea");
  var status = document.getElementById("export-status");
  btn.addEventListener("click", function () {
    btn.setAttribute("aria-busy", "true");
    fetch(btn.dataset.url, { headers: { "Accept": "application/json" } })
      .then(function (r) { if (!r.ok) throw new Error("fel " + r.status); return r.json(); })
      .then(function (data) {
        var txt = JSON.stringify(data, null, 2);
        ta.value = txt; ta.hidden = false;
        ta.focus(); ta.select(); ta.setSelectionRange(0, txt.length);
        var ok = false;
        try { ok = document.execCommand("copy"); } catch (e) { /* ignore */ }
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(txt).then(function () { ok = true; }, function () {});
        }
        status.hidden = false;
        status.textContent = (ok ? "✓ kopierat till urklipp" : "markera i rutan och kopiera")
          + " · " + data.antal_poster + " poster";
      })
      .catch(function (e) {
        status.hidden = false; status.textContent = "Kunde inte hämta: " + e.message;
      })
      .finally(function () { btn.removeAttribute("aria-busy"); });
  });
})();
