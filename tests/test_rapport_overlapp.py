from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

import app.database as db
import app.routes.web as web
from app.core.aggregate import Underlag
from app.core.models import Swishrapport
from app.core.pipeline import Pipelineresultat
from app.main import app
from app.services.ko_service import KoVy


client = TestClient(app)


@pytest.fixture
def isolerad_dashboard(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", future=True)
    monkeypatch.setattr(db, "engine", engine)
    db.Base.metadata.create_all(engine)

    for namn in ("a.xlsx", "b.xlsx"):
        (tmp_path / namn).touch()
    monkeypatch.setattr(web, "DATA_DIR", tmp_path)

    def fake_ladda_ko(sokvag):
        rapport = Swishrapport(
            filnamn=sokvag.name,
            period="2026-05",
            datumintervall="2026-05-01 till 2026-05-31",
            transaktioner=[],
        )
        resultat = Pipelineresultat(rapport=rapport, underlag=Underlag(period="2026-05"))
        return KoVy(resultat=resultat, poster=[])

    monkeypatch.setattr(web, "ladda_ko", fake_ladda_ko)
    return tmp_path


def _registrera(filnamn: str, tx_ids: set[str]) -> None:
    db.registrera_rapport(
        filnamn,
        "2026-05",
        f"hash-{filnamn}",
        len(tx_ids),
        str(Decimal(len(tx_ids))),
        tx_ids,
    )


def test_dashboard_varnar_for_delade_transaktioner(isolerad_dashboard):
    _registrera("a.xlsx", {"gemensam", "bara-a"})
    _registrera("b.xlsx", {"gemensam", "bara-b"})

    svar = client.get("/?fil=a.xlsx")

    assert svar.status_code == 200
    assert (
        "Rapporten delar 1 transaktioner med b.xlsx - risk för dubbelregistrering."
        in svar.text
    )


def test_dashboard_varnar_inte_for_disjunkta_rapporter(isolerad_dashboard):
    _registrera("a.xlsx", {"bara-a"})
    _registrera("b.xlsx", {"bara-b"})

    svar = client.get("/?fil=a.xlsx")

    assert svar.status_code == 200
    assert "risk för dubbelregistrering" not in svar.text


def test_rapportregistret_cachar_sorterade_tx_ids(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", future=True)
    monkeypatch.setattr(db, "engine", engine)
    db.Base.metadata.create_all(engine)

    _registrera("a.xlsx", {"tx-2", "tx-1"})

    with db.Session(engine) as session:
        rad = session.get(db.RapportRad, "a.xlsx")
        assert rad is not None
        assert rad.tx_ids == "tx-1,tx-2"
    assert db.las_rapporter()[0].tx_ids == frozenset({"tx-1", "tx-2"})



def test_migrering_lagger_till_tx_ids_i_befintligt_rapportregister(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", future=True)
    monkeypatch.setattr(db, "engine", engine)
    db.Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE rapport DROP COLUMN tx_ids"))

    db._migrera()

    with engine.begin() as connection:
        kolumner = {
            rad[1] for rad in connection.execute(text("PRAGMA table_info(rapport)"))
        }
    assert "tx_ids" in kolumner


def test_ko_registrerar_rapportens_tx_ids(tmp_path, monkeypatch):
    import app.services.ko_service as ko_service

    sokvag = tmp_path / "rapport.xlsx"
    sokvag.write_bytes(b"rapport")
    rapport = SimpleNamespace(
        filnamn="rapport.xlsx",
        period="2026-05",
        transaktioner=[
            SimpleNamespace(tx_id="tx-2", belopp=Decimal("2.00")),
            SimpleNamespace(tx_id="tx-1", belopp=Decimal("1.00")),
        ],
    )
    anrop = {}

    def fake_registrera(*args):
        anrop["args"] = args

    monkeypatch.setattr(ko_service, "registrera_rapport", fake_registrera)

    ko_service._registrera(sokvag, rapport)

    assert anrop["args"][5] == {"tx-1", "tx-2"}
