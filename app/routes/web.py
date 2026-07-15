"""Webbvyn: dashboard, styrd arbetsko, omatchade rader och underlagsvy."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.config import DATA_DIR, FORSAMLINGAR, MOTTAGARE, Kategori, Registreringssatt
from app.database import (
    angra,
    bekrafta,
    las_overstyrningar,
    las_sarskilda,
    skapa_overstyrning,
    skapa_sarskild,
    ta_bort_overstyrning,
    ta_bort_sarskild,
)
from app.deps import templates
from app.services.avstamning_service import kor_avstamning
from app.services.ko_service import KoVy, ladda_ko, standard_rapportfil

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
    rapporter = sorted(f.name for f in DATA_DIR.glob("*.xlsx")) if DATA_DIR.exists() else []
    if fil is None:
        return templates.TemplateResponse(request, "dashboard.html", {
            "vy": None, "rapporter": rapporter, "vald": None,
        })
    vy = ladda_ko(fil)
    total = sum((t.belopp for t in vy.resultat.rapport.transaktioner), Decimal("0"))
    return templates.TemplateResponse(request, "dashboard.html", {
        "vy": vy, "rapporter": rapporter, "vald": fil.name, "total": total,
    })


@router.get("/ko")
def arbetsko(request: Request):
    vy = _vy(request)
    return templates.TemplateResponse(request, "ko.html", {
        "vy": vy, "vald": _aktuell_fil(request).name,
    })


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
    return templates.TemplateResponse(request, "justeringar.html", {
        "vy": vy, "vald": _aktuell_fil(request).name, "period": period,
        "overstyrningar": las_overstyrningar(period),
        "sarskilda": las_sarskilda(period),
        "forsamlingar": [f.kanoniskt for f in FORSAMLINGAR],
        "manadskonton": manadskonton,
        "avst": resultat, "sar_effekt": sar_effekt,
        "ov_forsamling": ov_forsamling, "sar_verksamhet": sar_verksamhet,
        "ov_rader": ov_rader, "sar_rader": sar_rader,
    })


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
