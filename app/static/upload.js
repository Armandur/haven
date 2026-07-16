/*
 * Async filuppladdning med per-fil-progress och partiell-fel-hantering.
 *
 * En request per fil till /import (bara det faltet), sa varje fil valideras och
 * sparas for sig - en trasig fil forkastar inte de andra. Begransad parallellitet.
 * Faller tillbaka pa vanlig formularpost om JS ar av (formularet fungerar utan
 * denna fil).
 */
(function () {
  "use strict";

  var form = document.getElementById("import-form");
  if (!form) return;

  var ETIKETT = {
    swish: "Swish-rapport", kob_kollekt: "KOB kollekt",
    kob_insamling: "KOB insamling", kalender: "Kalender",
  };

  var overlay = document.getElementById("upload-overlay");
  var titleEl = document.getElementById("upload-title");
  var progressEl = document.getElementById("upload-progress");
  var detailEl = document.getElementById("upload-detail");
  var listEl = document.getElementById("upload-filelist");
  var noteEl = document.getElementById("upload-note");
  var closeEl = document.getElementById("upload-close");

  function setProgress(pct) {
    if (pct === null) progressEl.removeAttribute("value");
    else progressEl.value = pct;
  }
  function setFileStatus(el, state, text) {
    el.className = "ufile-status ufile-" + state;
    el.textContent = text;
  }

  // Ett XHR per falt. Resolvar med {ok, fel}.
  function uploadOne(input, onProgress) {
    return new Promise(function (resolve) {
      var fd = new FormData();
      fd.append(input.name, input.files[0], input.files[0].name);
      var xhr = new XMLHttpRequest();
      xhr.open("POST", form.action);
      xhr.setRequestHeader("Accept", "application/json");
      xhr.upload.addEventListener("progress", function (e) {
        if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100));
      });
      xhr.addEventListener("load", function () {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            var d = JSON.parse(xhr.responseText || "{}");
            var r = (d.resultat && d.resultat[0]) || {};
            resolve(r.ok ? { ok: true } : { ok: false, fel: r.fel || "okänt fel" });
          } catch (e) { resolve({ ok: false, fel: "svar kunde inte tolkas" }); }
        } else {
          resolve({ ok: false, fel: "serverfel " + xhr.status });
        }
      });
      xhr.addEventListener("error", function () { resolve({ ok: false, fel: "nätverksfel" }); });
      xhr.send(fd);
    });
  }

  form.addEventListener("submit", function (e) {
    var valda = Array.prototype.filter.call(
      form.querySelectorAll('input[type="file"][data-sort]'),
      function (i) { return i.files && i.files.length; });
    if (!valda.length) {
      e.preventDefault();
      alert("Välj minst en fil att ladda upp.");
      return;
    }
    e.preventDefault();

    // Bygg per-fil-lista
    listEl.textContent = "";
    var rader = valda.map(function (input) {
      var li = document.createElement("li");
      li.className = "ufile";
      var rad = document.createElement("div");
      rad.className = "ufile-rad";
      var namn = document.createElement("span");
      namn.className = "ufile-name";
      namn.textContent = ETIKETT[input.dataset.sort] + ": " + input.files[0].name;
      var status = document.createElement("span");
      status.className = "ufile-status";
      status.textContent = "väntar";
      rad.appendChild(namn); rad.appendChild(status);
      var felrad = document.createElement("div");
      felrad.className = "ufile-fel";
      felrad.hidden = true;
      li.appendChild(rad); li.appendChild(felrad);
      listEl.appendChild(li);
      return { input: input, status: status, felrad: felrad };
    });

    titleEl.textContent = "Laddar upp filer...";
    detailEl.textContent = "";
    noteEl.hidden = false;
    closeEl.hidden = true;
    setProgress(0);
    overlay.hidden = false;

    var total = valda.length, klara = 0, fel = 0, next = 0, active = 0, CONC = 3;

    function pump(resolve) {
      if (klara >= total) { resolve(); return; }
      while (active < CONC && next < total) {
        (function (rad) {
          active++;
          setFileStatus(rad.status, "uploading", "laddar upp 0%");
          uploadOne(rad.input, function (pct) {
            setFileStatus(rad.status, "uploading", "laddar upp " + pct + "%");
          }).then(function (res) {
            if (res.ok) {
              setFileStatus(rad.status, "done", "sparad");
              rad.felrad.hidden = true;
            } else {
              fel++;
              setFileStatus(rad.status, "error", "fel");
              rad.felrad.textContent = res.fel;
              rad.felrad.hidden = false;
            }
            active--; klara++;
            setProgress(Math.round((klara / total) * 100));
            pump(resolve);
          });
        })(rader[next++]);
      }
    }

    new Promise(pump).then(function () {
      setProgress(100);
      if (fel > 0) {
        titleEl.textContent = "Klart, men " + fel + " av " + total + " misslyckades";
        detailEl.textContent = (total - fel) + " fil(er) sparade. Åtgärda och ladda upp de som saknas igen.";
        closeEl.hidden = false;
      } else {
        titleEl.textContent = "Klart";
        window.location.reload();
      }
    });
  });

  if (closeEl) closeEl.addEventListener("click", function () { window.location.reload(); });
})();
