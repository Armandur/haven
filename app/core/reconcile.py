"""KOB-avstamning: jamfor Swish-underlaget mot KOB-exporterna.

Kollekt jamfors per (forsamling, tillfallesdatum) - den avgorande nivan enligt
spec 8.6 - och nettas per forsamling. Endast KOB:s Swish 1-rader jamfors, eftersom
Swish-rapporten bara innehaller Swish. Gava jamfors per verksamhet/konto.

Andamalstext skiljer sig ofta mellan kalender och KOB; belopp och datum ar de
palitliga nycklarna, andamalstexten visas som kontext med mjuk varning nar den
skiljer (se normalisera_andamal).
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from app.config import GAVA_NYCKELORD, Kategori, Kollekttyp
from app.core.aggregate import Underlag
from app.core.models import KobInsamlingsrad, KobKollektrad, Transaktion
from app.core.normalize import normalisera_andamal

SWISH_METOD = "Swish 1"


# --- Kollektavstamning ------------------------------------------------------

@dataclass
class AvstamRad:
    forsamling: str
    datum: date | None
    swish_andamal: str
    kob_andamal: str
    kollekttyp: str                  # "F" | "R" | "S" | ""
    swish: Decimal
    kob: Decimal
    diff: Decimal                    # swish - kob
    status: str                      # "ok" | "diff" | "notis"
    orsak: str = ""


@dataclass
class ForsamlingAvstamning:
    forsamling: str
    rader: list[AvstamRad] = field(default_factory=list)

    @property
    def swish_total(self) -> Decimal:
        return sum((r.swish for r in self.rader), Decimal("0.00"))

    @property
    def kob_total(self) -> Decimal:
        return sum((r.kob for r in self.rader), Decimal("0.00"))

    @property
    def diff(self) -> Decimal:
        return self.swish_total - self.kob_total

    @property
    def har_diff(self) -> bool:
        return any(r.status == "diff" for r in self.rader)


@dataclass
class KollektAvstamning:
    forsamlingar: list[ForsamlingAvstamning] = field(default_factory=list)

    @property
    def swish_total(self) -> Decimal:
        return sum((f.swish_total for f in self.forsamlingar), Decimal("0.00"))

    @property
    def kob_total(self) -> Decimal:
        return sum((f.kob_total for f in self.forsamlingar), Decimal("0.00"))

    @property
    def antal_diffar(self) -> int:
        return sum(1 for f in self.forsamlingar for r in f.rader if r.status == "diff")


def _typ_bokstav(typ_set: set) -> str:
    for t in ("S", "R", "F"):
        if t in typ_set:
            return t
    return ""


def avstam_kollekt(transaktioner: list[Transaktion],
                   kob_rader: list[KobKollektrad]) -> KollektAvstamning:
    # Swish-sidan: matchade kollekter, nyckel (forsamling, tillfallesdatum).
    swish: dict[tuple, dict] = defaultdict(
        lambda: {"belopp": Decimal("0.00"), "andamal": set(), "typ": set()})
    for t in transaktioner:
        if t.kategori is not Kategori.KOLLEKT or t.omatchad_orsak:
            continue
        datum = t.matchad_kalenderdatum or t.trans_datum
        d = swish[(t.forsamling, datum)]
        d["belopp"] += t.belopp
        if t.andamal:
            d["andamal"].add(t.andamal)
        if t.kollekttyp:
            d["typ"].add(t.kollekttyp.value)

    # KOB-sidan: bara Swish 1-rader, nyckel (forsamling, tillfallesdatum).
    kob: dict[tuple, dict] = defaultdict(
        lambda: {"belopp": Decimal("0.00"), "andamal": set(), "typ": set()})
    for r in kob_rader:
        if r.inbetalningsmetod.strip() != SWISH_METOD:
            continue
        d = kob[(r.forsamling, r.tillfallesdatum)]
        d["belopp"] += r.belopp
        if r.andamal:
            d["andamal"].add(r.andamal)
        if r.kollekttyp:
            d["typ"].add(r.kollekttyp)

    forsamlingar = sorted({f for f, _ in swish} | {f for f, _ in kob})
    resultat = KollektAvstamning()
    for fors in forsamlingar:
        fa = ForsamlingAvstamning(forsamling=fors)
        datum_nycklar = sorted(
            {d for (f, d) in swish if f == fors} | {d for (f, d) in kob if f == fors},
            key=lambda x: (x is None, x))
        for datum in datum_nycklar:
            s = swish.get((fors, datum))
            k = kob.get((fors, datum))
            s_belopp = s["belopp"] if s else Decimal("0.00")
            k_belopp = k["belopp"] if k else Decimal("0.00")
            s_and = ", ".join(sorted(s["andamal"])) if s else ""
            k_and = ", ".join(sorted(k["andamal"])) if k else ""
            typ = _typ_bokstav((s["typ"] if s else set()) | (k["typ"] if k else set()))
            diff = s_belopp - k_belopp

            status, orsak = _bedom_kollekt(s_belopp, k_belopp, s_and, k_and, typ)
            fa.rader.append(AvstamRad(
                forsamling=fors, datum=datum, swish_andamal=s_and, kob_andamal=k_and,
                kollekttyp=typ, swish=s_belopp, kob=k_belopp, diff=diff,
                status=status, orsak=orsak,
            ))
        resultat.forsamlingar.append(fa)
    return resultat


def _bedom_kollekt(s: Decimal, k: Decimal, s_and: str, k_and: str, typ: str):
    if s > 0 and k > 0:
        if s == k:
            if s_and and k_and and normalisera_andamal(s_and) != normalisera_andamal(k_and):
                return "notis", "belopp stämmer, ändamålstext skiljer mot KOB"
            return "ok", ""
        return "diff", "beloppsdiff mot KOB"
    if s > 0 and k == 0:
        if typ in ("R", "S"):
            return "diff", "saknas i KOB - ej kompletterad (R/S ägs av andra)"
        return "diff", "saknas i KOB - ej registrerad eller annat tillfälle"
    if k > 0 and s == 0:
        return "diff", "finns i KOB men ej i Swish (kontant, annat datum/ändamål?)"
    return "ok", ""


# --- Gavoavstamning ---------------------------------------------------------

@dataclass
class KobGavaDetalj:
    beskrivning: str
    belopp: Decimal


@dataclass
class GavaAvstamRad:
    verksamhet: str
    swish: Decimal
    kob: Decimal
    diff: Decimal
    status: str
    orsak: str = ""
    kob_detaljer: list[KobGavaDetalj] = field(default_factory=list)


@dataclass
class GavaAvstamning:
    rader: list[GavaAvstamRad] = field(default_factory=list)
    omappade: list[KobGavaDetalj] = field(default_factory=list)

    @property
    def antal_diffar(self) -> int:
        return sum(1 for r in self.rader if r.status == "diff")


def _matcha_verksamhet(rad: KobInsamlingsrad) -> str | None:
    text = f"{rad.mottagare} {rad.beskrivning} {rad.notering}".casefold()
    for verksamhet, nyckelord in GAVA_NYCKELORD.items():
        if any(n in text for n in nyckelord):
            return verksamhet
    return None


def avstam_gava(underlag: Underlag, kob_rader: list[KobInsamlingsrad]) -> GavaAvstamning:
    # Kontototalen = allman manadssumma + per andamal + utbrutna sarskilda poster.
    swish: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
    for p in underlag.gava_manad:
        swish[p.verksamhet] += p.belopp
    for p in underlag.gava_per_andamal:
        swish[p.verksamhet] += p.belopp
    for p in underlag.gava_sarskilda:
        swish[p.verksamhet] += p.belopp

    kob: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
    detaljer: dict[str, list[KobGavaDetalj]] = defaultdict(list)
    omappade: list[KobGavaDetalj] = []
    for r in kob_rader:
        if r.inbetalningsmetod.strip() != SWISH_METOD:
            continue
        verksamhet = _matcha_verksamhet(r)
        detalj = KobGavaDetalj(beskrivning=r.beskrivning or r.mottagare, belopp=r.belopp)
        if verksamhet is None:
            omappade.append(detalj)
            continue
        kob[verksamhet] += r.belopp
        detaljer[verksamhet].append(detalj)

    resultat = GavaAvstamning(omappade=omappade)
    for verksamhet in sorted(set(swish) | set(kob)):
        s, k = swish[verksamhet], kob[verksamhet]
        diff = s - k
        if s > 0 and k == 0:
            status, orsak = "diff", "ej registrerad i KOB"
        elif k > 0 and s == 0:
            status, orsak = "diff", "finns i KOB men ej i Swish-underlaget"
        elif s == k:
            status, orsak = "ok", ""
        else:
            status, orsak = "diff", "beloppsdiff mot KOB"
        resultat.rader.append(GavaAvstamRad(
            verksamhet=verksamhet, swish=s, kob=k, diff=diff,
            status=status, orsak=orsak, kob_detaljer=detaljer.get(verksamhet, []),
        ))
    return resultat
