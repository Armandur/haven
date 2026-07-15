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
