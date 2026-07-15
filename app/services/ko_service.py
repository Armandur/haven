"""Bygger den styrda arbetskon ur registreringsunderlaget + bekraftelsestatus.

Varje post far en stabil nyckel sa att bekraftelser overlever omrakning av
underlaget (filen las in pa nytt vid varje forfragan; berakningen ar snabb).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

from app.config import DATA_DIR, INBETALNINGSMETOD, KALENDER_FIL, Kollekttyp
from app.core.aggregate import Underlag
from app.core.models import Transaktion
from app.core.pipeline import Pipelineresultat, bearbeta, las_rapport
from app.database import bekraftade_nycklar, las_overstyrningar, las_sarskilda


@dataclass
class Delpost:
    forsamling: str
    belopp: Decimal
    antal: int
    transaktioner: list[Transaktion] = field(default_factory=list)


@dataclass
class Kopost:
    nyckel: str
    grupp: str                       # "F" | "R/S" | "Gåva"
    typ_kod: str                     # "F" | "R" | "S" | "gava" (for fargkod)
    typ_etikett: str                 # KOB-kollekttyp eller registreringssatt
    rubrik: str
    belopp: Decimal
    antal: int
    forsamling: str | None = None
    datum: date | None = None
    andamal: str | None = None
    period: str | None = None
    inbetalningsmetod: str = INBETALNINGSMETOD
    delposter: list[Delpost] = field(default_factory=list)
    transaktioner: list[Transaktion] = field(default_factory=list)
    bekraftad: bool = False
    kraver_manuell_andamal: bool = False


def _f_nyckel(forsamling, datum, andamal) -> str:
    return f"F|{forsamling}|{datum:%Y-%m-%d}|{andamal}"


def _rs_nyckel(typ, datum, andamal) -> str:
    return f"{typ}|{datum:%Y-%m-%d}|{andamal}"


def _gm_nyckel(verksamhet, period) -> str:
    return f"GM|{verksamhet}|{period}"


def _ga_nyckel(verksamhet, andamal) -> str:
    return f"GA|{verksamhet}|{andamal}"


def _sar_nyckel(sarskild_post_id) -> str:
    return f"SAR|{sarskild_post_id}"


def bygg_ko(underlag: Underlag) -> list[Kopost]:
    bekr = bekraftade_nycklar(underlag.period)
    poster: list[Kopost] = []

    for p in underlag.f_poster:
        nyckel = _f_nyckel(p.forsamling, p.datum, p.andamal)
        poster.append(Kopost(
            nyckel=nyckel, grupp="F", typ_kod="F", typ_etikett=Kollekttyp.F.kob_namn,
            rubrik=f"{p.forsamling} - {p.datum:%Y-%m-%d}",
            belopp=p.belopp, antal=p.antal, forsamling=p.forsamling,
            datum=p.datum, andamal=p.andamal, bekraftad=nyckel in bekr,
            transaktioner=p.transaktioner,
        ))

    for g in underlag.rs_grupper:
        typ = Kollekttyp(g.kollekttyp)
        nyckel = _rs_nyckel(g.kollekttyp, g.datum, g.andamal)
        delposter = [Delpost(d.forsamling, d.belopp, d.antal, d.transaktioner)
                     for d in g.delposter]
        poster.append(Kopost(
            nyckel=nyckel, grupp="R/S", typ_kod=g.kollekttyp, typ_etikett=typ.kob_namn,
            rubrik=f"{typ.kob_namn} - {g.datum:%Y-%m-%d}",
            belopp=g.summa, antal=g.antal, datum=g.datum, andamal=g.andamal,
            delposter=delposter, bekraftad=nyckel in bekr,
            transaktioner=[t for d in delposter for t in d.transaktioner],
        ))

    for p in underlag.gava_manad:
        nyckel = _gm_nyckel(p.verksamhet, p.period)
        poster.append(Kopost(
            nyckel=nyckel, grupp="Gåva", typ_kod="gava", typ_etikett="Insamling (månadssumma)",
            rubrik=f"{p.verksamhet} - {p.period}",
            belopp=p.belopp, antal=p.antal, forsamling=p.verksamhet,
            period=p.period, bekraftad=nyckel in bekr,
            transaktioner=p.transaktioner,
        ))

    for p in underlag.gava_per_andamal:
        nyckel = _ga_nyckel(p.verksamhet, p.andamal)
        poster.append(Kopost(
            nyckel=nyckel, grupp="Gåva", typ_kod="gava", typ_etikett="Insamling (per ändamål)",
            rubrik=f"{p.verksamhet} - {p.andamal}",
            belopp=p.belopp, antal=p.antal, forsamling=p.verksamhet,
            andamal=p.andamal, period=p.period, bekraftad=nyckel in bekr,
            kraver_manuell_andamal=p.kraver_manuell_andamal,
            transaktioner=p.transaktioner,
        ))

    for p in underlag.gava_sarskilda:
        nyckel = _sar_nyckel(p.sarskild_post_id)
        poster.append(Kopost(
            nyckel=nyckel, grupp="Gåva", typ_kod="gava", typ_etikett="Särskild post",
            rubrik=f"{p.verksamhet} - {p.namn}",
            belopp=p.belopp, antal=p.antal, forsamling=p.verksamhet,
            andamal=p.oronmarkning or p.namn, period=p.period,
            bekraftad=nyckel in bekr, transaktioner=p.transaktioner,
        ))

    return poster


@dataclass
class KoVy:
    resultat: Pipelineresultat
    poster: list[Kopost]

    @property
    def klara(self) -> int:
        return sum(1 for p in self.poster if p.bekraftad)

    @property
    def totalt(self) -> int:
        return len(self.poster)

    @property
    def nasta(self) -> Kopost | None:
        return next((p for p in self.poster if not p.bekraftad), None)


def standard_rapportfil() -> Path | None:
    """Forsta .xlsx i DATA_DIR som inte ar kalendern - default att lasa in."""
    if not DATA_DIR.exists():
        return None
    for f in sorted(DATA_DIR.glob("*.xlsx")):
        if f.name != KALENDER_FIL:
            return f
    return None


def ladda_ko(swish_sokvag: str | Path) -> KoVy:
    rapport = las_rapport(swish_sokvag)
    resultat = bearbeta(
        rapport,
        overstyrningar=las_overstyrningar(rapport.period),
        sarskilda_poster=las_sarskilda(rapport.period),
    )
    return KoVy(resultat=resultat, poster=bygg_ko(resultat.underlag))
