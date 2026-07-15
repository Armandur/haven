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


def test_overstyrning_loser_stigsjo():
    """Stigsjö-override (05-23 -> Musikverksamheten) ska nolla alla kollektdiffar."""
    from datetime import date
    from app.config import Kollekttyp
    from app.core.pipeline import kor_pipeline
    from app.core.regler import Overstyrning
    ov = [Overstyrning(
        id=1, period="2026-05", forsamling="Stigsjö församling",
        ny_andamal="Musikverksamheten i Stigsjö församling", ny_typ=Kollekttyp.F,
        ny_tillfallesdatum=date(2026, 5, 23),
        datum_fran=date(2026, 5, 23), datum_till=date(2026, 5, 23))]
    res = kor_pipeline(SWISH, overstyrningar=ov)
    avst = avstam_kollekt(res.rapport.transaktioner, las_kob_kollekt(KOB_KOLLEKT))
    assert avst.antal_diffar == 0
    stigsjo = next(f for f in avst.forsamlingar if f.forsamling == "Stigsjö församling")
    assert all(r.status == "ok" for r in stigsjo.rader)


def test_sarskild_post_invariant():
    """Utbruten särskild post + allmän ska motsvara kontots total."""
    from app.core.pipeline import kor_pipeline
    from app.core.regler import SarskildPost
    sar = [SarskildPost(id=1, period="2026-05", verksamhet="ACT Svenska Kyrkan",
                        namn="Ljuständning", meddelande_filter="ljus")]
    res = kor_pipeline(SWISH, sarskilda_poster=sar)
    u = res.underlag
    sarpost = next(p for p in u.gava_sarskilda if p.verksamhet == "ACT Svenska Kyrkan")
    allman = next(p for p in u.gava_manad if p.verksamhet == "ACT Svenska Kyrkan")
    assert allman.belopp + sarpost.belopp == _d("6656.00")
    assert sarpost.belopp > 0


def test_db_roundtrip_overstyrning(tmp_path, monkeypatch):
    """Låser skapa -> läs-seamen (sträng<->Kollekttyp/date) via en temp-DB."""
    from datetime import date
    from sqlalchemy import create_engine
    from app.config import Kollekttyp
    from app.core.pipeline import kor_pipeline
    import app.database as db

    eng = create_engine(f"sqlite:///{tmp_path / 't.db'}", future=True)
    monkeypatch.setattr(db, "engine", eng)
    db.Base.metadata.create_all(eng)

    db.skapa_overstyrning(
        "2026-05", "Stigsjö församling", "Musikverksamheten i Stigsjö församling",
        ny_typ="F", ny_tillfallesdatum="2026-05-23",
        datum_fran="2026-05-23", datum_till="2026-05-23")
    ov = db.las_overstyrningar("2026-05")
    assert len(ov) == 1
    assert ov[0].ny_typ == Kollekttyp.F
    assert ov[0].ny_tillfallesdatum == date(2026, 5, 23)

    res = kor_pipeline(SWISH, overstyrningar=ov)
    avst = avstam_kollekt(res.rapport.transaktioner, las_kob_kollekt(KOB_KOLLEKT))
    assert avst.antal_diffar == 0


def test_tx_id_stabil_och_unik():
    """tx_id ska vara stabilt mellan inlasningar och unikt per transaktion."""
    from app.core.pipeline import las_rapport
    a = las_rapport(SWISH)
    b = las_rapport(SWISH)
    ida = [t.tx_id for t in a.transaktioner]
    idb = [t.tx_id for t in b.transaktioner]
    assert ida == idb                      # deterministiskt
    assert len(set(ida)) == len(ida)       # unikt aven for identiska gavor
    assert all(t.tx_id for t in a.transaktioner)


def test_overstyrning_via_tx_ids(res):
    """Override pa bockade tx_ids (Stigsjö 05-23) ska nolla kollektdiffarna."""
    from datetime import date
    from app.config import Kollekttyp
    from app.core.pipeline import kor_pipeline
    from app.core.regler import Overstyrning
    ids = frozenset(
        t.tx_id for t in res.rapport.transaktioner
        if t.forsamling == "Stigsjö församling" and t.trans_datum == date(2026, 5, 23))
    assert len(ids) > 0
    ov = [Overstyrning(id=1, period="2026-05", forsamling="",
                       ny_andamal="Musikverksamheten i Stigsjö församling",
                       ny_typ=Kollekttyp.F, ny_tillfallesdatum=date(2026, 5, 23),
                       tx_ids=ids)]
    r2 = kor_pipeline(SWISH, overstyrningar=ov)
    avst = avstam_kollekt(r2.rapport.transaktioner, las_kob_kollekt(KOB_KOLLEKT))
    assert avst.antal_diffar == 0


def test_status_harleds(res):
    """Status ska härledas ur bekräftelser (inga i test-DB) + avstämning."""
    from app.database import init_db
    from app.services.avstamning_service import kor_avstamning
    from app.services.ko_service import KoVy, bygg_ko
    from app.services.status_service import bygg_status
    init_db()
    vy = KoVy(resultat=res, poster=bygg_ko(res.underlag))
    avst = kor_avstamning(res)
    ov = bygg_status(vy, avst)
    fmap = {e.namn: e for e in ov.forsamlingar}
    vmap = {e.namn: e for e in ov.verksamheter}
    assert all(e.tillstand == "ej_paborjad" for e in ov.forsamlingar)
    assert fmap["Säbrå församling"].avstamning_ok is True     # nettar rent
    assert vmap["ACT Svenska Kyrkan"].avstamning_ok is True
    assert vmap["Musik"].avstamning_ok is False               # ej registrerad i KOB


def test_rapportregister_idempotens_och_andring(tmp_path, monkeypatch):
    """Samma rapport dubbelregistrerar inte; ändrad hash flaggas (latchas)."""
    from sqlalchemy import create_engine
    import app.database as db
    eng = create_engine(f"sqlite:///{tmp_path / 't.db'}", future=True)
    monkeypatch.setattr(db, "engine", eng)
    db.Base.metadata.create_all(eng)

    assert db.registrera_rapport("f.xlsx", "2026-05", "H1", 515, "30692.00") is False
    assert db.registrera_rapport("f.xlsx", "2026-05", "H1", 515, "30692.00") is False
    assert len(db.las_rapporter()) == 1                       # idempotent
    assert db.registrera_rapport("f.xlsx", "2026-05", "H2", 515, "30692.00") is True
    assert db.rapport_andrad("f.xlsx") is True                # latchad
    assert len(db.las_rapporter()) == 1


def test_regelhistorik_loggas(tmp_path, monkeypatch):
    """Skapa/ta bort en regel ska logga skapad/borttagen med beskrivning."""
    from sqlalchemy import create_engine
    import app.database as db
    eng = create_engine(f"sqlite:///{tmp_path / 't.db'}", future=True)
    monkeypatch.setattr(db, "engine", eng)
    db.Base.metadata.create_all(eng)

    db.skapa_sarskild("2026-05", "Musik", "Konsert", meddelande_filter="konsert")
    h = db.las_historik("2026-05")
    assert len(h) == 1
    assert h[0].typ == "sarskild" and h[0].handelse == "skapad"
    assert "Musik / Konsert" in h[0].beskrivning

    sid = db.las_sarskilda("2026-05")[0].id
    db.ta_bort_sarskild(sid)
    h = db.las_historik("2026-05")
    assert len(h) == 2
    assert h[0].handelse == "borttagen"     # nyast först
