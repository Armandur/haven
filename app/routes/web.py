"""Webbvyn: dashboard, styrd arbetsko, omatchade rader och underlagsvy."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse

from app.config import (
    DATA_DIR,
    FORSAMLINGAR,
    KALENDER_FIL,
    MOTTAGARE,
    Kategori,
    Registreringssatt,
)
from app.database import (
    angra,
    bekrafta,
    las_forsamlingar_konfig,
    las_historik,
    las_mottagare_konfig,
    las_overstyrningar,
    las_rapporter,
    las_sarskilda,
    rapport_andrad,
    skapa_overstyrning,
    skapa_sarskild,
    spara_forsamling_alias,
    spara_mottagare,
    ta_bort_mottagare,
    ta_bort_overstyrning,
    ta_bort_sarskild,
    uppdatera_overstyrning,
)
from app.core.regler import Overstyrning, SarskildPost
from app.services.import_service import ta_emot
from app.services.konfig_service import ladda_konfig_till_minne
from app.deps import templates
from app.services.avstamning_service import kor_avstamning
from app.services.ko_service import KoVy, bygg_export, ladda_ko, standard_rapportfil
from app.services.status_service import bygg_status

router = APIRouter()


def _aktuell_fil(request: Request) -> Path | None:
    namn = request.query_params.get("fil")
    if namn:
        p = DATA_DIR / namn
        if p.exists():
            return p
    return standard_rapportfil()


def _vy(request: Request) -> KoVy:
    fil = _aktuell_fil(request)
    if fil is None:
        raise HTTPException(404, "Ingen Swish-rapport hittades i data-katalogen.")
    return ladda_ko(fil)


@router.get("/")
def dashboard(request: Request):
    fil = _aktuell_fil(request)
    rapporter = sorted(
        f.name for f in DATA_DIR.glob("*.xlsx")
        if f.name != KALENDER_FIL and not f.name.startswith(".")
    ) if DATA_DIR.exists() else []
    if fil is None:
        return templates.TemplateResponse(request, "dashboard.html", {
            "vy": None, "rapporter": rapporter, "vald": None,
        })
    vy = ladda_ko(fil)   # registrerar rapporten i registret
    total = sum((t.belopp for t in vy.resultat.rapport.transaktioner), Decimal("0"))
    return templates.TemplateResponse(request, "dashboard.html", {
        "vy": vy, "rapporter": rapporter, "vald": fil.name, "total": total,
        "registrerade": las_rapporter(), "andrad": rapport_andrad(fil.name),
    })


@router.post("/import")
async def importera(
    request: Request,
    swish: UploadFile | None = File(None),
    kob_kollekt: UploadFile | None = File(None),
    kob_insamling: UploadFile | None = File(None),
    kalender: UploadFile | None = File(None),
):
    resultat = []
    for sort, up in (("swish", swish), ("kob_kollekt", kob_kollekt),
                     ("kob_insamling", kob_insamling), ("kalender", kalender)):
        if up is None or not up.filename:
            continue
        innehall = await up.read()
        try:
            namn = ta_emot(sort, up.filename, innehall)
            resultat.append({"sort": sort, "filnamn": namn, "ok": True})
        except ValueError as e:
            resultat.append({"sort": sort, "filnamn": up.filename, "ok": False,
                             "fel": str(e)})
    if "application/json" in request.headers.get("accept", ""):
        return JSONResponse({"resultat": resultat})
    return RedirectResponse("/", status_code=302)


@router.get("/ko")
def arbetsko(request: Request):
    vy = _vy(request)
    return templates.TemplateResponse(request, "ko.html", {
        "vy": vy, "vald": _aktuell_fil(request).name,
    })


@router.get("/ko/export.json")
def ko_export(request: Request):
    vy = _vy(request)
    return JSONResponse(bygg_export(vy.resultat))


_USERSCRIPT_DIR = Path(__file__).resolve().parents[2] / "userscript"
_USERSCRIPT_FIL = _USERSCRIPT_DIR / "haven-kob.user.js"
_TEST_UNDERLAG_FIL = _USERSCRIPT_DIR / "test-underlag-utb.json"


@router.get("/kob-userscript.user.js")
def kob_userscript():
    """Serverar KOB-userscriptet. .user.js-suffixet gör att Tampermonkey/
    Violentmonkey fångar navigeringen och erbjuder installation direkt."""
    if not _USERSCRIPT_FIL.exists():
        raise HTTPException(status_code=404, detail="Userscriptet saknas.")
    return FileResponse(_USERSCRIPT_FIL, media_type="text/javascript",
                        filename="haven-kob.user.js", content_disposition_type="inline")


@router.get("/kob-test-underlag.json")
def kob_test_underlag():
    """Testunderlag för KOB-utbildningsmiljön (Östervåla-Harbo). Peka
    userscriptets 'Hämta från Håven'-URL hit för att testa utan skarp data."""
    if not _TEST_UNDERLAG_FIL.exists():
        raise HTTPException(status_code=404, detail="Testunderlaget saknas.")
    return FileResponse(_TEST_UNDERLAG_FIL, media_type="application/json",
                        content_disposition_type="inline")


@router.post("/ko/bekrafta")
async def ko_bekrafta(request: Request, nyckel: str = Form(...), period: str = Form(...)):
    bekrafta(nyckel, period)
    return await _ko_svar(request, nyckel)


@router.post("/ko/angra")
async def ko_angra(request: Request, nyckel: str = Form(...), period: str = Form(...)):
    angra(nyckel)
    return await _ko_svar(request, nyckel)


async def _ko_svar(request: Request, nyckel: str):
    """JSON for fetch (progressiv async), redirect for formularpost utan JS."""
    if request.headers.get("x-requested-with") == "fetch":
        vy = _vy(request)
        post = next((p for p in vy.poster if p.nyckel == nyckel), None)
        return JSONResponse({
            "nyckel": nyckel,
            "bekraftad": bool(post and post.bekraftad),
            "klara": vy.klara,
            "totalt": vy.totalt,
        })
    fil = _aktuell_fil(request)
    return RedirectResponse(f"/ko?fil={fil.name}", status_code=302)


@router.get("/status")
def status(request: Request):
    vy = _vy(request)
    avst = kor_avstamning(vy.resultat)
    oversikt = bygg_status(vy, avst)
    return templates.TemplateResponse(request, "status.html", {
        "vy": vy, "vald": _aktuell_fil(request).name,
        "oversikt": oversikt, "avst": avst,
    })


@router.get("/konfig")
def konfig(request: Request):
    return templates.TemplateResponse(request, "konfig.html", {
        "vald": request.query_params.get("fil"),
        "mottagare": las_mottagare_konfig(endast_aktiva=False),
        "forsamlingar": las_forsamlingar_konfig(),
        "forhandsvald_namn": request.query_params.get("namn", ""),
    })


def _redir_konfig(request: Request):
    fil = request.query_params.get("fil")
    suffix = f"?fil={fil}" if fil else ""
    return RedirectResponse(f"/konfig{suffix}", status_code=302)


@router.post("/konfig/mottagare/spara")
async def spara_mottagare_route(
    request: Request,
    namn: str = Form(...), kategori: str = Form(...), verksamhet: str = Form(""),
    registreringssatt: str = Form(""), aktiv: str = Form("on"),
):
    if kategori == "kollekt":
        verksamhet, registreringssatt = "", ""
    spara_mottagare(namn.strip(), kategori, verksamhet.strip(),
                    registreringssatt, 1 if aktiv else 0)
    ladda_konfig_till_minne()
    return _redir_konfig(request)


@router.post("/konfig/mottagare/tabort")
async def tabort_mottagare_route(request: Request, namn: str = Form(...)):
    ta_bort_mottagare(namn)
    ladda_konfig_till_minne()
    return _redir_konfig(request)


@router.post("/konfig/forsamling/alias")
async def spara_alias_route(request: Request, kanoniskt: str = Form(...),
                            alias: str = Form("")):
    spara_forsamling_alias(kanoniskt, alias.split(","))
    ladda_konfig_till_minne()
    return _redir_konfig(request)


@router.get("/kalender")
def kalender_vy(request: Request):
    from app.core.ingest_kalender import las_kalender
    kalfil = DATA_DIR / KALENDER_FIL
    finns = kalfil.exists()
    grupper: dict = {}
    if finns:
        for r in las_kalender(kalfil):
            grupper.setdefault(r.forsamling, []).append(r)
    fil = _aktuell_fil(request)
    return templates.TemplateResponse(request, "kalender.html", {
        "vald": fil.name if fil else None,
        "grupper": grupper, "kalenderfil": KALENDER_FIL, "finns": finns,
    })


@router.get("/omatchade")
def omatchade(request: Request):
    vy = _vy(request)
    return templates.TemplateResponse(request, "omatchade.html", {
        "vy": vy, "vald": _aktuell_fil(request).name,
    })


@router.get("/avstamning")
def avstamning(request: Request):
    vy = _vy(request)
    resultat = kor_avstamning(vy.resultat)
    return templates.TemplateResponse(request, "avstamning.html", {
        "vy": vy, "avst": resultat, "vald": _aktuell_fil(request).name,
    })


@router.get("/justeringar")
def justeringar(request: Request):
    vy = _vy(request)
    period = vy.resultat.rapport.period
    txs = vy.resultat.rapport.transaktioner
    manadskonton = [m.verksamhet for m in MOTTAGARE
                    if m.kategori is Kategori.GAVA
                    and m.registreringssatt is Registreringssatt.MANADSSUMMA]

    ov_forsamling = request.query_params.get("ov_forsamling") or ""
    sar_verksamhet = request.query_params.get("sar_verksamhet") or ""
    ov_rader = sorted(
        (t for t in txs if t.kategori is Kategori.KOLLEKT and t.forsamling == ov_forsamling),
        key=lambda t: (t.trans_datum, t.tid or datetime.min.time())
    ) if ov_forsamling else []
    sar_rader = sorted(
        (t for t in txs if t.kategori is Kategori.GAVA and t.verksamhet == sar_verksamhet),
        key=lambda t: (t.trans_datum, t.tid or datetime.min.time())
    ) if sar_verksamhet else []

    resultat = kor_avstamning(vy.resultat)
    sar_effekt = {p.sarskild_post_id: p for p in vy.resultat.underlag.gava_sarskilda}
    overstyrningar = las_overstyrningar(period)
    redigera_ov = request.query_params.get("redigera_ov")
    ov_redigera = next((o for o in overstyrningar if str(o.id) == redigera_ov), None)
    return templates.TemplateResponse(request, "justeringar.html", {
        "vy": vy, "vald": _aktuell_fil(request).name, "period": period,
        "overstyrningar": overstyrningar, "ov_redigera": ov_redigera,
        "sarskilda": las_sarskilda(period),
        "forsamlingar": [f.kanoniskt for f in FORSAMLINGAR],
        "manadskonton": manadskonton,
        "avst": resultat, "sar_effekt": sar_effekt,
        "ov_forsamling": ov_forsamling, "sar_verksamhet": sar_verksamhet,
        "ov_rader": ov_rader, "sar_rader": sar_rader,
        "historik": [(h, _historik_berorda(h, txs)) for h in las_historik(period)],
    })


def _historik_berorda(h, transaktioner: list):
    """Slar upp vilka transaktioner en historikpost gallde (tx_ids eller filter)."""
    if h.typ == "overstyrning":
        regel = Overstyrning(id=0, period=h.period, forsamling=h.scope, ny_andamal="",
                             tx_ids=h.tx_ids, meddelande_filter=h.meddelande_filter,
                             datum_fran=h.datum_fran, datum_till=h.datum_till)
    else:
        regel = SarskildPost(id=0, period=h.period, verksamhet=h.scope, namn="",
                             tx_ids=h.tx_ids, meddelande_filter=h.meddelande_filter,
                             datum_fran=h.datum_fran, datum_till=h.datum_till)
    return [t for t in transaktioner if regel.traffar(t)]


def _redir_justeringar(request: Request):
    fil = _aktuell_fil(request)
    return RedirectResponse(f"/justeringar?fil={fil.name}", status_code=302)


@router.post("/justeringar/overstyrning/skapa")
async def skapa_overstyrning_route(
    request: Request,
    period: str = Form(...), forsamling: str = Form(""), ny_andamal: str = Form(...),
    ny_typ: str = Form(""), ny_tillfallesdatum: str = Form(""),
    tx_ids: list[str] = Form(default=[]),
    meddelande_filter: str = Form(""), datum_fran: str = Form(""),
    datum_till: str = Form(""), orsak: str = Form(""),
):
    skapa_overstyrning(period, forsamling, ny_andamal, ny_typ, ny_tillfallesdatum,
                       tx_ids, meddelande_filter, datum_fran, datum_till, orsak)
    return _redir_justeringar(request)


@router.post("/justeringar/overstyrning/uppdatera")
async def uppdatera_overstyrning_route(
    request: Request, id: int = Form(...), ny_andamal: str = Form(...),
    ny_typ: str = Form(""), ny_tillfallesdatum: str = Form(""), orsak: str = Form(""),
):
    uppdatera_overstyrning(id, ny_andamal, ny_typ, ny_tillfallesdatum, orsak)
    return _redir_justeringar(request)


@router.post("/justeringar/overstyrning/tabort")
async def tabort_overstyrning_route(request: Request, id: int = Form(...)):
    ta_bort_overstyrning(id)
    return _redir_justeringar(request)


@router.post("/justeringar/sarskild/skapa")
async def skapa_sarskild_route(
    request: Request,
    period: str = Form(...), verksamhet: str = Form(...), namn: str = Form(...),
    oronmarkning: str = Form(""), tx_ids: list[str] = Form(default=[]),
    meddelande_filter: str = Form(""),
    datum_fran: str = Form(""), datum_till: str = Form(""),
):
    skapa_sarskild(period, verksamhet, namn, oronmarkning, tx_ids,
                   meddelande_filter, datum_fran, datum_till)
    return _redir_justeringar(request)


@router.post("/justeringar/sarskild/tabort")
async def tabort_sarskild_route(request: Request, id: int = Form(...)):
    ta_bort_sarskild(id)
    return _redir_justeringar(request)


@router.get("/underlag")
def underlag(request: Request):
    vy = _vy(request)
    return templates.TemplateResponse(request, "underlag.html", {
        "vy": vy, "underlag": vy.resultat.underlag, "vald": _aktuell_fil(request).name,
    })
