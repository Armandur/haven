"""Facit-test: last pipelinens siffror mot den kanda maj 2026-avstamningen.

Kraver att data/-filerna finns (gitignorade). Hoppas over annars.
"""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from app.config import DATA_DIR, KALENDER_FIL
from app.core.ingest_kob import las_kob_insamling, las_kob_kollekt
from app.core.pipeline import kor_pipeline
from app.core.reconcile import avstam_gava, avstam_kollekt

SWISH = DATA_DIR / "1948 25-05 Uppdelad.xlsx"
KOB_KOLLEKT = DATA_DIR / "KOB_ParishCollectionReport (18).xls"
KOB_INSAMLING = DATA_DIR / "KOB_Accounts_Contributions (15).xls"

pytestmark = pytest.mark.skipif(
    not (SWISH.exists() and (DATA_DIR / KALENDER_FIL).exists()),
    reason="maj 2026-testdata saknas i data/",
)


@pytest.fixture(scope="module")
def res():
    return kor_pipeline(SWISH)


def _d(x: str) -> Decimal:
    return Decimal(x)


def test_total_och_sjalvkontroll(res):
    total = sum((t.belopp for t in res.rapport.transaktioner), _d("0"))
    assert total == _d("30692.00")
    u = res.underlag
    delar = (
        sum((p.belopp for p in u.f_poster), _d("0"))
        + sum((g.summa for g in u.rs_grupper), _d("0"))
        + sum((p.belopp for p in u.gava_manad), _d("0"))
        + sum((p.belopp for p in u.gava_per_andamal), _d("0"))
        + sum((t.belopp for t in u.omatchade), _d("0"))
    )
    assert delar == total


def test_inga_omatchade(res):
    assert res.underlag.omatchade == []


def test_tillfalle_folas_pa_kalenderdatum(res):
    """Betalning dagen efter gudstjansten ska folas in pa tillfallet, inte bli
    egen post. Laser matchad_kalenderdatum-aggregeringen (05-18 -> 05-17)."""
    from datetime import date
    jul = [p for p in res.underlag.f_poster
           if p.forsamling == "Härnösands domkyrkoförsamling" and p.andamal == "Jul i gemenskap"]
    assert len(jul) == 1, "Jul i gemenskap ska vara en enda post (05-17)"
    assert jul[0].datum == date(2026, 5, 17)
    assert jul[0].belopp == _d("1500.00")

    # R-kollekten ska grupperas pa tillfallet 05-10, inte splittas pa 05-13.
    r_datum = {g.datum for g in res.underlag.rs_grupper if g.kollekttyp == "R"}
    assert date(2026, 5, 13) not in r_datum
    assert date(2026, 5, 10) in r_datum


def test_gava_manadssummor(res):
    per = {p.verksamhet: p.belopp for p in res.underlag.gava_manad}
    assert per["ACT Svenska Kyrkan"] == _d("6656.00")
    assert per["Diakoni"] == _d("1885.00")
    assert per["Musik"] == _d("8530.00")


def test_kollekt_per_forsamling_mot_kob(res):
    """Swish 1-summa per forsamling ska matcha KOB."""
    swish = {}
    for p in res.underlag.f_poster:
        swish[p.forsamling] = swish.get(p.forsamling, _d("0")) + p.belopp
    for g in res.underlag.rs_grupper:
        for dl in g.delposter:
            swish[dl.forsamling] = swish.get(dl.forsamling, _d("0")) + dl.belopp

    kob = {}
    for r in las_kob_kollekt(KOB_KOLLEKT):
        if r.inbetalningsmetod.strip() == "Swish 1":
            kob[r.forsamling] = kob.get(r.forsamling, _d("0")) + r.belopp

    for fors, belopp in kob.items():
        assert swish.get(fors) == belopp, f"{fors}: swish {swish.get(fors)} != kob {belopp}"


def test_kollekt_avstamning_nettar_per_forsamling(res):
    avst = avstam_kollekt(res.rapport.transaktioner, las_kob_kollekt(KOB_KOLLEKT))
    assert avst.swish_total == _d("10076.00")
    assert avst.swish_total == avst.kob_total
    for f in avst.forsamlingar:
        assert f.diff == _d("0.00"), f"{f.forsamling} nettar inte: {f.diff}"


def test_stigsjo_visar_tva_motverkande_diffar(res):
    avst = avstam_kollekt(res.rapport.transaktioner, las_kob_kollekt(KOB_KOLLEKT))
    stigsjo = next(f for f in avst.forsamlingar if f.forsamling == "Stigsjö församling")
    diffar = [r for r in stigsjo.rader if r.status == "diff"]
    assert len(diffar) == 2
    assert {r.diff for r in diffar} == {_d("1120.00"), _d("-1120.00")}
    assert stigsjo.diff == _d("0.00")


def test_gava_avstamning(res):
    avst = avstam_gava(res.underlag, las_kob_insamling(KOB_INSAMLING))
    per = {r.verksamhet: r for r in avst.rader}
    assert per["ACT Svenska Kyrkan"].status == "ok"
    assert per["ACT Svenska Kyrkan"].kob == _d("6656.00")
    assert per["Diakoni"].status == "ok"
    assert per["Diakoni"].kob == _d("1885.00")
    assert per["Musik"].status == "diff"
    assert per["Gåvomedelskassan"].status == "diff"
