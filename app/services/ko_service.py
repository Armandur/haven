"""Bygger den styrda arbetskon ur registreringsunderlaget + bekraftelsestatus.

Varje post far en stabil nyckel sa att bekraftelser overlever omrakning av
underlaget (filen las in pa nytt vid varje forfragan; berakningen ar snabb).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

from app.config import DATA_DIR, INBETALNINGSMETOD, KALENDER_FIL, Kollekttyp
from app.core.aggregate import Underlag
from app.core.models import Transaktion
from app.core.pipeline import Pipelineresultat, bearbeta, las_rapport
from app.database import (
    bekraftade_nycklar,
    las_overstyrningar,
    las_sarskilda,
    registrera_rapport,
)


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
class Sekvenspost:
    """Ett element i kollektsekvensen: forsamlingsrubrik, F-post eller R/S-break-in."""
    typ: str                         # "rubrik" | "post" | "rs"
    forsamling: str | None = None
    post: Kopost | None = None
    forts: bool = False              # rubrik aterupprepad efter en break-in


def bygg_kollekt_sekvens(poster: list[Kopost]) -> list[Sekvenspost]:
    """Kollekter ordnade per forsamling; R/S-tillfallen bryter in kronologiskt.

    F-posterna grupperas under forsamlingsrubriker (i datumordning inom varje).
    R/S-tillfallena skjuts in en gang var, pa sin datumposition, och rubriken
    aterupprepas efter en break-in sa floden blir tydligt.
    """
    f_poster = [p for p in poster if p.grupp == "F"]
    rs_poster = sorted((p for p in poster if p.grupp == "R/S"),
                       key=lambda p: (p.datum, p.typ_kod))

    # Ordna forsamlingar efter deras tidigaste tillfalle sa att break-ins landar
    # kronologiskt naturligt (forsamlingen med tidigast kollekt kommer forst).
    min_datum: dict[str, object] = {}
    for p in f_poster:
        if p.forsamling not in min_datum or p.datum < min_datum[p.forsamling]:
            min_datum[p.forsamling] = p.datum
    f_poster.sort(key=lambda p: (min_datum[p.forsamling], p.forsamling, p.datum))

    per_fors: dict[str, list[Kopost]] = {}
    for p in f_poster:
        per_fors.setdefault(p.forsamling, []).append(p)

    sekvens: list[Sekvenspost] = []
    rs_i = 0
    for fors, fposts in per_fors.items():
        rubrik_satt = False
        forsta_rubrik = True
        for post in fposts:
            while rs_i < len(rs_poster) and rs_poster[rs_i].datum <= post.datum:
                sekvens.append(Sekvenspost("rs", post=rs_poster[rs_i]))
                rs_i += 1
                rubrik_satt = False
            if not rubrik_satt:
                sekvens.append(Sekvenspost("rubrik", forsamling=fors, forts=not forsta_rubrik))
                rubrik_satt = True
                forsta_rubrik = False
            sekvens.append(Sekvenspost("post", post=post))
    while rs_i < len(rs_poster):
        sekvens.append(Sekvenspost("rs", post=rs_poster[rs_i]))
        rs_i += 1
    return sekvens


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
    def kollekt_sekvens(self) -> list[Sekvenspost]:
        return bygg_kollekt_sekvens(self.poster)

    @property
    def visningsordning(self) -> list[Kopost]:
        """Posterna i exakt den ordning arbetskon visar dem (kollekt sedan gava),
        sa att 'nasta' pekar pa det kort anvandaren faktiskt ser forst."""
        ordning = [s.post for s in self.kollekt_sekvens if s.typ in ("post", "rs")]
        ordning.extend(self.gava_poster)
        return ordning

    @property
    def nasta(self) -> Kopost | None:
        return next((p for p in self.visningsordning if not p.bekraftad), None)

    @property
    def gava_poster(self) -> list[Kopost]:
        return [p for p in self.poster if p.grupp == "Gåva"]

    @property
    def kollekt_antal(self) -> int:
        return sum(1 for p in self.poster if p.grupp in ("F", "R/S"))

    @property
    def gava_antal(self) -> int:
        return sum(1 for p in self.poster if p.grupp == "Gåva")

    @property
    def kollekt_klara(self) -> int:
        return sum(1 for p in self.poster if p.grupp in ("F", "R/S") and p.bekraftad)

    @property
    def gava_klara(self) -> int:
        return sum(1 for p in self.poster if p.grupp == "Gåva" and p.bekraftad)


def standard_rapportfil() -> Path | None:
    """Forsta .xlsx i DATA_DIR som inte ar kalendern - default att lasa in."""
    if not DATA_DIR.exists():
        return None
    for f in sorted(DATA_DIR.glob("*.xlsx")):
        if f.name != KALENDER_FIL and not f.name.startswith("."):
            return f
    return None


def bygg_export(res: Pipelineresultat) -> dict:
    """Registreringsunderlaget som JSON-struktur för KOB-userscriptet.

    En post per registreringsenhet enligt docs/KOB-INMATNING.md. Belopp som
    strängar med punkt-decimal (öresäkert); userscriptet formaterar om till KOB:s
    komma-format. KOB-specifik mappning (mottagare, kollektställe) avgörs av
    userscriptet/handläggaren - här ligger bara det Håven faktiskt vet.
    """
    rap, u = res.rapport, res.underlag
    poster: list[dict] = []

    for p in u.f_poster:
        poster.append({
            "typ": "F", "kob_flode": "kollekt", "forsamling": p.forsamling,
            "kollektstalle": None, "datum": p.datum.isoformat(),
            "andamal": p.andamal, "belopp": str(p.belopp),
            "inbetalningsmetod": INBETALNINGSMETOD,
        })
    for g in u.rs_grupper:
        poster.append({
            "typ": g.kollekttyp, "kob_flode": "kollekt_gemensam",
            "andamal": g.andamal, "datum": g.datum.isoformat(),
            "summa": str(g.summa), "inbetalningsmetod": INBETALNINGSMETOD,
            "delposter": [{"forsamling": d.forsamling, "belopp": str(d.belopp)}
                          for d in g.delposter],
        })
    for p in u.gava_manad:
        poster.append({
            "typ": "insamling_manad", "kob_flode": "insamling_gava", "kob_typ": "Gåva",
            "verksamhet": p.verksamhet, "beskrivning": p.verksamhet,
            "period": p.period, "belopp": str(p.belopp),
            "inbetalningsmetod": INBETALNINGSMETOD,
        })
    for p in u.gava_sarskilda:
        poster.append({
            "typ": "sarskild", "kob_flode": "insamling_gava",
            "kob_typ": "Insamlingsaktivitet", "verksamhet": p.verksamhet,
            "namn": p.namn, "oronmarkning": p.oronmarkning, "belopp": str(p.belopp),
            "inbetalningsmetod": INBETALNINGSMETOD,
        })
    for p in u.gava_per_andamal:
        poster.append({
            "typ": "per_andamal", "kob_flode": "insamling_gava", "kob_typ": "Gåva",
            "verksamhet": p.verksamhet, "andamal": p.andamal, "belopp": str(p.belopp),
            "inbetalningsmetod": INBETALNINGSMETOD,
        })

    return {
        "kalla": "Håven", "version": 1, "period": rap.period,
        "rapport": rap.filnamn, "inbetalningsmetod": INBETALNINGSMETOD,
        "antal_poster": len(poster), "poster": poster,
    }


def ladda_ko(swish_sokvag: str | Path) -> KoVy:
    swish_sokvag = Path(swish_sokvag)
    rapport = las_rapport(swish_sokvag)
    _registrera(swish_sokvag, rapport)
    resultat = bearbeta(
        rapport,
        overstyrningar=las_overstyrningar(rapport.period),
        sarskilda_poster=las_sarskilda(rapport.period),
    )
    return KoVy(resultat=resultat, poster=bygg_ko(resultat.underlag))


def _registrera(sokvag: Path, rapport) -> None:
    """Registrera rapporten i registret (idempotent, upsert pa filnamn)."""
    filhash = hashlib.sha256(sokvag.read_bytes()).hexdigest()
    total = sum((t.belopp for t in rapport.transaktioner), Decimal("0.00"))
    registrera_rapport(rapport.filnamn, rapport.period, filhash,
                       len(rapport.transaktioner), str(total))
