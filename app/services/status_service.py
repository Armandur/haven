"""Statussparning: harleder tillstand per enhet (forsamling/verksamhet) ur
arbetskons bekraftelser + KOB-avstamningen. Ersatter Registreringar-matrisen.

Tillstand: ej_paborjad -> paborjad -> registrerad -> avstamd.
- registrerad: alla enhetens registreringsposter ar bekraftade i arbetskon.
- avstamd: registrerad OCH avstamningen for enheten ar ren (0 diff).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from app.services.avstamning_service import Avstamningsresultat
from app.services.ko_service import Kopost, KoVy

TILLSTAND_ETIKETT = {
    "ej_paborjad": "Ej påbörjad",
    "paborjad": "Påbörjad",
    "registrerad": "Registrerad i KOB",
    "avstamd": "Avstämd",
}


@dataclass
class Enhetsstatus:
    typ: str                     # "forsamling" | "verksamhet"
    namn: str
    antal: int
    bekraftade: int
    tillstand: str
    avstamning_ok: bool | None   # None = ingen avstamning kord
    belopp: Decimal = Decimal("0.00")

    @property
    def etikett(self) -> str:
        return TILLSTAND_ETIKETT[self.tillstand]


@dataclass
class Statusoversikt:
    forsamlingar: list[Enhetsstatus] = field(default_factory=list)
    verksamheter: list[Enhetsstatus] = field(default_factory=list)
    har_avstamning: bool = False

    def _raknare(self, enheter: list[Enhetsstatus], tillstand: str) -> int:
        return sum(1 for e in enheter if e.tillstand == tillstand)

    @property
    def sammanfattning(self) -> dict:
        alla = self.forsamlingar + self.verksamheter
        return {
            "totalt": len(alla),
            "avstamd": sum(1 for e in alla if e.tillstand == "avstamd"),
            "registrerad": sum(1 for e in alla if e.tillstand == "registrerad"),
            "paborjad": sum(1 for e in alla if e.tillstand == "paborjad"),
            "ej_paborjad": sum(1 for e in alla if e.tillstand == "ej_paborjad"),
        }


def _tillstand(antal: int, bekr: int, avstamning_ok: bool | None) -> str:
    if bekr == 0:
        return "ej_paborjad"
    if bekr < antal:
        return "paborjad"
    if avstamning_ok:
        return "avstamd"
    return "registrerad"


def _summa(poster: list[Kopost]) -> Decimal:
    return sum((p.belopp for p in poster), Decimal("0.00"))


def bygg_status(vy: KoVy, avst: Avstamningsresultat) -> Statusoversikt:
    poster = vy.poster

    # --- Forsamlingar: F-poster + de R/S-tillfallen forsamlingen ingar i ---
    f_enheter: dict[str, list[Kopost]] = {}
    for p in poster:
        if p.grupp == "F":
            f_enheter.setdefault(p.forsamling, []).append(p)
        elif p.grupp == "R/S":
            for d in p.delposter:
                f_enheter.setdefault(d.forsamling, []).append(p)

    # --- Verksamheter: gavaposter (forsamling-faltet bar verksamheten) ---
    v_enheter: dict[str, list[Kopost]] = {}
    for p in poster:
        if p.grupp == "Gåva":
            v_enheter.setdefault(p.forsamling, []).append(p)

    oversikt = Statusoversikt(har_avstamning=bool(avst.kollekt or avst.gava))

    kollekt_ren = {}
    if avst.kollekt:
        for f in avst.kollekt.forsamlingar:
            kollekt_ren[f.forsamling] = not f.har_diff
    gava_ok = {}
    if avst.gava:
        for r in avst.gava.rader:
            gava_ok[r.verksamhet] = (r.status == "ok")

    for namn in sorted(f_enheter):
        pl = f_enheter[namn]
        avok = kollekt_ren.get(namn) if avst.kollekt else None
        bekr = sum(1 for p in pl if p.bekraftad)
        belopp = Decimal("0.00")
        for p in pl:
            if p.grupp == "F":
                belopp += p.belopp
            else:  # R/S: bara forsamlingens andel, inte hela tillfallessumman
                belopp += sum((d.belopp for d in p.delposter if d.forsamling == namn),
                              Decimal("0.00"))
        oversikt.forsamlingar.append(Enhetsstatus(
            typ="forsamling", namn=namn, antal=len(pl), bekraftade=bekr,
            tillstand=_tillstand(len(pl), bekr, avok), avstamning_ok=avok,
            belopp=belopp))

    for namn in sorted(v_enheter):
        pl = v_enheter[namn]
        avok = gava_ok.get(namn) if avst.gava else None
        bekr = sum(1 for p in pl if p.bekraftad)
        oversikt.verksamheter.append(Enhetsstatus(
            typ="verksamhet", namn=namn, antal=len(pl), bekraftade=bekr,
            tillstand=_tillstand(len(pl), bekr, avok), avstamning_ok=avok,
            belopp=_summa(pl)))

    return oversikt
