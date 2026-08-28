"""Route-tester for stegvis import: stage -> identifiera -> bekrafta/kassera.

Anropar routerna (inte bara servicen) med genererade minimifiler, mot en
tillfallig data-katalog sa riktiga data/ inte rors.
"""
from __future__ import annotations

from io import BytesIO

import openpyxl
import pytest
from fastapi.testclient import TestClient

import app.services.import_service as import_service
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def egen_datadir(tmp_path, monkeypatch):
    monkeypatch.setattr(import_service, "DATA_DIR", tmp_path)
    return tmp_path


def _swish_xlsx() -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Clearingnummer: 1234"])
    ws.append(["Bokföringsdatum", "Transaktionsdatum", "Valutadatum",
               "Mottagarnummer", "Mottagarnamn", "Meddelande",
               "Orderreferens", "Tid", "Belopp"])
    ws.append(["2026-05-17", "2026-05-17", "2026-05-17", "123",
               "Domkyrkoförsamlingen", "Kollekt", "abc", "10:00:00", 100])
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _kalender_xlsx() -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "DK"   # kortkod for Harnosands domkyrkoforsamling
    ws.append(["Datum", "Tema", "Veckodag", "Kyrklig helgdag", "Typ", "Ändamål"])
    ws.append(["2026-05-17", "", "Söndag", "", "F", "Diakoni"])
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _stagea(namn: str, innehall: bytes) -> dict:
    r = client.post("/import/stage", files={"fil": (namn, innehall)})
    assert r.status_code == 200, r.text
    return r.json()


def test_stage_identifierar_swish():
    d = _stagea("rapport.xlsx", _swish_xlsx())
    assert d["ok"] is True
    assert d["sort"] == "swish"
    assert d["filnamn"] == "rapport.xlsx"


def test_stage_identifierar_kalender():
    d = _stagea("kollektandamal.xlsx", _kalender_xlsx())
    assert d["sort"] == "kalender"


def test_stage_oidentifierad_fil_stagas_utan_sort(egen_datadir):
    d = _stagea("konstig.xlsx", b"inte en excelfil alls")
    assert d["ok"] is True
    assert d["sort"] is None
    assert list((egen_datadir / ".staging").glob(f"{d['token']}__*"))


def test_stage_avvisar_fel_andelse():
    r = client.post("/import/stage", files={"fil": ("dokument.pdf", b"x")})
    assert r.status_code == 400
    assert r.json()["ok"] is False


def test_bekrafta_flyttar_till_data(egen_datadir):
    d = _stagea("rapport.xlsx", _swish_xlsx())
    r = client.post("/import/bekrafta",
                    json={"val": [{"token": d["token"], "sort": "swish"}]})
    assert r.status_code == 200
    res = r.json()["resultat"][0]
    assert res["ok"] is True
    assert res["filnamn"] == "rapport.xlsx"
    assert (egen_datadir / "rapport.xlsx").exists()
    assert not list((egen_datadir / ".staging").glob(f"{d['token']}__*"))


def test_bekrafta_fel_sort_lamnar_filen_i_staging(egen_datadir):
    d = _stagea("rapport.xlsx", _swish_xlsx())
    r = client.post("/import/bekrafta",
                    json={"val": [{"token": d["token"], "sort": "kalender"}]})
    res = r.json()["resultat"][0]
    assert res["ok"] is False
    # Filen ligger kvar sa sorten kan andras och bekraftas igen
    assert list((egen_datadir / ".staging").glob(f"{d['token']}__*"))
    r2 = client.post("/import/bekrafta",
                     json={"val": [{"token": d["token"], "sort": "swish"}]})
    assert r2.json()["resultat"][0]["ok"] is True


def test_kassera_tar_bort_stagad_fil(egen_datadir):
    d = _stagea("rapport.xlsx", _swish_xlsx())
    r = client.post("/import/kassera", json={"tokens": [d["token"]]})
    assert r.status_code == 200
    assert not list((egen_datadir / ".staging").glob("*"))
    assert not (egen_datadir / "rapport.xlsx").exists()
