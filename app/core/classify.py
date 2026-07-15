"""Klassificering av transaktioner som kollekt eller gava via mottagarmappningen."""
from __future__ import annotations

from app.config import Kategori
from app.core.models import Transaktion
from app.core.normalize import forsamling_fran_namn, mottagare_fran_namn


def klassificera(transaktioner: list[Transaktion]) -> None:
    """Satter kategori (+forsamling/verksamhet) in-place. Okanda flaggas."""
    for t in transaktioner:
        m = mottagare_fran_namn(t.mottagarnamn)
        if m is None:
            t.omatchad_orsak = "okänd mottagare (kräver manuell klassning)"
            continue
        t.kategori = m.kategori
        if m.kategori is Kategori.KOLLEKT:
            fors = forsamling_fran_namn(t.mottagarnamn)
            t.forsamling = fors.kanoniskt if fors else t.mottagarnamn
        else:
            t.verksamhet = m.verksamhet
            t.registreringssatt = m.registreringssatt
