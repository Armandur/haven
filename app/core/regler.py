"""Handlaggarregler som justerar transaktioner: andamalsoverstyrning och
sarskilda poster. Rena vardeobjekt + applikationslogik, ingen I/O eller DB.

Bada ar period-skopade och valjer transaktioner via filter (forsamling/verksamhet
+ meddelande-delstrang + datumintervall pa transaktionsdatum).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.config import Kategori, Kollekttyp
from app.core.models import Transaktion


def _matchar_filter(t: Transaktion, meddelande: str | None,
                    datum_fran: date | None, datum_till: date | None) -> bool:
    if meddelande and meddelande.casefold() not in (t.meddelande or "").casefold():
        return False
    if datum_fran and t.trans_datum < datum_fran:
        return False
    if datum_till and t.trans_datum > datum_till:
        return False
    return True


@dataclass
class Overstyrning:
    """Overstyr foreslaget andamal/typ/tillfalle for kollekter i ett urval.

    Urvalet ar antingen explicita transaktioner (tx_ids, fran radbockning) eller
    ett filter (forsamling + meddelande + datumintervall). tx_ids har foretrade.
    """
    id: int
    period: str
    forsamling: str                      # kanoniskt namn
    ny_andamal: str
    ny_typ: Kollekttyp | None = None     # None = behall matchad typ
    ny_tillfallesdatum: date | None = None   # None = behall matchat datum
    tx_ids: frozenset[str] | None = None
    meddelande_filter: str | None = None
    datum_fran: date | None = None
    datum_till: date | None = None
    orsak: str = ""

    def traffar(self, t: Transaktion) -> bool:
        if t.kategori is not Kategori.KOLLEKT:
            return False
        if self.tx_ids:
            return t.tx_id in self.tx_ids
        return (t.forsamling == self.forsamling
                and _matchar_filter(t, self.meddelande_filter,
                                    self.datum_fran, self.datum_till))


def applicera_overstyrningar(transaktioner: list[Transaktion],
                             overstyrningar: list[Overstyrning]) -> None:
    """Satter andamal/typ/matchad_kalenderdatum in-place for traffade kollekter."""
    for o in overstyrningar:
        for t in transaktioner:
            if not o.traffar(t):
                continue
            t.andamal = o.ny_andamal
            if o.ny_typ is not None:
                t.kollekttyp = o.ny_typ
            if o.ny_tillfallesdatum is not None:
                t.matchad_kalenderdatum = o.ny_tillfallesdatum
            t.overstyrd = True
            t.omatchad_orsak = None


@dataclass
class SarskildPost:
    """En utbruten post pa ett gavokonto (t.ex. loppis, konsert, ljus).

    Urvalet ar explicita tx_ids (radbockning) eller ett filter (verksamhet +
    meddelande + datumintervall). tx_ids har foretrade.
    """
    id: int
    period: str
    verksamhet: str
    namn: str
    oronmarkning: str = ""
    tx_ids: frozenset[str] | None = None
    meddelande_filter: str | None = None
    datum_fran: date | None = None
    datum_till: date | None = None

    def traffar(self, t: Transaktion) -> bool:
        if self.tx_ids:
            return t.tx_id in self.tx_ids
        return (t.verksamhet == self.verksamhet
                and _matchar_filter(t, self.meddelande_filter,
                                    self.datum_fran, self.datum_till))


def tillhor_sarskild(t: Transaktion, poster: list[SarskildPost]) -> SarskildPost | None:
    """Forsta sarskilda post vars urval traffar transaktionen (skapandeordning)."""
    for p in poster:
        if p.traffar(t):
            return p
    return None
