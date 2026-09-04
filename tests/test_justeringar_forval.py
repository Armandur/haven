"""Routeprov: forval_tx bockar rader och tillfallespickern renderas.

Kraver data/-filerna (gitignorade) - hoppas over annars, som facittestet.
"""
from __future__ import annotations

from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from app.config import DATA_DIR, KALENDER_FIL
from app.core.pipeline import kor_pipeline
from app.main import app
from app.services.ko_service import standard_rapportfil

client = TestClient(app)

pytestmark = pytest.mark.skipif(
    standard_rapportfil() is None or not (DATA_DIR / KALENDER_FIL).exists(),
    reason="rapport-/kalenderdata saknas i data/",
)


def _kollekt_tx():
    fil = standard_rapportfil()
    res = kor_pipeline(fil)
    t = next(t for t in res.rapport.transaktioner
             if t.kategori and t.kategori.value == "kollekt" and t.forsamling)
    return fil.name, t


def test_forval_tx_bockar_raden_och_pickern_renderas():
    filnamn, t = _kollekt_tx()
    r = client.get(
        f"/justeringar?fil={quote(filnamn)}"
        f"&ov_forsamling={quote(t.forsamling)}&forval_tx={t.tx_id}"
    )
    assert r.status_code == 200
    assert f'value="{t.tx_id}"\n                       checked' in r.text \
        or f'value="{t.tx_id}" checked' in r.text \
        or (t.tx_id in r.text and "checked" in r.text.split(t.tx_id, 1)[1][:100])
    assert "hv-tillfallepicker" in r.text
    assert "Hämta från kalendern" in r.text


def test_utan_forval_ar_inget_bockat():
    filnamn, t = _kollekt_tx()
    r = client.get(
        f"/justeringar?fil={quote(filnamn)}&ov_forsamling={quote(t.forsamling)}"
    )
    assert r.status_code == 200
    assert t.tx_id in r.text
    assert "checked" not in r.text.split(t.tx_id, 1)[1][:100]
