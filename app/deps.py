"""Delade FastAPI-beroenden. Importeras harifran, kopieras aldrig in i routes."""
from __future__ import annotations

from pathlib import Path

from fastapi.templating import Jinja2Templates

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def kr(varde) -> str:
    """Formatera belopp som svensk krontext, t.ex. '1 234,50'.

    Hart mellanslag (U+00A0) som tusentalsavgransare sa beloppet inte radbryts
    mitt i talet i smala tabellkolumner.
    """
    return f"{varde:,.2f}".replace(",", " ").replace(".", ",")


templates.env.filters["kr"] = kr
