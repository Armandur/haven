"""F-kollekt till nationell org (Act/SKUT) ska bli kollekttyp "N", ovriga F "F".

Datafritt - bygger syntetiska transaktioner. Se TASK-228.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.config import Kategori, Kollekttyp, ar_nationell_org, kollekttyp_namn
from app.core.aggregate import bygg_underlag
from app.core.models import Transaktion


def _f_tx(andamal: str, belopp: str = "100.00") -> Transaktion:
    d = date(2026, 5, 3)
    return Transaktion(
        flik="X", bokf_datum=d, trans_datum=d, valuta_datum=d,
        mottagarnummer="1", mottagarnamn="X", meddelande="", orderreferens="",
        tid=None, belopp=Decimal(belopp),
        kategori=Kategori.KOLLEKT, forsamling="Säbrå församling",
        andamal=andamal, kollekttyp=Kollekttyp.F, matchad_kalenderdatum=d,
    )


def test_ar_nationell_org():
    assert ar_nationell_org("Act Svenska kyrkan")
    assert ar_nationell_org("act svenska kyrkan")
    assert ar_nationell_org("Svenska kyrkan i utlandet")
    assert not ar_nationell_org("Diakonala hjälpfonden")
    assert not ar_nationell_org("Rikskollekt")
    assert not ar_nationell_org("")
    assert not ar_nationell_org(None)


def test_kollekttyp_namn():
    assert kollekttyp_namn("N") == "Förskollekt nationell org"
    assert kollekttyp_namn("F") == "Församlingskollekt"
    assert Kollekttyp.F.kob_namn == "Församlingskollekt"


def test_f_act_blir_n_ovriga_f():
    u = bygg_underlag(
        [_f_tx("Act Svenska kyrkan"), _f_tx("Diakonala hjälpfonden")], "2026-05")
    typer = {p.andamal: p.kollekttyp for p in u.f_poster}
    assert typer["Act Svenska kyrkan"] == "N"
    assert typer["Diakonala hjälpfonden"] == "F"
