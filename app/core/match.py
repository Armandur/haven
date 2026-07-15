"""Andamalsmatchning for kollekter via framatfyllningsregeln (spec 6.3).

For en kollekttransaktion till forsamling P med transaktionsdatum D galler
andamalet for den kalenderrad dar Datum = max(Datum <= D). Andamalet galler
framat tills nasta tillfalle. Omatchat flaggas, slaps aldrig tyst.
"""
from __future__ import annotations

from bisect import bisect_right
from collections import defaultdict
from datetime import date

from app.config import Kategori
from app.core.models import Kalenderrad, Transaktion


class Kalenderindex:
    """Per forsamling: sorterade datum + rader for snabb max(<=D)-uppslagning."""

    def __init__(self, rader: list[Kalenderrad]):
        self._datum: dict[str, list[date]] = defaultdict(list)
        self._rad: dict[str, list[Kalenderrad]] = defaultdict(list)
        for r in sorted(rader, key=lambda x: x.datum):
            self._datum[r.forsamling].append(r.datum)
            self._rad[r.forsamling].append(r)

    def har_forsamling(self, forsamling: str) -> bool:
        return forsamling in self._datum

    def slå_upp(self, forsamling: str, d: date) -> Kalenderrad | None:
        datum = self._datum.get(forsamling)
        if not datum:
            return None
        pos = bisect_right(datum, d)
        if pos == 0:
            return None  # betalning fore forsta tillfallet
        return self._rad[forsamling][pos - 1]


def matcha_andamal(transaktioner: list[Transaktion], index: Kalenderindex) -> None:
    """Satter andamal/kollekttyp/matchad_kalenderdatum in-place for kollekter."""
    for t in transaktioner:
        if t.kategori is not Kategori.KOLLEKT or t.forsamling is None:
            continue
        if not index.har_forsamling(t.forsamling):
            t.omatchad_orsak = f"ingen kalender för {t.forsamling}"
            continue
        rad = index.slå_upp(t.forsamling, t.trans_datum)
        if rad is None:
            t.omatchad_orsak = "betalning före första kollekttillfället"
            continue
        t.matchad_kalenderdatum = rad.datum
        t.kollekttyp = rad.typ
        t.andamal = rad.andamal or None
        if not rad.andamal:
            t.omatchad_orsak = (
                f"ändamål saknas i kalendern för {rad.datum:%Y-%m-%d}"
            )
        elif rad.typ is None:
            t.omatchad_orsak = (
                f"kollekttyp (F/R/S) saknas i kalendern för {rad.datum:%Y-%m-%d}"
            )
