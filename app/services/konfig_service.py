"""Laddar den redigerbara konfigurationen (forsamlingar/mottagare) fran SQLite
in i namnnormaliseringen. Anropas vid appstart och efter varje konfigandring.
"""
from __future__ import annotations

from app.core import normalize
from app.database import las_forsamlingar_konfig, las_mottagare_konfig


def ladda_konfig_till_minne() -> None:
    normalize.satt_konfig(las_forsamlingar_konfig(), las_mottagare_konfig())
