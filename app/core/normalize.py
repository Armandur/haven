"""Namnnormalisering: ravarden ur olika kallor -> kanoniska begrepp."""
from __future__ import annotations

import re
from decimal import Decimal, ROUND_HALF_UP

from app.config import FORSAMLINGAR, MOTTAGARE, Forsamling, Mottagare

_WS = re.compile(r"\s+")


def _nyckel(s: str | None) -> str:
    """Normaliserad jamforelsenyckel: trim, kollapsa mellanslag, casefold."""
    return _WS.sub(" ", (s or "").strip()).casefold()


# Uppslagstabeller. Byggs om via satt_konfig() (fran DB vid appstart), och
# initieras har med frodata sa att ren anvandning (tester, CLI) funkar utan DB.
_FORS_LOOKUP: dict[str, Forsamling] = {}
_KORTKOD_LOOKUP: dict[str, Forsamling] = {}
_MOTT_LOOKUP: dict[str, Mottagare] = {}


def satt_konfig(forsamlingar: tuple[Forsamling, ...],
                mottagare: tuple[Mottagare, ...]) -> None:
    """Bygg om namnuppslagen fran given konfig (kanoniska namn, alias, mottagare)."""
    _FORS_LOOKUP.clear()
    _KORTKOD_LOOKUP.clear()
    _MOTT_LOOKUP.clear()
    for f in forsamlingar:
        _FORS_LOOKUP[_nyckel(f.kanoniskt)] = f
        _KORTKOD_LOOKUP[f.kortkod] = f
        for a in f.alias:
            _FORS_LOOKUP[_nyckel(a)] = f
    for m in mottagare:
        _MOTT_LOOKUP[_nyckel(m.namn)] = m


satt_konfig(FORSAMLINGAR, MOTTAGARE)


def forsamling_fran_namn(namn: str | None) -> Forsamling | None:
    return _FORS_LOOKUP.get(_nyckel(namn))


def forsamling_fran_kortkod(kortkod: str) -> Forsamling | None:
    return _KORTKOD_LOOKUP.get(kortkod.strip().upper())


def mottagare_fran_namn(namn: str | None) -> Mottagare | None:
    return _MOTT_LOOKUP.get(_nyckel(namn))


def normalisera_andamal(s: str | None) -> str:
    """Jamforelsenyckel for andamalstext mellan kalender och KOB.

    Kalendern skriver t.ex. 'Svenska Kyrkans Unga ½, SALT, barn och unga i EFS ½'
    dar KOB har 'Svenska Kyrkans Unga / SALT, barn och unga i EFS'. Vi tar bort
    andelstecken och skiljetecken och jamfor pa ordinnehallet.
    """
    t = (s or "").casefold()
    for tecken in ("½", "¼", "¾", "/", ",", ".", "-"):
        t = t.replace(tecken, " ")
    return _WS.sub(" ", t).strip()


def to_decimal(varde) -> Decimal:
    """Belopp -> Decimal med tva decimaler (oren), utan float-drift."""
    if varde is None or varde == "":
        return Decimal("0.00")
    d = Decimal(str(varde))
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
