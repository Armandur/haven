"""SQLite-tillstand for arbetskon. Lattviktigt i Fas 0 (bara bekraftelser);
full datamodell enligt SPEC.md avsnitt 11 byggs ut i Fas 2.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import String, create_engine, delete, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from app.config import DB_PATH, Kollekttyp
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


engine = create_engine(f"sqlite:///{DB_PATH}", future=True)


def init_db() -> None:
    Base.metadata.create_all(engine)
    _migrera()


def _migrera() -> None:
    """Latta ALTER TABLE-guards for befintliga databaser (ingen Alembic i Fas 0-1)."""
    tillagg = {
        "overstyrning": [("tx_ids", "TEXT DEFAULT ''")],
        "sarskild_post": [("tx_ids", "TEXT DEFAULT ''")],
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
           f"{forsamling or '—'} → {ny_andamal} ({urval})", av_vem)


def ta_bort_overstyrning(id: int) -> None:
    with Session(engine) as s:
        rad = s.get(OverstyrningRad, id)
        if rad is None:
            return
        period = rad.period
        urval = _beskriv_urval(_ptxids(rad.tx_ids), rad.meddelande_filter,
                               rad.datum_fran, rad.datum_till)
        beskrivning = f"{rad.forsamling or '—'} → {rad.ny_andamal} ({urval})"
        s.delete(rad)
        s.commit()
    _logga(period, "overstyrning", "borttagen", beskrivning)


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
    _logga(period, "sarskild", "skapad", f"{verksamhet} / {namn} ({urval})", av_vem)


def ta_bort_sarskild(id: int) -> None:
    with Session(engine) as s:
        rad = s.get(SarskildPostRad, id)
        if rad is None:
            return
        period = rad.period
        urval = _beskriv_urval(_ptxids(rad.tx_ids), rad.meddelande_filter,
                               rad.datum_fran, rad.datum_till)
        beskrivning = f"{rad.verksamhet} / {rad.namn} ({urval})"
        s.delete(rad)
        s.commit()
    _logga(period, "sarskild", "borttagen", beskrivning)


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


def registrera_rapport(filnamn: str, period: str, innehalls_hash: str,
                       antal_tx: int, total: str) -> bool:
    """Upsert pa filnamn. Returnerar True om innehallet andrats sedan forra gangen
    (samma filnamn men ny hash) - da bor tx_id-baserade regler ses over."""
    now = _now()
    andrad_nu = False
    with Session(engine) as s:
        rad = s.get(RapportRad, filnamn)
        if rad is None:
            s.add(RapportRad(
                filnamn=filnamn, period=period, innehalls_hash=innehalls_hash,
                antal_tx=antal_tx, total=total, forst_importerad=now,
                senast_sedd=now, andrad=0))
        else:
            if rad.innehalls_hash and rad.innehalls_hash != innehalls_hash:
                rad.andrad = 1
                andrad_nu = True
            rad.innehalls_hash = innehalls_hash
            rad.period = period
            rad.antal_tx = antal_tx
            rad.total = total
            rad.senast_sedd = now
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
                andrad=bool(r.andrad),
            ) for r in rader
        ]


def rapport_andrad(filnamn: str) -> bool:
    with Session(engine) as s:
        rad = s.get(RapportRad, filnamn)
        return bool(rad and rad.andrad)


# --- Regelhistorik ----------------------------------------------------------

@dataclass
class Historikpost:
    tidpunkt: str
    typ: str
    handelse: str
    beskrivning: str
    av_vem: str


def _logga(period: str, typ: str, handelse: str, beskrivning: str, av_vem: str = "") -> None:
    with Session(engine) as s:
        s.add(RegelhistorikRad(
            tidpunkt=_now(), period=period, typ=typ, handelse=handelse,
            beskrivning=beskrivning, av_vem=av_vem))
        s.commit()


def las_historik(period: str, limit: int = 50) -> list[Historikpost]:
    with Session(engine) as s:
        rader = s.scalars(
            select(RegelhistorikRad).where(RegelhistorikRad.period == period)
            .order_by(RegelhistorikRad.id.desc()).limit(limit)
        ).all()
        return [
            Historikpost(tidpunkt=r.tidpunkt, typ=r.typ, handelse=r.handelse,
                         beskrivning=r.beskrivning, av_vem=r.av_vem)
            for r in rader
        ]
