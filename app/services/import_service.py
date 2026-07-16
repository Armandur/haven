"""Mottagning av uppladdade in-filer: sanering, validering och atomisk spar.

Varje fil skrivs till en temp-fil, testparsas med samma inlasare som pipelinen
anvander, och byts atomiskt till destinationen forst nar den ar giltig - sa en
trasig fil aldrig ersatter en fungerande. Per fil, sa en misslyckad uppladdning
inte forkastar redan sparade filer.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

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
