"""Orkestrering av karnpipelinen: fran filer till registreringsunderlag.

Delad i las_rapport (billig, ger perioden) och bearbeta (matchning, regler,
aggregering) sa att handlaggarregler for ratt period kan laddas dar emellan.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.config import DATA_DIR, KALENDER_FIL
from app.core.aggregate import Underlag, bygg_underlag
from app.core.classify import klassificera
from app.core.ingest_kalender import las_kalender
from app.core.ingest_swish import las_swishrapport
from app.core.match import Kalenderindex, matcha_andamal
from app.core.models import Swishrapport
from app.core.regler import (
    Overstyrning,
    SarskildPost,
    applicera_overstyrningar,
)


@dataclass
class Pipelineresultat:
    rapport: Swishrapport
    underlag: Underlag


def las_rapport(swish_sokvag: str | Path) -> Swishrapport:
    return las_swishrapport(swish_sokvag)


def bearbeta(rapport: Swishrapport,
             kalender_sokvag: str | Path | None = None,
             overstyrningar: list[Overstyrning] | None = None,
             sarskilda_poster: list[SarskildPost] | None = None) -> Pipelineresultat:
    kalender_sokvag = kalender_sokvag or (DATA_DIR / KALENDER_FIL)
    index = Kalenderindex(las_kalender(kalender_sokvag))

    klassificera(rapport.transaktioner)
    matcha_andamal(rapport.transaktioner, index)
    if overstyrningar:
        applicera_overstyrningar(rapport.transaktioner, overstyrningar)

    underlag = bygg_underlag(rapport.transaktioner, rapport.period,
                             sarskilda_poster or [])
    return Pipelineresultat(rapport=rapport, underlag=underlag)


def kor_pipeline(swish_sokvag: str | Path,
                 kalender_sokvag: str | Path | None = None,
                 overstyrningar: list[Overstyrning] | None = None,
                 sarskilda_poster: list[SarskildPost] | None = None) -> Pipelineresultat:
    rapport = las_rapport(swish_sokvag)
    return bearbeta(rapport, kalender_sokvag, overstyrningar, sarskilda_poster)
