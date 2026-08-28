"""Mottagning av uppladdade in-filer: sanering, validering och atomisk spar.

Varje fil skrivs till en temp-fil, testparsas med samma inlasare som pipelinen
anvander, och byts atomiskt till destinationen forst nar den ar giltig - sa en
trasig fil aldrig ersatter en fungerande. Per fil, sa en misslyckad uppladdning
inte forkastar redan sparade filer.

Stegvis import (slappzonen): filen stageas i data/.staging/, identifieras, och
flyttas till data/ forst vid bekraftelse. Avbrott kasserar de stagade filerna.
"""
from __future__ import annotations

import os
import re
import time
import uuid
from pathlib import Path

import xlrd

from app.config import DATA_DIR, KALENDER_FIL
from app.core.ingest_kalender import las_kalender
from app.core.ingest_kob import las_kob_insamling, las_kob_kollekt
from app.core.ingest_swish import las_swishrapport

_OTILLATNA = re.compile(r"[^\w .\-()åäöÅÄÖ]")


def _sanera(namn: str) -> str:
    namn = os.path.basename(namn or "").strip()
    namn = _OTILLATNA.sub("_", namn)
    return namn or "uppladdad"


def _validera_swish(p: Path) -> None:
    rap = las_swishrapport(p)
    if not rap.transaktioner:
        raise ValueError("inga transaktioner hittades")


def _validera_kob_kollekt(p: Path) -> None:
    if not las_kob_kollekt(p):
        raise ValueError("inga kollektrader hittades - fel exportfil?")


def _validera_kob_insamling(p: Path) -> None:
    if not las_kob_insamling(p):
        raise ValueError("inga insamlingsrader hittades - fel exportfil?")


def _validera_kalender(p: Path) -> None:
    if not las_kalender(p):
        raise ValueError("inga församlingsblad/rader hittades")


# sort -> (etikett, tillaten andelse, destinationsnamn, valideringsfunktion)
SORTER = {
    "swish": ("Swish-rapport", ".xlsx", lambda namn: namn, _validera_swish),
    "kob_kollekt": ("KOB kollektexport", ".xls",
                    lambda namn: "KOB_ParishCollectionReport_uppladdad.xls",
                    _validera_kob_kollekt),
    "kob_insamling": ("KOB insamlingsexport", ".xls",
                      lambda namn: "KOB_Accounts_Contributions_uppladdad.xls",
                      _validera_kob_insamling),
    "kalender": ("Ändamålskalender", ".xlsx", lambda namn: KALENDER_FIL,
                 _validera_kalender),
}


def ta_emot(sort: str, filnamn: str, innehall: bytes) -> str:
    """Validera och spara en uppladdad fil. Returnerar sparat filnamn.
    Kastar ValueError med begripligt svenskt meddelande vid fel."""
    spec = SORTER.get(sort)
    if spec is None:
        raise ValueError("Okänd filtyp")
    etikett, andelse, destnamn_fn, validera = spec

    sanerat = _sanera(filnamn)
    if not sanerat.lower().endswith(andelse):
        raise ValueError(f"{etikett} måste vara en {andelse}-fil")
    if not innehall:
        raise ValueError("Filen är tom")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    destnamn = destnamn_fn(sanerat)
    # Temp behaller ratt andelse (openpyxl/xlrd validerar den) och doljs med
    # punktprefix sa den inte plockas av rapport-/KOB-globbarna.
    tmp = DATA_DIR / ("._tmp_" + destnamn)
    tmp.write_bytes(innehall)
    try:
        validera(tmp)
    except Exception as e:
        tmp.unlink(missing_ok=True)
        raise ValueError(f"Kunde inte läsa {etikett}: {e}")
    tmp.replace(DATA_DIR / destnamn)   # atomisk - byter bara nar filen ar giltig
    return destnamn


# --- Stegvis import: stagea -> identifiera -> bekrafta/kassera ---------------

_TOKEN_RE = re.compile(r"^[0-9a-f]{32}$")
_STAGE_MAX_ALDER_S = 3600   # overgivna stagade filer stadas efter en timme


def _staging_dir() -> Path:
    # Harleds per anrop sa test kan peka om DATA_DIR. Punktprefixet doljer
    # katalogen for rapport-/KOB-globbarna.
    return DATA_DIR / ".staging"


def _identifiera_xls(p: Path) -> str | None:
    """Skilj KOB-exporterna pa sarskiljande kolumner. Bada inlasarna nojer sig
    med 'församling'+'belopp', sa en kollektfil skulle aven parsa som
    insamlingsfil - darfor gar identifieringen pa rubrikraden i stallet."""
    try:
        wb = xlrd.open_workbook(p)
    except Exception:
        return None
    for sheet in wb.sheets():
        if sheet.nrows < 1:
            continue
        kolumner = {
            str(sheet.cell_value(0, j)).strip().casefold()
            for j in range(sheet.ncols)
        }
        if "kollektändamål" in kolumner or "kollektställe" in kolumner:
            return "kob_kollekt"
        if "insamlingstyp" in kolumner or "öronmärkning" in kolumner:
            return "kob_insamling"
    return None


def identifiera(p: Path, filnamn: str) -> str | None:
    """Gissa sort for en uppladdad fil, eller None om den inte kanns igen.

    Swish provas fore kalender: ett swishblad vars fliknamn rakar matcha en
    kortkod skulle kunna ge kalenderrader, medan kalendern aldrig parsar som
    swish (saknar Bokforingsdatum-rubrik)."""
    namn = filnamn.casefold()
    if namn.endswith(".xls"):
        return _identifiera_xls(p)
    if namn.endswith(".xlsx"):
        for sort in ("swish", "kalender"):
            try:
                SORTER[sort][3](p)
                return sort
            except Exception:
                continue
    return None


def stagea(filnamn: str, innehall: bytes) -> dict:
    """Spara en uppladdad fil i staging och forsok identifiera sorten.
    Returnerar {token, filnamn, sort} dar sort ar None om oidentifierad."""
    if not innehall:
        raise ValueError("Filen är tom")
    sanerat = _sanera(filnamn)
    if not sanerat.casefold().endswith((".xls", ".xlsx")):
        raise ValueError("Endast .xls- och .xlsx-filer kan importeras")
    katalog = _staging_dir()
    katalog.mkdir(parents=True, exist_ok=True)
    _stada_staging(katalog)
    token = uuid.uuid4().hex
    p = katalog / f"{token}__{sanerat}"
    p.write_bytes(innehall)
    return {"token": token, "filnamn": sanerat, "sort": identifiera(p, sanerat)}


def _stagad_fil(token: str) -> Path:
    if not _TOKEN_RE.match(token or ""):
        raise ValueError("Ogiltig filreferens")
    traffar = list(_staging_dir().glob(f"{token}__*"))
    if not traffar:
        raise ValueError("Filen finns inte längre - ladda upp den igen")
    return traffar[0]


def bekrafta_stagad(token: str, sort: str) -> str:
    """Validera en stagad fil som vald sort och flytta den till data/.
    Vid valideringsfel ligger filen kvar i staging sa sorten kan andras."""
    spec = SORTER.get(sort)
    if spec is None:
        raise ValueError("Okänd filtyp")
    etikett, andelse, destnamn_fn, validera = spec
    p = _stagad_fil(token)
    filnamn = p.name.split("__", 1)[1]
    if not filnamn.casefold().endswith(andelse):
        raise ValueError(f"{etikett} måste vara en {andelse}-fil")
    try:
        validera(p)
    except Exception as e:
        raise ValueError(f"Kunde inte läsa som {etikett}: {e}")
    destnamn = destnamn_fn(filnamn)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    p.replace(DATA_DIR / destnamn)
    return destnamn


def kassera_stagad(token: str) -> None:
    try:
        _stagad_fil(token).unlink(missing_ok=True)
    except ValueError:
        pass   # redan borta eller ogiltig referens - inget att stada


def _stada_staging(katalog: Path) -> None:
    granstid = time.time() - _STAGE_MAX_ALDER_S
    for p in katalog.glob("*__*"):
        try:
            if p.stat().st_mtime < granstid:
                p.unlink(missing_ok=True)
        except OSError:
            pass
