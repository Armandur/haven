"""Inlasning av de tva KOB-exporterna (.xls, BIFF via xlrd).

Kannetecken: datum ar Excel-serienummer, data ligger utspridd over flera blad
(ett per forsamling), och rapporten innehaller bade Kontant- och Swish 1-rader.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import xlrd

from app.core.models import KobInsamlingsrad, KobKollektrad
from app.core.normalize import forsamling_fran_namn, to_decimal


def _kolmap(sheet) -> dict[str, int]:
    return {
        str(sheet.cell_value(0, j)).strip().casefold(): j
        for j in range(sheet.ncols)
        if str(sheet.cell_value(0, j)).strip()
    }


def _col(kolmap: dict[str, int], *namn: str) -> int | None:
    for n in namn:
        if n in kolmap:
            return kolmap[n]
    return None


def _serial_datum(varde, datemode) -> date | None:
    if varde in (None, ""):
        return None
    try:
        return xlrd.xldate.xldate_as_datetime(float(varde), datemode).date()
    except (ValueError, TypeError):
        return None


def _text(sheet, i, j) -> str:
    if j is None:
        return ""
    v = sheet.cell_value(i, j)
    return "" if v is None else str(v).strip()


def _kanoniskt(ra: str) -> str:
    f = forsamling_fran_namn(ra)
    return f.kanoniskt if f else ra


def las_kob_kollekt(sokvag: str | Path) -> list[KobKollektrad]:
    sokvag = Path(sokvag)
    wb = xlrd.open_workbook(sokvag)
    ut: list[KobKollektrad] = []
    for sheet in wb.sheets():
        if sheet.nrows < 2:
            continue
        km = _kolmap(sheet)
        c_fors = _col(km, "församling")
        c_stalle = _col(km, "kollektställe")
        c_datum = _col(km, "tillfällesdatum")
        c_typ = _col(km, "kollekttyp")
        c_and = _col(km, "kollektändamål")
        c_metod = _col(km, "inbetalningsmetod")
        c_belopp = _col(km, "belopp")
        if c_fors is None or c_belopp is None:
            continue
        for i in range(1, sheet.nrows):
            ra = _text(sheet, i, c_fors)
            if not ra:
                continue
            ut.append(KobKollektrad(
                forsamling=_kanoniskt(ra),
                forsamling_ra=ra,
                kollektstalle=_text(sheet, i, c_stalle),
                tillfallesdatum=_serial_datum(
                    sheet.cell_value(i, c_datum), wb.datemode) if c_datum is not None else None,
                kollekttyp=_text(sheet, i, c_typ),
                andamal=_text(sheet, i, c_and),
                inbetalningsmetod=_text(sheet, i, c_metod),
                belopp=to_decimal(sheet.cell_value(i, c_belopp)),
                kalla=sokvag.name,
            ))
    return ut


def las_kob_insamling(sokvag: str | Path) -> list[KobInsamlingsrad]:
    sokvag = Path(sokvag)
    wb = xlrd.open_workbook(sokvag)
    ut: list[KobInsamlingsrad] = []
    for sheet in wb.sheets():
        if sheet.nrows < 2:
            continue
        km = _kolmap(sheet)
        c_fors = _col(km, "församling")
        c_mott = _col(km, "mottagare")
        c_datum = _col(km, "datum")
        c_typ = _col(km, "insamlingstyp")
        c_besk = _col(km, "typ av aktivitet / beskrivning", "beskrivning")
        c_oron = _col(km, "öronmärkning")
        c_note = _col(km, "notering")
        c_metod = _col(km, "inbetalningsmetod")
        c_belopp = _col(km, "belopp")
        if c_fors is None or c_belopp is None:
            continue
        for i in range(1, sheet.nrows):
            ra = _text(sheet, i, c_fors)
            if not ra:
                continue
            ut.append(KobInsamlingsrad(
                forsamling=_kanoniskt(ra),
                mottagare=_text(sheet, i, c_mott),
                datum=_serial_datum(
                    sheet.cell_value(i, c_datum), wb.datemode) if c_datum is not None else None,
                insamlingstyp=_text(sheet, i, c_typ),
                beskrivning=_text(sheet, i, c_besk),
                oronmarkning=_text(sheet, i, c_oron),
                notering=_text(sheet, i, c_note),
                inbetalningsmetod=_text(sheet, i, c_metod),
                belopp=to_decimal(sheet.cell_value(i, c_belopp)),
                kalla=sokvag.name,
            ))
    return ut
