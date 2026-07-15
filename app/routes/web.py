"""Webbvyn: dashboard, styrd arbetsko, omatchade rader och underlagsvy."""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.config import DATA_DIR
from app.database import angra, bekrafta
from app.deps import templates
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


@router.get("/underlag")
def underlag(request: Request):
    vy = _vy(request)
    return templates.TemplateResponse(request, "underlag.html", {
        "vy": vy, "underlag": vy.resultat.underlag, "vald": _aktuell_fil(request).name,
    })
