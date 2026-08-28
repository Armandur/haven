"""Routeprov för en fil-parameter som inte längre finns."""
from __future__ import annotations

from fastapi.testclient import TestClient

import app.routes.web as web
from app.main import app


client = TestClient(app)


def test_okand_fil_varnar_och_visar_senaste_rapporten(tmp_path, monkeypatch):
    senaste = tmp_path / "senaste.xlsx"
    senaste.touch()
    monkeypatch.setattr(web, "DATA_DIR", tmp_path)
    monkeypatch.setattr(web, "standard_rapportfil", lambda: senaste)

    svar = client.get("/kalender?fil=finns-inte.xlsx")

    assert svar.status_code == 200
    assert 'Den begärda rapporten "finns-inte.xlsx" saknas.' in svar.text
    assert "Senaste rapporten visas i stället." in svar.text
    assert "?fil=senaste.xlsx" in svar.text
