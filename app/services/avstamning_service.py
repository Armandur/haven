"""Tjanstelager for avstamningen: hittar KOB-filerna och kor reconcile."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from app.config import DATA_DIR, KOB_INSAMLING_GLOB, KOB_KOLLEKT_GLOB
from app.core.ingest_kob import las_kob_insamling, las_kob_kollekt
from app.core.pipeline import Pipelineresultat
from app.core.reconcile import (
    Datumintervall,
    GavaAvstamning,
    KollektAvstamning,
    avstam_gava,
    avstam_kollekt,
)


@dataclass
class Avstamningsresultat:
    kollekt: KollektAvstamning | None
    gava: GavaAvstamning | None
    kob_kollekt_fil: str | None
    kob_insamling_fil: str | None
    saknade: list[str]
    rapport_intervall: Datumintervall | None


def _senaste(glob: str) -> Path | None:
    if not DATA_DIR.exists():
        return None
    traffar = sorted(DATA_DIR.glob(glob))
    return traffar[-1] if traffar else None


def kor_avstamning(res: Pipelineresultat) -> Avstamningsresultat:
    kollektfil = _senaste(KOB_KOLLEKT_GLOB)
    insamlingsfil = _senaste(KOB_INSAMLING_GLOB)
    saknade: list[str] = []
    rapport_datum = [t.trans_datum for t in res.rapport.transaktioner]
    rapport_intervall_text = getattr(res.rapport, "datumintervall", "")
    if rapport_intervall_text:
        fran_text, till_text = rapport_intervall_text.split(" - ", maxsplit=1)
        rapport_intervall = Datumintervall(
            date.fromisoformat(fran_text), date.fromisoformat(till_text),
        )
    else:
        rapport_intervall = (
            Datumintervall(min(rapport_datum), max(rapport_datum)) if rapport_datum else None
        )

    kollekt = None
    if kollektfil:
        kollekt = avstam_kollekt(
            res.rapport.transaktioner,
            las_kob_kollekt(kollektfil),
            rapport_intervall,
        )
    else:
        saknade.append(f"KOB-kollektexport ({KOB_KOLLEKT_GLOB})")

    gava = None
    if insamlingsfil:
        gava = avstam_gava(
            res.underlag,
            las_kob_insamling(insamlingsfil),
            rapport_intervall,
        )
    else:
        saknade.append(f"KOB-insamlingsexport ({KOB_INSAMLING_GLOB})")

    return Avstamningsresultat(
        kollekt=kollekt, gava=gava,
        kob_kollekt_fil=kollektfil.name if kollektfil else None,
        kob_insamling_fil=insamlingsfil.name if insamlingsfil else None,
        saknade=saknade,
        rapport_intervall=rapport_intervall,
    )
