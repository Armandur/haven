from __future__ import annotations

from dataclasses import replace
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


def _kob_insamling(datum: date | None, belopp: str = "100.00") -> KobInsamlingsrad:
    return KobInsamlingsrad(
        forsamling="",
        mottagare="ACT Svenska kyrkan",
        datum=datum,
        insamlingstyp="",
        beskrivning="ACT Svenska kyrkan",
        oronmarkning="",
        notering="",
        inbetalningsmetod="Swish 1",
        belopp=Decimal(belopp),
        kalla="test.xls",
    )


def test_kollektrader_utanför_rapportperioden_summeras_och_filtreras():
    inom = replace(
        _kob_kollekt(date(2026, 5, 17)),
        inbetalningsmetod="Swish 1",
        belopp=Decimal("100.00"),
    )
    utanfor = replace(
        _kob_kollekt(date(2026, 6, 7)),
        inbetalningsmetod="Swish 1",
        belopp=Decimal("250.00"),
    )

    avst = avstam_kollekt(
        [_transaktion(date(2026, 5, 17))],
        [inom, utanfor],
        Datumintervall(date(2026, 5, 1), date(2026, 5, 31)),
    )

    assert avst.kob_total == Decimal("100.00")
    assert avst.antal_diffar == 0
    assert avst.utanfor_period_antal == 1
    assert avst.utanfor_period_summa == Decimal("250.00")
    assert all(r.datum != date(2026, 6, 7) for f in avst.forsamlingar for r in f.rader)


def test_kollektrad_for_manadsskiftestillfalle_behalls_nar_swish_har_tillfallet():
    """Sista sondagens tillfalle betalas via Swish men bokfors i nasta manads
    rapport - KOB-raden ska da jamforas, inte filtreras som annan manad."""
    kob = replace(
        _kob_kollekt(date(2026, 5, 31)),
        inbetalningsmetod="Swish 1",
        belopp=Decimal("100.00"),
    )

    avst = avstam_kollekt(
        [_transaktion(date(2026, 5, 31))],   # matchad mot 31 maj-tillfallet
        [kob],
        Datumintervall(date(2026, 6, 1), date(2026, 6, 30)),
    )

    assert avst.utanfor_period_antal == 0
    rad = next(r for f in avst.forsamlingar for r in f.rader)
    assert rad.datum == date(2026, 5, 31)
    assert rad.swish == rad.kob == Decimal("100.00")
    assert rad.status == "ok"


def test_typskillnad_med_stammande_belopp_ger_notis():
    datum = date(2026, 6, 28)
    transaktion = replace(
        _transaktion(datum),
        andamal="Act Svenska kyrkan",
        kollekttyp=Kollekttyp.R,
    )
    kob = replace(
        _kob_kollekt(datum),
        andamal="Act Svenska kyrkan",
        kollekttyp="Förskollekt nationell org",
        inbetalningsmetod="Swish 1",
        belopp=Decimal("100.00"),
    )

    avst = avstam_kollekt([transaktion], [kob])

    rad = next(r for f in avst.forsamlingar for r in f.rader)
    assert rad.status == "notis"
    assert rad.diff == Decimal("0.00")
    assert rad.orsak == (
        "belopp stämmer, men söktypen skiljer: kalendern säger Rikskollekt, "
        "KOB har Förskollekt nationell org"
    )


def test_f_och_forsamlingskollekt_ar_samma_soktyp():
    datum = date(2026, 5, 17)
    kob = replace(
        _kob_kollekt(datum),
        kollekttyp="Församlingskollekt",
        inbetalningsmetod="Swish 1",
        belopp=Decimal("100.00"),
    )

    avst = avstam_kollekt([_transaktion(datum)], [kob])

    rad = next(r for f in avst.forsamlingar for r in f.rader)
    assert rad.status == "ok"
    assert rad.orsak == ""


def test_f_till_nationell_org_matchar_forskollekt_nationell_org():
    datum = date(2026, 5, 17)
    transaktion = replace(_transaktion(datum), andamal="Act Svenska kyrkan")
    kob = replace(
        _kob_kollekt(datum),
        andamal="Act Svenska kyrkan",
        kollekttyp="Förskollekt nationell org",
        inbetalningsmetod="Swish 1",
        belopp=Decimal("100.00"),
    )

    avst = avstam_kollekt([transaktion], [kob])

    rad = next(r for f in avst.forsamlingar for r in f.rader)
    assert rad.kollekttyp == "N"
    assert rad.status == "ok"
    assert rad.orsak == ""


def test_kollektrad_utan_datum_och_utan_intervall_behandlas_som_tidigare():
    utan_datum = replace(
        _kob_kollekt(date(2026, 5, 17)),
        tillfallesdatum=None,
        inbetalningsmetod="Swish 1",
        belopp=Decimal("40.00"),
    )
    utanfor = replace(
        _kob_kollekt(date(2026, 6, 7)),
        inbetalningsmetod="Swish 1",
        belopp=Decimal("60.00"),
    )

    filtrerad = avstam_kollekt(
        [], [utan_datum, utanfor], Datumintervall(date(2026, 5, 1), date(2026, 5, 31)),
    )
    ofiltrerad = avstam_kollekt([], [utan_datum, utanfor])

    assert filtrerad.kob_total == Decimal("40.00")
    assert any(r.datum is None for f in filtrerad.forsamlingar for r in f.rader)
    assert ofiltrerad.kob_total == Decimal("100.00")
    assert ofiltrerad.utanfor_period_antal == 0


def test_insamlingsrader_utanför_rapportperioden_summeras_och_filtreras():
    avst = avstam_gava(
        Underlag(period="2026-05"),
        [
            _kob_insamling(date(2026, 5, 17), "100.00"),
            _kob_insamling(date(2026, 6, 7), "250.00"),
            _kob_insamling(None, "40.00"),
        ],
        Datumintervall(date(2026, 5, 1), date(2026, 5, 31)),
    )

    act = next(r for r in avst.rader if r.verksamhet == "ACT Svenska Kyrkan")
    assert act.kob == Decimal("140.00")
    assert len(act.kob_detaljer) == 2
    assert avst.utanfor_period_antal == 1
    assert avst.utanfor_period_summa == Decimal("250.00")


def test_insamlingsrader_utan_rapportintervall_filtreras_inte():
    avst = avstam_gava(
        Underlag(period="2026-05"),
        [_kob_insamling(date(2026, 6, 7), "250.00")],
    )

    act = next(r for r in avst.rader if r.verksamhet == "ACT Svenska Kyrkan")
    assert act.kob == Decimal("250.00")
    assert avst.utanfor_period_antal == 0


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


def test_rapportens_uttryckliga_datumintervall_anvands_fore_transaktionsdatumen(
    monkeypatch,
):
    from types import SimpleNamespace

    monkeypatch.setattr("app.services.avstamning_service._senaste", lambda glob: None)
    res = SimpleNamespace(
        rapport=SimpleNamespace(
            datumintervall="2026-05-01 - 2026-05-31",
            transaktioner=[_transaktion(date(2026, 5, 29))],
        ),
        underlag=Underlag(period="2026-05"),
    )

    avst = kor_avstamning(res)

    assert avst.rapport_intervall == Datumintervall(
        date(2026, 5, 1), date(2026, 5, 31),
    )


def _render_avstamning(avst) -> str:
    from types import SimpleNamespace
    vy = SimpleNamespace(resultat=SimpleNamespace(rapport=SimpleNamespace(period="2026-05")))
    request = SimpleNamespace(url=SimpleNamespace(path="/avstamning"),
                              state=SimpleNamespace(saknad_rapportfil=None))
    return templates.get_template("avstamning.html").render(
        request=request, vy=vy, avst=avst, vald=None,
    )


def test_template_visar_bada_intervallvarningarna():
    from app.core.reconcile import AvstamRad, ForsamlingAvstamning, GavaAvstamRad

    # Delvis overlapp: bade jamforda rader (kob > 0) och bortfiltrerade finns,
    # sa det ar intervallbanner + notis som ska visas, inte saknar-period-beskedet.
    kollekt = KollektAvstamning(
        kob_intervall=Datumintervall(date(2026, 5, 1), date(2026, 5, 31)),
        utanfor_period_antal=2,
        utanfor_period_summa=Decimal("350.00"),
        forsamlingar=[ForsamlingAvstamning("Testförsamlingen", rader=[
            AvstamRad(
                forsamling="Testförsamlingen", datum=date(2026, 5, 17),
                swish_andamal="X", kob_andamal="X", kollekttyp="F",
                swish=Decimal("100.00"), kob=Decimal("100.00"),
                diff=Decimal("0.00"), status="ok",
            ),
            AvstamRad(
                forsamling="Testförsamlingen", datum=date(2026, 6, 1),
                swish_andamal="X", kob_andamal="", kollekttyp="F",
                swish=Decimal("50.00"), kob=Decimal("0.00"),
                diff=Decimal("50.00"), status="diff",
                orsak="datumet ligger utanför KOB-exportens intervall - hämta om "
                      "exporten med ett större datumintervall",
            ),
        ])],
    )
    gava = GavaAvstamning(
        kob_intervall=Datumintervall(date(2026, 5, 2), date(2026, 5, 30)),
        utanfor_period_antal=3,
        utanfor_period_summa=Decimal("475.00"),
        rader=[GavaAvstamRad(verksamhet="Diakoni", swish=Decimal("50.00"),
                             kob=Decimal("50.00"), diff=Decimal("0.00"), status="ok")],
    )
    avst = Avstamningsresultat(
        kollekt=kollekt, gava=gava,
        kob_kollekt_fil="kollekt.xls", kob_insamling_fil="insamling.xls",
        saknade=[], rapport_intervall=Datumintervall(date(2026, 5, 1), date(2026, 6, 1)),
    )

    html = _render_avstamning(avst)

    assert "1 kollekttillfälle(n) i Swish-rapporten" in html
    assert "(2026-05-01 - 2026-05-31)" in html
    assert "KOB-insamlingsexporten täcker 2026-05-02 - 2026-05-30" in html
    assert html.count("Hämta om exporten med ett större datumintervall.") == 2
    assert "2 KOB-rader (350,00 kr) ligger utanför rapportens period" in html
    assert "3 KOB-rader (475,00 kr) ligger utanför rapportens period" in html


def test_kollektbanner_visas_inte_utan_tillfallen_utanfor_exporten():
    """Juni-fallet: rapportens deklarerade slut (30/6) ligger efter exportens
    sista tillfalle (28/6), men inga kollekttillfallen finns dar - betalningar
    29-30/6 framatfylls till 28/6. Ingen hamta om-banner da."""
    from app.core.reconcile import AvstamRad, ForsamlingAvstamning

    kollekt = KollektAvstamning(
        kob_intervall=Datumintervall(date(2026, 5, 31), date(2026, 6, 28)),
        forsamlingar=[ForsamlingAvstamning("Testförsamlingen", rader=[AvstamRad(
            forsamling="Testförsamlingen", datum=date(2026, 6, 28),
            swish_andamal="X", kob_andamal="X", kollekttyp="R",
            swish=Decimal("100.00"), kob=Decimal("100.00"),
            diff=Decimal("0.00"), status="ok",
        )])],
    )
    avst = Avstamningsresultat(
        kollekt=kollekt, gava=None,
        kob_kollekt_fil="kollekt.xls", kob_insamling_fil=None,
        saknade=[], rapport_intervall=Datumintervall(date(2026, 6, 1), date(2026, 6, 30)),
    )
    assert kollekt.tillfallen_utanfor_export == 0

    html = _render_avstamning(avst)

    assert "Hämta om exporten med ett större datumintervall." not in html
    assert "Ingen KOB-kollektexport finns" not in html


def test_template_visar_saknar_period_i_stallet_for_radvarningar():
    """Helt disjunkt export (alla KOB-rader bortfiltrerade, inget jamfort):
    ETT tydligt besked per sektion i stallet for banner + notis + diffrader."""
    avst = Avstamningsresultat(
        kollekt=KollektAvstamning(
            kob_intervall=Datumintervall(date(2026, 5, 31), date(2026, 6, 28)),
            utanfor_period_antal=20,
            utanfor_period_summa=Decimal("12262.00"),
        ),
        gava=GavaAvstamning(
            kob_intervall=Datumintervall(date(2026, 6, 5), date(2026, 6, 30)),
            utanfor_period_antal=2,
            utanfor_period_summa=Decimal("17909.50"),
        ),
        kob_kollekt_fil="kollekt.xls", kob_insamling_fil="insamling.xls",
        saknade=[], rapport_intervall=Datumintervall(date(2026, 7, 1), date(2026, 7, 31)),
    )
    assert avst.kollekt_saknar_period and avst.gava_saknar_period

    html = _render_avstamning(avst)

    assert "Ingen KOB-kollektexport finns för rapportens period" in html
    assert "Ingen KOB-insamlingsexport finns för rapportens period" in html
    assert "Hämta om exporten med ett större datumintervall." not in html
    assert "ligger utanför rapportens period och visas inte" not in html


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
