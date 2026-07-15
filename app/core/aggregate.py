"""Aggregering av klassade/matchade transaktioner till registreringsunderlag.

- F-kollekter: forsamlingsvis, en post per (forsamling, datum, andamal).
- R/S-kollekter: grupperat per tillfalle (kollekttyp, andamal, datum) med
  varje forsamlings belopp under (registreras pa ett gemensamt tillfalle i KOB).
- Gava manadssumma: en summa per verksamhet (sarskilda poster bryts ut i Fas 1).
- Gava per andamal (Gavomedelskassan): grupperas per andamal (manuellt i Fas 1).
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from app.config import Kategori, Kollekttyp, Registreringssatt
from app.core.models import Transaktion


@dataclass
class FPost:
    forsamling: str
    datum: date
    andamal: str
    belopp: Decimal
    antal: int
    transaktioner: list[Transaktion] = field(default_factory=list)
    kollekttyp: str = "F"


@dataclass
class RSDelpost:
    forsamling: str
    belopp: Decimal
    antal: int
    transaktioner: list[Transaktion] = field(default_factory=list)


@dataclass
class RSGrupp:
    kollekttyp: str          # "R" eller "S"
    andamal: str
    datum: date
    delposter: list[RSDelpost] = field(default_factory=list)

    @property
    def summa(self) -> Decimal:
        return sum((d.belopp for d in self.delposter), Decimal("0.00"))

    @property
    def antal(self) -> int:
        return sum(d.antal for d in self.delposter)


@dataclass
class GavaManadspost:
    verksamhet: str
    period: str
    belopp: Decimal
    antal: int
    transaktioner: list[Transaktion] = field(default_factory=list)


@dataclass
class GavaAndamalspost:
    verksamhet: str
    period: str
    andamal: str             # provisorisk gruppnyckel (meddelande) tills manuellt satt
    belopp: Decimal
    antal: int
    transaktioner: list[Transaktion] = field(default_factory=list)
    kraver_manuell_andamal: bool = True


@dataclass
class Underlag:
    period: str
    f_poster: list[FPost] = field(default_factory=list)
    rs_grupper: list[RSGrupp] = field(default_factory=list)
    gava_manad: list[GavaManadspost] = field(default_factory=list)
    gava_per_andamal: list[GavaAndamalspost] = field(default_factory=list)
    omatchade: list[Transaktion] = field(default_factory=list)


def _summa(txs: list[Transaktion]) -> Decimal:
    return sum((t.belopp for t in txs), Decimal("0.00"))


def bygg_underlag(transaktioner: list[Transaktion], period: str) -> Underlag:
    u = Underlag(period=period)

    f_grupp: dict[tuple, list[Transaktion]] = defaultdict(list)
    rs_grupp: dict[tuple, dict[str, list[Transaktion]]] = defaultdict(lambda: defaultdict(list))
    gava_manad: dict[str, list[Transaktion]] = defaultdict(list)
    gava_and: dict[tuple, list[Transaktion]] = defaultdict(list)

    for t in transaktioner:
        if t.omatchad_orsak:
            u.omatchade.append(t)
            continue

        if t.kategori is Kategori.KOLLEKT:
            # Registreringsenheten i KOB ar tillfallet (matchad kalenderdatum),
            # inte betalningsdatumet. En betalning dagen efter gudstjansten
            # ska folas in pa gudstjanstens tillfalle.
            tillfalle = t.matchad_kalenderdatum or t.trans_datum
            if t.kollekttyp is Kollekttyp.F:
                f_grupp[(t.forsamling, tillfalle, t.andamal)].append(t)
            elif t.kollekttyp in (Kollekttyp.R, Kollekttyp.S):
                rs_grupp[(t.kollekttyp.value, t.andamal, tillfalle)][t.forsamling].append(t)
            else:
                u.omatchade.append(t)

        elif t.kategori is Kategori.GAVA:
            if t.registreringssatt is Registreringssatt.PER_ANDAMAL:
                # Provisorisk nyckel = meddelande; handlaggaren satter ratt andamal i Fas 1.
                nyckel = t.meddelande or "(utan meddelande)"
                gava_and[(t.verksamhet, nyckel)].append(t)
            else:
                gava_manad[t.verksamhet].append(t)
        else:
            u.omatchade.append(t)

    for (fors, datum, andamal), txs in f_grupp.items():
        u.f_poster.append(FPost(fors, datum, andamal, _summa(txs), len(txs), txs))
    u.f_poster.sort(key=lambda p: (p.forsamling, p.datum, p.andamal))

    for (typ, andamal, datum), per_fors in rs_grupp.items():
        grupp = RSGrupp(kollekttyp=typ, andamal=andamal, datum=datum)
        for fors, txs in per_fors.items():
            grupp.delposter.append(RSDelpost(fors, _summa(txs), len(txs), txs))
        grupp.delposter.sort(key=lambda d: d.forsamling)
        u.rs_grupper.append(grupp)
    u.rs_grupper.sort(key=lambda g: (g.kollekttyp, g.datum, g.andamal))

    for verksamhet, txs in gava_manad.items():
        u.gava_manad.append(GavaManadspost(verksamhet, period, _summa(txs), len(txs), txs))
    u.gava_manad.sort(key=lambda p: p.verksamhet)

    for (verksamhet, nyckel), txs in gava_and.items():
        u.gava_per_andamal.append(
            GavaAndamalspost(verksamhet, period, nyckel, _summa(txs), len(txs), txs))
    u.gava_per_andamal.sort(key=lambda p: (p.verksamhet, p.andamal))

    return u
