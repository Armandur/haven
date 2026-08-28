"""Analys: flagga avvikande riks-/stiftskollektdagar mellan forsamlingar.

Riks- och stiftskollekter ar gemensamma - alla forsamlingsblad ska normalt ha
samma datum for samma andamal. En forsamling kan dock ha beviljat byte av
kollektdag (t.ex. Hemso som tar rikskollekter pa lordagar i stallet for
sondagar). Denna modul grupperar kalenderns R/S-rader per (typ, normaliserat
andamal), klustrar narliggande datum till samma tillfalle, och flaggar
forsamlingar vars datum avviker fran klustrets majoritetsdatum.

Ren analys, ingen I/O - tar list[Kalenderrad], returnerar list[Avvikelse].
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta

from app.config import Kollekttyp
from app.core.models import Kalenderrad
from app.core.normalize import normalisera_andamal

_GAP = timedelta(days=10)
_R_S = (Kollekttyp.R, Kollekttyp.S)


def kollektdag_nyckel(forsamling: str, datum: date, typ: Kollekttyp, andamal: str) -> str:
    """Stabil kvitteringsnyckel: forsamling + datum + typ + normaliserat andamal.

    `andamal` kan vara ra text eller redan normaliserad - normaliseras alltid har
    sa nyckeln blir densamma aven om anropande kod skickar ravardet.
    """
    return f"{forsamling}|{datum.isoformat()}|{typ.value}|{normalisera_andamal(andamal)}"


@dataclass
class Avvikelse:
    """En forsamlings avvikande kollektdag inom ett kluster av tillfallen."""
    typ: Kollekttyp
    andamal: str                          # visningstext (fran en majoritetsrad)
    normaliserat_andamal: str
    majoritetsdatum: date
    majoritet_antal: int
    majoritet_forsamlingar: tuple[str, ...]
    forsamling: str
    datum: date

    @property
    def nyckel(self) -> str:
        return kollektdag_nyckel(self.forsamling, self.datum, self.typ,
                                 self.normaliserat_andamal)


def hitta_avvikelser(rader: list[Kalenderrad]) -> list[Avvikelse]:
    """Grupperar R/S-rader per (typ, normaliserat andamal), klustrar narliggande
    datum (gap <= 10 dagar) till samma tillfalle, och flaggar forsamlingar vars
    datum avviker fran klustrets majoritetsdatum. Tva kluster med samma
    andamal men langt isar i tid (t.ex. olika manader) blandas inte ihop."""
    grupper: dict[tuple[Kollekttyp, str], list[Kalenderrad]] = {}
    for r in rader:
        if r.typ not in _R_S or not r.andamal:
            continue
        grupper.setdefault((r.typ, normalisera_andamal(r.andamal)), []).append(r)

    avvikelser: list[Avvikelse] = []
    for (typ, norm_andamal), grupp in grupper.items():
        for kluster in _klustra(grupp):
            avvikelser.extend(_flagga_kluster(typ, norm_andamal, kluster))
    return sorted(avvikelser, key=lambda a: (a.majoritetsdatum, a.forsamling))


def _klustra(rader: list[Kalenderrad]) -> list[list[Kalenderrad]]:
    """Ankarklustring i tva pass: forst valjs ankare (mest forekommande datum
    bland kvarvarande rader, tidigast vid lika) tills varje rad ligger inom
    _GAP fran nagot ankare; sedan tilldelas varje rad sitt NARMASTE ankare.

    Ren kedjeklustring (rad hor till klustret om den ligger nara FOREGAENDE
    rad) rakar lanka ihop tva egentligen skilda tillfallen nar en forsamling
    har en rad mitt emellan - t.ex. alla forsamlingar pa 20/6, sex av dem
    ocksa pa 5/7 (ett separat tillfalle 15 dagar senare) och en forsamling
    i stallet pa 28/6: kedjan slar ihop allt till EN grupp och flaggar de sex
    pa 5/7 som falska avvikare. Narmaste-tilldelningen gor dessutom att raden
    mitt emellan hamnar hos ratt tillfalle: Hemsos 28/6 hor till
    5/7-tillfallet (7 dagar) - inte midsommardagens 20/6 (8 dagar)."""
    kvar = list(rader)
    ankare: list[date] = []
    while kvar:
        rakning = Counter(r.datum for r in kvar)
        flest = max(rakning.values())
        a = min(d for d, antal in rakning.items() if antal == flest)
        ankare.append(a)
        kvar = [r for r in kvar if abs((r.datum - a).days) > _GAP.days]
    kluster: dict[date, list[Kalenderrad]] = {a: [] for a in ankare}
    for r in rader:
        narmast = min(ankare, key=lambda a: (abs((r.datum - a).days), a))
        kluster[narmast].append(r)
    return [k for k in kluster.values() if k]


def _flagga_kluster(typ: Kollekttyp, norm_andamal: str,
                    kluster: list[Kalenderrad]) -> list[Avvikelse]:
    per_datum: dict[date, list[Kalenderrad]] = {}
    for r in kluster:
        per_datum.setdefault(r.datum, []).append(r)
    if len(per_datum) <= 1:
        return []  # alla forsamlingar har samma datum - inget att flagga

    majoritetsdatum, majoritetsrader = max(
        per_datum.items(), key=lambda kv: (len(kv[1]), kv[0])
    )
    tvaa = max((len(v) for d, v in per_datum.items() if d != majoritetsdatum), default=0)
    if len(majoritetsrader) <= tvaa:
        return []  # ingen entydig majoritet - kan inte avgora vem som avviker

    return [
        Avvikelse(
            typ=typ, andamal=majoritetsrader[0].andamal, normaliserat_andamal=norm_andamal,
            majoritetsdatum=majoritetsdatum, majoritet_antal=len(majoritetsrader),
            majoritet_forsamlingar=tuple(r.forsamling for r in majoritetsrader),
            forsamling=r.forsamling, datum=d,
        )
        for d, rader in per_datum.items() if d != majoritetsdatum
        for r in rader
    ]
