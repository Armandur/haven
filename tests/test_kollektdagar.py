"""Tester for TASK-1530: avvikande riks-/stiftskollektdagar mellan forsamlingar.

Del 1: rena enhetstester av analysen (app/core/kollektdagar.py).
Del 2: route-tester mot /kalender (GET visar, POST kvittera/angra) med
isolerad DB och stubbad kalenderinlasning - riktiga data/ och haven.db rors inte.
"""
from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

import app.database as db
import app.routes.web as web
from app.config import Kollekttyp
from app.core.kollektdagar import hitta_avvikelser, kollektdag_nyckel
from app.core.models import Kalenderrad
from app.main import app

client = TestClient(app)


def _rad(forsamling: str, datum: date, typ: Kollekttyp = Kollekttyp.R,
        andamal: str = "Act Svenska kyrkan") -> Kalenderrad:
    return Kalenderrad(forsamling=forsamling, kortkod=forsamling[:2].upper(),
                       datum=datum, veckodag="", helgdag="", typ=typ, andamal=andamal)


# --- Analys ------------------------------------------------------------------

def test_samma_datum_overallt_ger_inga_flaggor():
    rader = [
        _rad("Domkyrko", date(2026, 6, 21)),
        _rad("Hemsö", date(2026, 6, 21)),
        _rad("Häggdånger", date(2026, 6, 21)),
    ]
    assert hitta_avvikelser(rader) == []


def test_en_avvikare_flaggas():
    rader = [
        _rad("Domkyrko", date(2026, 6, 21)),
        _rad("Häggdånger", date(2026, 6, 21)),
        _rad("Hemsö", date(2026, 6, 20)),
    ]
    avvikelser = hitta_avvikelser(rader)
    assert len(avvikelser) == 1
    a = avvikelser[0]
    assert a.forsamling == "Hemsö"
    assert a.datum == date(2026, 6, 20)
    assert a.majoritetsdatum == date(2026, 6, 21)
    assert a.majoritet_antal == 2
    assert a.typ is Kollekttyp.R


def test_tva_kluster_samma_andamal_olika_manader_blandas_inte_ihop():
    rader = [
        # Juni-tillfalle: tva overens, en avvikare
        _rad("Domkyrko", date(2026, 6, 21)),
        _rad("Häggdånger", date(2026, 6, 21)),
        _rad("Hemsö", date(2026, 6, 20)),
        # Augusti-tillfalle (samma andamal, langt fran juni): alla overens
        _rad("Domkyrko", date(2026, 8, 30)),
        _rad("Häggdånger", date(2026, 8, 30)),
        _rad("Hemsö", date(2026, 8, 30)),
    ]
    avvikelser = hitta_avvikelser(rader)
    assert len(avvikelser) == 1
    assert avvikelser[0].majoritetsdatum == date(2026, 6, 21)
    assert avvikelser[0].datum == date(2026, 6, 20)


def test_bro_via_mellanliggande_datum_slar_inte_ihop_tva_tillfallen():
    """Regression: en forsamling som lagger sitt EGET tillfalle mitt emellan tva
    skilda tillfallen ska inte lanka ihop dem via kedjeklustring (verklig bugg
    hittad mot 2026 - Kollektandamal.xlsx: R Act Svenska kyrkan 20/6 + 5/7 lankades
    ihop via Hemsos 28/6 och gav 6 falska avvikare pa 5/7). Raden mitt emellan
    ska dessutom tilldelas sitt NARMASTE tillfalle: 28/6 ligger 7 dagar fran 5/7
    men 8 fran midsommardagens 20/6 (dar alla ar overens) - avvikelsen ska alltsa
    rapporteras mot 5/7-majoriteten."""
    forsamlingar = ["Domkyrko", "Häggdånger", "Högsjö", "Stigsjö", "Säbrå", "Viksjö"]
    rader = []
    for f in forsamlingar:
        rader.append(_rad(f, date(2026, 6, 20)))
        rader.append(_rad(f, date(2026, 7, 5)))
    rader.append(_rad("Hemsö", date(2026, 6, 20)))
    rader.append(_rad("Hemsö", date(2026, 6, 28)))   # Hemsos motsvarighet till 5/7

    avvikelser = hitta_avvikelser(rader)
    assert len(avvikelser) == 1
    a = avvikelser[0]
    assert a.forsamling == "Hemsö"
    assert a.datum == date(2026, 6, 28)
    assert a.majoritetsdatum == date(2026, 7, 5)
    assert a.majoritet_antal == 6


def test_ingen_entydig_majoritet_flaggar_ingen():
    rader = [_rad("Domkyrko", date(2026, 6, 21)), _rad("Hemsö", date(2026, 6, 20))]
    assert hitta_avvikelser(rader) == []


def test_f_kollekt_ignoreras():
    rader = [
        _rad("Domkyrko", date(2026, 6, 21), typ=Kollekttyp.F, andamal="Diakoni"),
        _rad("Hemsö", date(2026, 6, 20), typ=Kollekttyp.F, andamal="Diakoni"),
    ]
    assert hitta_avvikelser(rader) == []


def test_nyckel_ar_stabil_och_innehaller_normaliserat_andamal():
    n1 = kollektdag_nyckel("Hemsö", date(2026, 6, 20), Kollekttyp.R, "Act Svenska kyrkan")
    n2 = kollektdag_nyckel("Hemsö", date(2026, 6, 20), Kollekttyp.R, "Act Svenska kyrkan")
    assert n1 == n2
    assert "Hemsö" in n1 and "2026-06-20" in n1


# --- Routes --------------------------------------------------------------

_RADER = [
    _rad("Domkyrko", date(2026, 6, 21)),
    _rad("Häggdånger", date(2026, 6, 21)),
    _rad("Hemsö", date(2026, 6, 20)),
]


@pytest.fixture
def kalendermiljo(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", future=True)
    monkeypatch.setattr(db, "engine", engine)
    db.Base.metadata.create_all(engine)

    monkeypatch.setattr(web, "DATA_DIR", tmp_path)
    (tmp_path / web.KALENDER_FIL).touch()
    monkeypatch.setattr("app.core.ingest_kalender.las_kalender", lambda _p: _RADER)
    return tmp_path


def test_get_kalender_visar_avvikelse(kalendermiljo):
    r = client.get("/kalender")
    assert r.status_code == 200
    assert "Hemsö" in r.text
    assert "2026-06-20" in r.text
    assert "Kvittera" in r.text


def test_post_kvittera_flyttar_till_kvitterade(kalendermiljo):
    nyckel = hitta_avvikelser(_RADER)[0].nyckel
    r = client.post("/kalender/kollektdag/kvittera", data={"nyckel": nyckel})
    assert r.status_code == 200   # foljde redirect till /kalender
    assert "Kvitterade kollektdagsavvikelser" in r.text
    assert "Ångra" in r.text

    # Notisrutan med avvikelsen ska inte langre finnas
    r2 = client.get("/kalender")
    assert "avvikande riks-/stiftskollektdag" not in r2.text


def test_post_angra_visar_avvikelsen_igen(kalendermiljo):
    nyckel = hitta_avvikelser(_RADER)[0].nyckel
    client.post("/kalender/kollektdag/kvittera", data={"nyckel": nyckel})
    r = client.post("/kalender/kollektdag/angra", data={"nyckel": nyckel})
    assert r.status_code == 200
    assert "avvikande riks-/stiftskollektdag" in r.text
    assert "Kvitterade kollektdagsavvikelser" not in r.text
