from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.config import Kategori, Kollekttyp
from app.core.aggregate import Underlag
from app.core.models import KobInsamlingsrad, KobKollektrad, Transaktion
from app.core.reconcile import (
    Datumintervall,
    GavaAvstamning,
    KollektAvstamning,
    avstam_gava,
    avstam_kollekt,
)
from app.deps import templates
from app.services.avstamning_service import Avstamningsresultat, kor_avstamning


def _transaktion(datum: date) -> Transaktion:
    return Transaktion(
        flik="Kollekt",
        bokf_datum=datum,
        trans_datum=datum,
        valuta_datum=datum,
        mottagarnummer="123",
        mottagarnamn="Testförsamlingen",
        meddelande="",
        orderreferens="ref",
        tid=None,
        belopp=Decimal("100.00"),
        kategori=Kategori.KOLLEKT,
        forsamling="Testförsamlingen",
        andamal="Teständamål",
        kollekttyp=Kollekttyp.F,
        matchad_kalenderdatum=datum,
    )


def _kob_kollekt(datum: date) -> KobKollektrad:
    return KobKollektrad(
        forsamling="Testförsamlingen",
        forsamling_ra="Testförsamlingen",
        kollektstalle="Testkyrkan",
        tillfallesdatum=datum,
        kollekttyp="F",
        andamal="Teständamål",
        inbetalningsmetod="Kontant",
        belopp=Decimal("0.00"),
        kalla="test.xls",
    )


def test_saknad_kollekt_utanfor_exportintervall_far_tydlig_orsak():
    avst = avstam_kollekt(
        [_transaktion(date(2026, 6, 1))],
        [_kob_kollekt(date(2026, 5, 1)), _kob_kollekt(date(2026, 5, 31))],
    )

    rad = next(r for f in avst.forsamlingar for r in f.rader if r.swish > 0)
    assert rad.status == "diff"
    assert "utanför KOB-exportens intervall" in rad.orsak
    assert "hämta om exporten" in rad.orsak
    assert avst.kob_intervall is not None
    assert avst.kob_intervall.fran == date(2026, 5, 1)
    assert avst.kob_intervall.till == date(2026, 5, 31)


def test_saknad_kollekt_inom_exportintervall_behaller_befintlig_orsak():
    avst = avstam_kollekt(
        [_transaktion(date(2026, 5, 17))],
        [_kob_kollekt(date(2026, 5, 1)), _kob_kollekt(date(2026, 5, 31))],
    )

    rad = next(r for f in avst.forsamlingar for r in f.rader if r.swish > 0)
    assert rad.orsak == "saknas i KOB - ej registrerad eller annat tillfälle"


def test_insamlingsexportens_datumtackning_harleds_fran_raderna():
    rader = [
        KobInsamlingsrad(
            forsamling="", mottagare="", datum=datum, insamlingstyp="",
            beskrivning="", oronmarkning="", notering="",
            inbetalningsmetod="Kontant", belopp=Decimal("0.00"), kalla="test.xls",
        )
        for datum in (date(2026, 5, 2), date(2026, 5, 30))
    ]

    avst = avstam_gava(Underlag(period="2026-05"), rader)

    assert avst.kob_intervall is not None
    assert avst.kob_intervall.fran == date(2026, 5, 2)
    assert avst.kob_intervall.till == date(2026, 5, 30)



def test_rapportintervall_harleds_fran_transaktionsdatum(monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setattr("app.services.avstamning_service._senaste", lambda glob: None)
    res = SimpleNamespace(
        rapport=SimpleNamespace(
            transaktioner=[
                _transaktion(date(2026, 5, 2)),
                _transaktion(date(2026, 6, 1)),
            ],
        ),
        underlag=Underlag(period="2026-05"),
    )

    avst = kor_avstamning(res)

    assert avst.rapport_intervall == Datumintervall(date(2026, 5, 2), date(2026, 6, 1))


def test_template_visar_bada_intervallvarningarna():
    from types import SimpleNamespace

    rapport_intervall = Datumintervall(date(2026, 5, 1), date(2026, 6, 1))
    avst = Avstamningsresultat(
        kollekt=KollektAvstamning(
            kob_intervall=Datumintervall(date(2026, 5, 1), date(2026, 5, 31)),
        ),
        gava=GavaAvstamning(
            kob_intervall=Datumintervall(date(2026, 5, 2), date(2026, 5, 30)),
        ),
        kob_kollekt_fil="kollekt.xls",
        kob_insamling_fil="insamling.xls",
        saknade=[],
        rapport_intervall=rapport_intervall,
    )
    vy = SimpleNamespace(resultat=SimpleNamespace(rapport=SimpleNamespace(period="2026-05")))
    request = SimpleNamespace(url=SimpleNamespace(path="/avstamning"),
                              state=SimpleNamespace(saknad_rapportfil=None))

    html = templates.get_template("avstamning.html").render(
        request=request, vy=vy, avst=avst, vald=None,
    )

    assert "KOB-kollektexporten täcker 2026-05-01 - 2026-05-31" in html
    assert "KOB-insamlingsexporten täcker 2026-05-02 - 2026-05-30" in html
    assert html.count("Hämta om exporten med ett större datumintervall.") == 2


def test_ingen_varning_nar_exporten_bara_borjar_senare():
    """Harledd tackning underskattar starten (forsta tillfallet ar sallan dag 1)
    - en korrekt manads export far inte ge falsk banner."""
    rapport = Datumintervall(date(2026, 5, 1), date(2026, 5, 29))
    kob = Datumintervall(date(2026, 5, 3), date(2026, 5, 31))
    assert not kob.saknar_tackning_for(rapport)


def test_varning_nar_rapporten_fortsatter_efter_exporten():
    rapport = Datumintervall(date(2026, 5, 1), date(2026, 6, 1))
    kob = Datumintervall(date(2026, 5, 3), date(2026, 5, 31))
    assert kob.saknar_tackning_for(rapport)


def test_varning_nar_exporten_ar_fel_manad():
    rapport = Datumintervall(date(2026, 5, 1), date(2026, 5, 29))
    kob = Datumintervall(date(2026, 5, 31), date(2026, 6, 28))
    assert kob.saknar_tackning_for(rapport)
