"""SQLite-tillstand for arbetskon. Lattviktigt i Fas 0 (bara bekraftelser);
full datamodell enligt SPEC.md avsnitt 11 byggs ut i Fas 2.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import String, create_engine, delete, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from app import config
from app.config import (
    DB_PATH,
    Forsamling,
    Kategori,
    Kollekttyp,
    Mottagare,
    Registreringssatt,
)
from app.core.regler import Overstyrning, SarskildPost


class Base(DeclarativeBase):
    pass


def _pdate(s: str | None) -> date | None:
    return date.fromisoformat(s) if s else None


def _ptxids(s: str | None) -> frozenset[str] | None:
    ids = [x for x in (s or "").split(",") if x]
    return frozenset(ids) if ids else None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _beskriv_urval(tx_ids, meddelande_filter, datum_fran, datum_till) -> str:
    if tx_ids:
        return f"{len(tx_ids)} markerade rader"
    delar = []
    if meddelande_filter:
        delar.append(f'"{meddelande_filter}"')
    if datum_fran or datum_till:
        delar.append(f"{datum_fran or ''}–{datum_till or ''}")
    return " ".join(delar) or "filter"


class Bekraftelse(Base):
    """En bekraftad registreringspost i arbetskon (idempotent pa nyckel)."""
    __tablename__ = "bekraftelse"

    nyckel: Mapped[str] = mapped_column(String, primary_key=True)
    period: Mapped[str] = mapped_column(String, index=True)
    av_vem: Mapped[str] = mapped_column(String, default="")
    tidpunkt: Mapped[str] = mapped_column(String, default="")


class OverstyrningRad(Base):
    """Manuell overstyrning av foreslaget kollektandamal (spec 8.3)."""
    __tablename__ = "overstyrning"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    period: Mapped[str] = mapped_column(String, index=True)
    forsamling: Mapped[str] = mapped_column(String)
    ny_andamal: Mapped[str] = mapped_column(String)
    ny_typ: Mapped[str] = mapped_column(String, default="")            # F/R/S eller ""
    ny_tillfallesdatum: Mapped[str] = mapped_column(String, default="")  # ISO eller ""
    tx_ids: Mapped[str] = mapped_column(String, default="")            # kommaseparerade
    meddelande_filter: Mapped[str] = mapped_column(String, default="")
    datum_fran: Mapped[str] = mapped_column(String, default="")
    datum_till: Mapped[str] = mapped_column(String, default="")
    orsak: Mapped[str] = mapped_column(String, default="")
    av_vem: Mapped[str] = mapped_column(String, default="")
    tidpunkt: Mapped[str] = mapped_column(String, default="")


class SarskildPostRad(Base):
    """En utbruten sarskild post pa ett gavokonto (spec 6.5)."""
    __tablename__ = "sarskild_post"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    period: Mapped[str] = mapped_column(String, index=True)
    verksamhet: Mapped[str] = mapped_column(String)
    namn: Mapped[str] = mapped_column(String)
    oronmarkning: Mapped[str] = mapped_column(String, default="")
    tx_ids: Mapped[str] = mapped_column(String, default="")            # kommaseparerade
    meddelande_filter: Mapped[str] = mapped_column(String, default="")
    datum_fran: Mapped[str] = mapped_column(String, default="")
    datum_till: Mapped[str] = mapped_column(String, default="")
    av_vem: Mapped[str] = mapped_column(String, default="")
    tidpunkt: Mapped[str] = mapped_column(String, default="")


class KollektdagKvittering(Base):
    """Kvitterad (bekraftad) avvikande riks-/stiftskollektdag (spec TASK-1530).
    Nyckel: forsamling + datum + typ + normaliserat andamal (se kollektdagar.py)."""
    __tablename__ = "kollektdag_kvittering"

    nyckel: Mapped[str] = mapped_column(String, primary_key=True)
    notering: Mapped[str] = mapped_column(String, default="")   # ex "Beviljat av domkapitlet"
    av_vem: Mapped[str] = mapped_column(String, default="")
    tidpunkt: Mapped[str] = mapped_column(String, default="")


class ForsamlingRad(Base):
    """Redigerbar forsamlingskonfig (froad fran config.FORSAMLINGAR)."""
    __tablename__ = "forsamling"

    kanoniskt: Mapped[str] = mapped_column(String, primary_key=True)
    kortkod: Mapped[str] = mapped_column(String, default="")
    alias: Mapped[str] = mapped_column(String, default="")   # kommaseparerade


class MottagareRad(Base):
    """Redigerbar mottagarmappning (froad fran config.MOTTAGARE)."""
    __tablename__ = "mottagare"

    namn: Mapped[str] = mapped_column(String, primary_key=True)
    kategori: Mapped[str] = mapped_column(String)             # kollekt | gava
    verksamhet: Mapped[str] = mapped_column(String, default="")
    registreringssatt: Mapped[str] = mapped_column(String, default="")
    aktiv: Mapped[int] = mapped_column(default=1)


class RegelhistorikRad(Base):
    """Logg over andringar av justeringsregler (sparbarhet, spec 9)."""
    __tablename__ = "regelhistorik"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tidpunkt: Mapped[str] = mapped_column(String, default="")
    period: Mapped[str] = mapped_column(String, index=True)
    typ: Mapped[str] = mapped_column(String)          # "overstyrning" | "sarskild"
    handelse: Mapped[str] = mapped_column(String)     # "skapad" | "borttagen"
    beskrivning: Mapped[str] = mapped_column(String, default="")
    av_vem: Mapped[str] = mapped_column(String, default="")
    # Urvalet vid handelsen, sa berorda rader kan losas upp aven for borttagna regler:
    scope: Mapped[str] = mapped_column(String, default="")   # forsamling | verksamhet
    tx_ids: Mapped[str] = mapped_column(String, default="")
    meddelande_filter: Mapped[str] = mapped_column(String, default="")
    datum_fran: Mapped[str] = mapped_column(String, default="")
    datum_till: Mapped[str] = mapped_column(String, default="")


class RapportRad(Base):
    """Register over importerade Swish-rapporter (idempotens + andringsdetektering)."""
    __tablename__ = "rapport"

    filnamn: Mapped[str] = mapped_column(String, primary_key=True)
    period: Mapped[str] = mapped_column(String, index=True)
    innehalls_hash: Mapped[str] = mapped_column(String, default="")
    antal_tx: Mapped[int] = mapped_column(default=0)
    total: Mapped[str] = mapped_column(String, default="0.00")
    forst_importerad: Mapped[str] = mapped_column(String, default="")
    senast_sedd: Mapped[str] = mapped_column(String, default="")
    andrad: Mapped[int] = mapped_column(default=0)   # latchad flagga: innehall har andrats
    tx_ids: Mapped[str] = mapped_column(String, default="")


engine = create_engine(f"sqlite:///{DB_PATH}", future=True)


def init_db() -> None:
    Base.metadata.create_all(engine)
    _migrera()
    _seed_konfig()


def _seed_konfig() -> None:
    """Fro forsamling/mottagare fran config forsta gangen (tomma tabeller)."""
    with Session(engine) as s:
        if s.scalars(select(ForsamlingRad).limit(1)).first() is None:
            for f in config.FORSAMLINGAR:
                s.add(ForsamlingRad(kanoniskt=f.kanoniskt, kortkod=f.kortkod,
                                    alias=",".join(f.alias)))
        if s.scalars(select(MottagareRad).limit(1)).first() is None:
            for m in config.MOTTAGARE:
                s.add(MottagareRad(
                    namn=m.namn, kategori=m.kategori.value,
                    verksamhet=m.verksamhet or "",
                    registreringssatt=m.registreringssatt.value if m.registreringssatt else "",
                    aktiv=1))
        s.commit()


def _migrera() -> None:
    """Latta ALTER TABLE-guards for befintliga databaser (ingen Alembic i Fas 0-1)."""
    tillagg = {
        "overstyrning": [("tx_ids", "TEXT DEFAULT ''")],
        "sarskild_post": [("tx_ids", "TEXT DEFAULT ''")],
        "rapport": [("tx_ids", "TEXT DEFAULT ''")],
        "kollektdag_kvittering": [("notering", "TEXT DEFAULT ''")],
        "regelhistorik": [
            ("scope", "TEXT DEFAULT ''"), ("tx_ids", "TEXT DEFAULT ''"),
            ("meddelande_filter", "TEXT DEFAULT ''"),
            ("datum_fran", "TEXT DEFAULT ''"), ("datum_till", "TEXT DEFAULT ''"),
        ],
    }
    with engine.begin() as conn:
        for tabell, kolumner in tillagg.items():
            befintliga = {rad[1] for rad in conn.execute(text(f"PRAGMA table_info({tabell})"))}
            for namn, typ in kolumner:
                if namn not in befintliga:
                    conn.execute(text(f"ALTER TABLE {tabell} ADD COLUMN {namn} {typ}"))


def bekraftade_nycklar(period: str) -> set[str]:
    with Session(engine) as s:
        rader = s.scalars(
            select(Bekraftelse.nyckel).where(Bekraftelse.period == period)
        ).all()
    return set(rader)


def bekrafta(nyckel: str, period: str, av_vem: str = "") -> None:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with Session(engine) as s:
        rad = s.get(Bekraftelse, nyckel)
        if rad is None:
            s.add(Bekraftelse(nyckel=nyckel, period=period, av_vem=av_vem, tidpunkt=now))
        else:
            rad.period, rad.av_vem, rad.tidpunkt = period, av_vem, now
        s.commit()


def angra(nyckel: str) -> None:
    with Session(engine) as s:
        rad = s.get(Bekraftelse, nyckel)
        if rad is not None:
            s.delete(rad)
            s.commit()


# --- Kvitterade kollektdagsavvikelser ---------------------------------------

def kvitterade_kollektdagar() -> dict[str, str]:
    """Nyckel -> notering for alla kvitterade avvikelser."""
    with Session(engine) as s:
        rader = s.scalars(select(KollektdagKvittering)).all()
        return {r.nyckel: r.notering for r in rader}


def kvittera_kollektdag(nyckel: str, notering: str = "", av_vem: str = "") -> None:
    """Upsert - anropas aven for att uppdatera noteringen pa en kvittering."""
    now = _now()
    with Session(engine) as s:
        rad = s.get(KollektdagKvittering, nyckel)
        if rad is None:
            s.add(KollektdagKvittering(nyckel=nyckel, notering=notering,
                                       av_vem=av_vem, tidpunkt=now))
        else:
            rad.notering, rad.av_vem, rad.tidpunkt = notering, av_vem, now
        s.commit()


def angra_kollektdag(nyckel: str) -> None:
    with Session(engine) as s:
        rad = s.get(KollektdagKvittering, nyckel)
        if rad is not None:
            s.delete(rad)
            s.commit()


# --- Overstyrningar ---------------------------------------------------------

def las_overstyrningar(period: str) -> list[Overstyrning]:
    with Session(engine) as s:
        rader = s.scalars(
            select(OverstyrningRad).where(OverstyrningRad.period == period)
            .order_by(OverstyrningRad.id)
        ).all()
        return [
            Overstyrning(
                id=r.id, period=r.period, forsamling=r.forsamling,
                ny_andamal=r.ny_andamal,
                ny_typ=Kollekttyp(r.ny_typ) if r.ny_typ else None,
                ny_tillfallesdatum=_pdate(r.ny_tillfallesdatum),
                tx_ids=_ptxids(r.tx_ids),
                meddelande_filter=r.meddelande_filter or None,
                datum_fran=_pdate(r.datum_fran), datum_till=_pdate(r.datum_till),
                orsak=r.orsak,
            ) for r in rader
        ]


def skapa_overstyrning(period: str, forsamling: str, ny_andamal: str,
                       ny_typ: str = "", ny_tillfallesdatum: str = "",
                       tx_ids: list[str] | None = None,
                       meddelande_filter: str = "", datum_fran: str = "",
                       datum_till: str = "", orsak: str = "", av_vem: str = "") -> None:
    with Session(engine) as s:
        s.add(OverstyrningRad(
            period=period, forsamling=forsamling, ny_andamal=ny_andamal,
            ny_typ=ny_typ, ny_tillfallesdatum=ny_tillfallesdatum,
            tx_ids=",".join(tx_ids or []),
            meddelande_filter=meddelande_filter, datum_fran=datum_fran,
            datum_till=datum_till, orsak=orsak, av_vem=av_vem, tidpunkt=_now(),
        ))
        s.commit()
    urval = _beskriv_urval(tx_ids, meddelande_filter, datum_fran, datum_till)
    _logga(period, "overstyrning", "skapad",
           f"{forsamling or '—'} → {ny_andamal} ({urval})", av_vem,
           scope=forsamling, tx_ids=",".join(tx_ids or []),
           meddelande_filter=meddelande_filter, datum_fran=datum_fran, datum_till=datum_till)


def uppdatera_overstyrning(id: int, ny_andamal: str, ny_typ: str = "",
                           ny_tillfallesdatum: str = "", orsak: str = "",
                           av_vem: str = "") -> None:
    """Uppdaterar malet (andamal/typ/tillfallesdatum) pa en befintlig overstyrning.
    Urvalet (tx_ids/filter) behalls. Loggar en 'andrad'-post i historiken."""
    with Session(engine) as s:
        rad = s.get(OverstyrningRad, id)
        if rad is None:
            return
        period = rad.period
        gammalt = f"{rad.forsamling or '—'} → {rad.ny_andamal}"
        rad.ny_andamal = ny_andamal
        rad.ny_typ = ny_typ
        rad.ny_tillfallesdatum = ny_tillfallesdatum
        rad.orsak = orsak
        urval = _beskriv_urval(_ptxids(rad.tx_ids), rad.meddelande_filter,
                               rad.datum_fran, rad.datum_till)
        scope, tx_ids = rad.forsamling, rad.tx_ids
        mfilter, dfran, dtill = rad.meddelande_filter, rad.datum_fran, rad.datum_till
        s.commit()
    _logga(period, "overstyrning", "ändrad",
           f"{gammalt} ⟶ {ny_andamal} ({urval})", av_vem, scope=scope, tx_ids=tx_ids,
           meddelande_filter=mfilter, datum_fran=dfran, datum_till=dtill)


def ta_bort_overstyrning(id: int) -> None:
    with Session(engine) as s:
        rad = s.get(OverstyrningRad, id)
        if rad is None:
            return
        period = rad.period
        urval = _beskriv_urval(_ptxids(rad.tx_ids), rad.meddelande_filter,
                               rad.datum_fran, rad.datum_till)
        beskrivning = f"{rad.forsamling or '—'} → {rad.ny_andamal} ({urval})"
        scope, tx_ids = rad.forsamling, rad.tx_ids
        mfilter, dfran, dtill = rad.meddelande_filter, rad.datum_fran, rad.datum_till
        s.delete(rad)
        s.commit()
    _logga(period, "overstyrning", "borttagen", beskrivning, scope=scope, tx_ids=tx_ids,
           meddelande_filter=mfilter, datum_fran=dfran, datum_till=dtill)


# --- Sarskilda poster -------------------------------------------------------

def las_sarskilda(period: str) -> list[SarskildPost]:
    with Session(engine) as s:
        rader = s.scalars(
            select(SarskildPostRad).where(SarskildPostRad.period == period)
            .order_by(SarskildPostRad.id)
        ).all()
        return [
            SarskildPost(
                id=r.id, period=r.period, verksamhet=r.verksamhet, namn=r.namn,
                oronmarkning=r.oronmarkning, tx_ids=_ptxids(r.tx_ids),
                meddelande_filter=r.meddelande_filter or None,
                datum_fran=_pdate(r.datum_fran), datum_till=_pdate(r.datum_till),
            ) for r in rader
        ]


def skapa_sarskild(period: str, verksamhet: str, namn: str, oronmarkning: str = "",
                   tx_ids: list[str] | None = None,
                   meddelande_filter: str = "", datum_fran: str = "",
                   datum_till: str = "", av_vem: str = "") -> None:
    with Session(engine) as s:
        s.add(SarskildPostRad(
            period=period, verksamhet=verksamhet, namn=namn,
            oronmarkning=oronmarkning, tx_ids=",".join(tx_ids or []),
            meddelande_filter=meddelande_filter,
            datum_fran=datum_fran, datum_till=datum_till, av_vem=av_vem, tidpunkt=_now(),
        ))
        s.commit()
    urval = _beskriv_urval(tx_ids, meddelande_filter, datum_fran, datum_till)
    _logga(period, "sarskild", "skapad", f"{verksamhet} / {namn} ({urval})", av_vem,
           scope=verksamhet, tx_ids=",".join(tx_ids or []),
           meddelande_filter=meddelande_filter, datum_fran=datum_fran, datum_till=datum_till)


def ta_bort_sarskild(id: int) -> None:
    with Session(engine) as s:
        rad = s.get(SarskildPostRad, id)
        if rad is None:
            return
        period = rad.period
        urval = _beskriv_urval(_ptxids(rad.tx_ids), rad.meddelande_filter,
                               rad.datum_fran, rad.datum_till)
        beskrivning = f"{rad.verksamhet} / {rad.namn} ({urval})"
        scope, tx_ids = rad.verksamhet, rad.tx_ids
        mfilter, dfran, dtill = rad.meddelande_filter, rad.datum_fran, rad.datum_till
        s.delete(rad)
        s.commit()
    _logga(period, "sarskild", "borttagen", beskrivning, scope=scope, tx_ids=tx_ids,
           meddelande_filter=mfilter, datum_fran=dfran, datum_till=dtill)


# --- Rapportregister --------------------------------------------------------

@dataclass
class Rapportpost:
    filnamn: str
    period: str
    antal_tx: int
    total: Decimal
    forst_importerad: str
    senast_sedd: str
    andrad: bool
    tx_ids: frozenset[str]


@dataclass(frozen=True)
class Rapportoverlapp:
    filnamn: str
    antal: int


def registrera_rapport(filnamn: str, period: str, innehalls_hash: str,
                       antal_tx: int, total: str,
                       tx_ids: set[str] | frozenset[str] | None = None) -> bool:
    """Upsert pa filnamn. Returnerar True om innehallet andrats sedan forra gangen
    (samma filnamn men ny hash) - da bor tx_id-baserade regler ses over."""
    now = _now()
    andrad_nu = False
    tx_ids_text = ",".join(sorted(tx_ids)) if tx_ids is not None else ""
    with Session(engine) as s:
        rad = s.get(RapportRad, filnamn)
        if rad is None:
            s.add(RapportRad(
                filnamn=filnamn, period=period, innehalls_hash=innehalls_hash,
                antal_tx=antal_tx, total=total, forst_importerad=now,
                senast_sedd=now, andrad=0, tx_ids=tx_ids_text))
        else:
            if rad.innehalls_hash and rad.innehalls_hash != innehalls_hash:
                rad.andrad = 1
                andrad_nu = True
            rad.innehalls_hash = innehalls_hash
            rad.period = period
            rad.antal_tx = antal_tx
            rad.total = total
            rad.senast_sedd = now
            if tx_ids is not None:
                rad.tx_ids = tx_ids_text
        s.commit()
    return andrad_nu


def las_rapporter() -> list[Rapportpost]:
    with Session(engine) as s:
        rader = s.scalars(select(RapportRad).order_by(RapportRad.period.desc())).all()
        return [
            Rapportpost(
                filnamn=r.filnamn, period=r.period, antal_tx=r.antal_tx,
                total=Decimal(r.total or "0.00"),
                forst_importerad=r.forst_importerad, senast_sedd=r.senast_sedd,
                andrad=bool(r.andrad), tx_ids=_ptxids(r.tx_ids) or frozenset(),
            ) for r in rader
        ]


def rapport_andrad(filnamn: str) -> bool:
    with Session(engine) as s:
        rad = s.get(RapportRad, filnamn)
        return bool(rad and rad.andrad)


def rapport_overlapp(filnamn: str) -> list[Rapportoverlapp]:
    with Session(engine) as s:
        vald = s.get(RapportRad, filnamn)
        valda_ids = _ptxids(vald.tx_ids) if vald else None
        if not valda_ids:
            return []
        ovriga = s.scalars(
            select(RapportRad).where(RapportRad.filnamn != filnamn)
        ).all()

    resultat = []
    for rad in ovriga:
        gemensamma = valda_ids & (_ptxids(rad.tx_ids) or frozenset())
        if gemensamma:
            resultat.append(Rapportoverlapp(rad.filnamn, len(gemensamma)))
    return sorted(resultat, key=lambda o: (-o.antal, o.filnamn))


# --- Regelhistorik ----------------------------------------------------------

@dataclass
class Historikpost:
    tidpunkt: str
    period: str
    typ: str
    handelse: str
    beskrivning: str
    av_vem: str
    scope: str = ""
    tx_ids: frozenset[str] | None = None
    meddelande_filter: str | None = None
    datum_fran: date | None = None
    datum_till: date | None = None


def _logga(period: str, typ: str, handelse: str, beskrivning: str, av_vem: str = "",
           scope: str = "", tx_ids: str = "", meddelande_filter: str = "",
           datum_fran: str = "", datum_till: str = "") -> None:
    with Session(engine) as s:
        s.add(RegelhistorikRad(
            tidpunkt=_now(), period=period, typ=typ, handelse=handelse,
            beskrivning=beskrivning, av_vem=av_vem, scope=scope, tx_ids=tx_ids,
            meddelande_filter=meddelande_filter, datum_fran=datum_fran,
            datum_till=datum_till))
        s.commit()


def las_forsamlingar_konfig() -> tuple[Forsamling, ...]:
    with Session(engine) as s:
        rader = s.scalars(select(ForsamlingRad).order_by(ForsamlingRad.kanoniskt)).all()
        return tuple(
            Forsamling(r.kanoniskt, r.kortkod,
                       tuple(a.strip() for a in r.alias.split(",") if a.strip()))
            for r in rader
        )


def las_mottagare_konfig(endast_aktiva: bool = True) -> tuple[Mottagare, ...]:
    with Session(engine) as s:
        rader = s.scalars(select(MottagareRad).order_by(MottagareRad.namn)).all()
        return tuple(
            Mottagare(
                r.namn, Kategori(r.kategori), r.verksamhet or None,
                Registreringssatt(r.registreringssatt) if r.registreringssatt else None)
            for r in rader if (r.aktiv or not endast_aktiva)
        )


def spara_mottagare(namn: str, kategori: str, verksamhet: str = "",
                    registreringssatt: str = "", aktiv: int = 1) -> None:
    with Session(engine) as s:
        rad = s.get(MottagareRad, namn)
        if rad is None:
            s.add(MottagareRad(namn=namn, kategori=kategori, verksamhet=verksamhet,
                               registreringssatt=registreringssatt, aktiv=aktiv))
        else:
            rad.kategori = kategori
            rad.verksamhet = verksamhet
            rad.registreringssatt = registreringssatt
            rad.aktiv = aktiv
        s.commit()


def ta_bort_mottagare(namn: str) -> None:
    with Session(engine) as s:
        s.execute(delete(MottagareRad).where(MottagareRad.namn == namn))
        s.commit()


def spara_forsamling_alias(kanoniskt: str, alias: list[str]) -> None:
    with Session(engine) as s:
        rad = s.get(ForsamlingRad, kanoniskt)
        if rad is not None:
            rad.alias = ",".join(a.strip() for a in alias if a.strip())
            s.commit()


def las_historik(period: str, limit: int = 50) -> list[Historikpost]:
    with Session(engine) as s:
        rader = s.scalars(
            select(RegelhistorikRad).where(RegelhistorikRad.period == period)
            .order_by(RegelhistorikRad.id.desc()).limit(limit)
        ).all()
        return [
            Historikpost(
                tidpunkt=r.tidpunkt, period=r.period, typ=r.typ, handelse=r.handelse,
                beskrivning=r.beskrivning, av_vem=r.av_vem, scope=r.scope or "",
                tx_ids=_ptxids(r.tx_ids), meddelande_filter=r.meddelande_filter or None,
                datum_fran=_pdate(r.datum_fran), datum_till=_pdate(r.datum_till))
            for r in rader
        ]
