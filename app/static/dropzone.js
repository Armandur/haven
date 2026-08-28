/*
 * Samlad slappzon med automatisk typidentifiering (tvastegsimport).
 *
 * Varje slappt fil laddas upp direkt till /import/stage (per-fil-progress)
 * och hamnar i staging pa servern, som forsoker identifiera sorten. Kortet
 * "Kontrollera filtyperna" visas direkt under importkortet med identifierad
 * typ per fil (andringsbar via dropdown). Fler filer kan slappas medan kortet
 * ar oppet - de laggs till i listan. "Importera" validerar och flyttar
 * filerna till data/, "Avbryt" kasserar de stagade. Utan JS syns i stallet
 * det manuella formularet.
 */
(function () {
  "use strict";

  var zone = document.getElementById("dropzone");
  if (!zone) return;

  var input = document.getElementById("dropzone-input");
  var manuell = document.getElementById("import-manuell");
  var kort = document.getElementById("stage-kort");
  var titleEl = document.getElementById("stage-title");
  var listEl = document.getElementById("stage-filelist");
  var detailEl = document.getElementById("stage-detail");
  var avbrytEl = document.getElementById("stage-avbryt");
  var importEl = document.getElementById("stage-importera");

  var SORTER = [
    ["swish", "Swish-rapport"],
    ["kob_kollekt", "KOB kollektexport"],
    ["kob_insamling", "KOB insamlingsexport"],
    ["kalender", "Ändamålskalender"],
  ];

  // JS pa: visa zonen, fall ihop det manuella formularet (noscript-fallback).
  zone.hidden = false;
  if (manuell) manuell.removeAttribute("open");

  var rader = [];      // {fil, token, sparad, status, felrad, select, li}
  var pagaende = 0;    // antal filer som fortfarande laddas upp

  function setStatus(rad, state, text) {
    rad.status.className = "ufile-status ufile-" + state;
    rad.status.textContent = text;
  }

  function stageOne(rad, onProgress) {
    return new Promise(function (resolve) {
      var fd = new FormData();
      fd.append("fil", rad.fil, rad.fil.name);
      var xhr = new XMLHttpRequest();
      xhr.open("POST", "/import/stage");
      xhr.upload.addEventListener("progress", function (e) {
        if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100));
      });
      xhr.addEventListener("load", function () {
        try { resolve(JSON.parse(xhr.responseText || "{}")); }
        catch (e) { resolve({ ok: false, fel: "svar kunde inte tolkas" }); }
      });
      xhr.addEventListener("error", function () { resolve({ ok: false, fel: "nätverksfel" }); });
      xhr.send(fd);
    });
  }

  function byggRad(fil) {
    var li = document.createElement("li");
    li.className = "ufile";
    var radEl = document.createElement("div");
    radEl.className = "ufile-rad";
    var namn = document.createElement("span");
    namn.className = "ufile-name";
    namn.textContent = fil.name;
    var select = document.createElement("select");
    select.className = "ufile-select";
    select.hidden = true;
    var tom = document.createElement("option");
    tom.value = "";
    tom.textContent = "Välj typ...";
    select.appendChild(tom);
    SORTER.forEach(function (s) {
      var o = document.createElement("option");
      o.value = s[0];
      o.textContent = s[1];
      select.appendChild(o);
    });
    var status = document.createElement("span");
    status.className = "ufile-status";
    status.textContent = "väntar";
    radEl.appendChild(namn); radEl.appendChild(select); radEl.appendChild(status);
    var felrad = document.createElement("div");
    felrad.className = "ufile-fel";
    felrad.hidden = true;
    li.appendChild(radEl); li.appendChild(felrad);
    listEl.appendChild(li);
    var rad = { fil: fil, token: null, sparad: false,
                status: status, felrad: felrad, select: select, li: li };
    select.addEventListener("change", uppdateraKnapp);
    rader.push(rad);
    return rad;
  }

  function uppdateraKnapp() {
    var kvar = rader.filter(function (r) { return r.token && !r.sparad; });
    importEl.disabled = pagaende > 0 || !kvar.length ||
      kvar.some(function (r) { return !r.select.value; });
  }

  function visaIdentifiering(rad, res) {
    if (!res.ok) {
      setStatus(rad, "error", "fel");
      rad.felrad.textContent = res.fel || "okänt fel";
      rad.felrad.hidden = false;
      return;
    }
    rad.token = res.token;
    rad.select.hidden = false;
    if (res.sort) {
      rad.select.value = res.sort;
      setStatus(rad, "done", "identifierad");
    } else {
      setStatus(rad, "error", "okänd typ - välj själv");
    }
  }

  // Slappta filer laggs till i kortet - fungerar bade for forsta slappet
  // och for fler filer medan kortet redan ar oppet.
  function laggTill(filer) {
    if (kort.hidden) {
      listEl.textContent = "";
      rader = [];
      kort.hidden = false;
    }
    var nya = filer.map(byggRad);
    pagaende += nya.length;
    titleEl.textContent = "Laddar upp filer...";
    detailEl.textContent = "";
    importEl.disabled = true;
    avbrytEl.disabled = false;

    var next = 0, active = 0, klara = 0, CONC = 3;
    function pump() {
      if (klara >= nya.length) return;
      while (active < CONC && next < nya.length) {
        (function (rad) {
          active++;
          setStatus(rad, "uploading", "laddar upp 0%");
          stageOne(rad, function (pct) {
            setStatus(rad, "uploading", "laddar upp " + pct + "%");
          }).then(function (res) {
            visaIdentifiering(rad, res);
            active--; klara++; pagaende--;
            if (pagaende === 0) {
              titleEl.textContent = "Kontrollera filtyperna";
              detailEl.textContent =
                "Ändra typ i listan om något blev fel, och importera sedan. " +
                "Fler filer kan släppas i zonen ovanför.";
            }
            uppdateraKnapp();
            pump();
          });
        })(nya[next++]);
      }
    }
    pump();
  }

  importEl.addEventListener("click", function () {
    var kvar = rader.filter(function (r) { return r.token && !r.sparad; });
    if (!kvar.length) return;
    importEl.disabled = true;
    avbrytEl.disabled = true;
    kvar.forEach(function (r) { setStatus(r, "uploading", "importerar..."); });
    fetch("/import/bekrafta", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ val: kvar.map(function (r) {
        return { token: r.token, sort: r.select.value };
      }) }),
    }).then(function (svar) { return svar.json(); }).then(function (d) {
      var perToken = {};
      (d.resultat || []).forEach(function (r) { perToken[r.token] = r; });
      var fel = 0;
      kvar.forEach(function (rad) {
        var r = perToken[rad.token] || { ok: false, fel: "inget svar" };
        if (r.ok) {
          rad.sparad = true;
          rad.select.hidden = true;
          setStatus(rad, "done", "sparad");
          rad.felrad.hidden = true;
        } else {
          fel++;
          setStatus(rad, "error", "fel");
          rad.felrad.textContent = r.fel || "okänt fel";
          rad.felrad.hidden = false;
        }
      });
      avbrytEl.disabled = false;
      if (fel === 0) {
        titleEl.textContent = "Klart";
        window.location.reload();
      } else {
        titleEl.textContent = fel + " fil(er) kunde inte importeras";
        detailEl.textContent = "Ändra typ och försök igen, eller avbryt för att kasta de kvarvarande.";
        importEl.textContent = "Försök igen";
        uppdateraKnapp();
      }
    }).catch(function () {
      titleEl.textContent = "Nätverksfel - försök igen";
      avbrytEl.disabled = false;
      uppdateraKnapp();
    });
  });

  avbrytEl.addEventListener("click", function () {
    var tokens = rader.filter(function (r) { return r.token && !r.sparad; })
                      .map(function (r) { return r.token; });
    var nagonSparad = rader.some(function (r) { return r.sparad; });
    avbrytEl.disabled = true;
    var klart = tokens.length
      ? fetch("/import/kassera", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ tokens: tokens }),
        }).catch(function () {})
      : Promise.resolve();
    klart.then(function () {
      kort.hidden = true;
      listEl.textContent = "";
      rader = [];
      avbrytEl.disabled = false;
      importEl.textContent = "Importera";
      if (nagonSparad) window.location.reload();
    });
  });

  // Zonen: klick, tangentbord och drag-och-slapp.
  zone.addEventListener("click", function () { input.click(); });
  zone.addEventListener("keydown", function (e) {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); input.click(); }
  });
  input.addEventListener("change", function () {
    if (input.files && input.files.length) {
      laggTill(Array.prototype.slice.call(input.files));
      input.value = "";
    }
  });
  ["dragenter", "dragover"].forEach(function (ev) {
    zone.addEventListener(ev, function (e) {
      e.preventDefault();
      zone.classList.add("dragover");
    });
  });
  ["dragleave", "drop"].forEach(function (ev) {
    zone.addEventListener(ev, function (e) {
      e.preventDefault();
      zone.classList.remove("dragover");
    });
  });
  zone.addEventListener("drop", function (e) {
    var filer = e.dataTransfer && e.dataTransfer.files;
    if (filer && filer.length) laggTill(Array.prototype.slice.call(filer));
  });

  // Slapp utanfor zonen ska inte fa webblasaren att navigera till filen.
  window.addEventListener("dragover", function (e) { e.preventDefault(); });
  window.addEventListener("drop", function (e) { e.preventDefault(); });
})();
