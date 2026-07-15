"""Orkestrering av karnpipelinen: fran filer till registreringsunderlag."""
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


@dataclass
class Pipelineresultat:
    rapport: Swishrapport
    underlag: Underlag


def kor_pipeline(swish_sokvag: str | Path,
                 kalender_sokvag: str | Path | None = None) -> Pipelineresultat:
    kalender_sokvag = kalender_sokvag or (DATA_DIR / KALENDER_FIL)

    rapport = las_swishrapport(swish_sokvag)
    kalender = las_kalender(kalender_sokvag)
    index = Kalenderindex(kalender)

    klassificera(rapport.transaktioner)
    matcha_andamal(rapport.transaktioner, index)
    underlag = bygg_underlag(rapport.transaktioner, rapport.period)

    return Pipelineresultat(rapport=rapport, underlag=underlag)
