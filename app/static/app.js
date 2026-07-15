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

    function synlig(r) {
      var d = r.dataset.datum;
      if (fran.value && d < fran.value) return false;
      if (till.value && d > till.value) return false;
      if (medd.value && r.dataset.meddelande.indexOf(medd.value.toLowerCase()) < 0) return false;
      return true;
    }
    function uppdatera() {
      var vis = 0, mark = 0, summa = 0;
      rows.forEach(function (r) {
        var s = synlig(r);
        r.hidden = !s;
        if (s) vis++;
        var cb = r.querySelector(".hv-valj");
        if (cb.checked) { mark++; summa += parseFloat(r.dataset.belopp) || 0; }
      });
      antal.textContent = vis;
      markantal.textContent = mark;
      marksumma.textContent = fmt(summa);
    }
    [fran, till, medd].forEach(function (el) { el.addEventListener("input", uppdatera); });
    table.addEventListener("change", function (e) {
      if (e.target.classList.contains("hv-valj")) uppdatera();
    });

    // Skift+klick markerar intervallet av synliga rader mellan senaste och nuvarande.
    var sistaIdx = null;
    table.addEventListener("click", function (e) {
      var cb = e.target;
      if (!cb.classList || !cb.classList.contains("hv-valj")) return;
      var idx = rows.indexOf(cb.closest("tr"));
      if (e.shiftKey && sistaIdx !== null && idx !== -1) {
        var lo = Math.min(sistaIdx, idx), hi = Math.max(sistaIdx, idx);
        for (var i = lo; i <= hi; i++) {
          if (!rows[i].hidden) rows[i].querySelector(".hv-valj").checked = cb.checked;
        }
        uppdatera();
      }
      sistaIdx = idx;
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
