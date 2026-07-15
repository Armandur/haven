"""SQLite-tillstand for arbetskon. Lattviktigt i Fas 0 (bara bekraftelser);
full datamodell enligt SPEC.md avsnitt 11 byggs ut i Fas 2.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from app.config import DB_PATH


class Base(DeclarativeBase):
    pass


class Bekraftelse(Base):
    """En bekraftad registreringspost i arbetskon (idempotent pa nyckel)."""
    __tablename__ = "bekraftelse"

    nyckel: Mapped[str] = mapped_column(String, primary_key=True)
    period: Mapped[str] = mapped_column(String, index=True)
    av_vem: Mapped[str] = mapped_column(String, default="")
    tidpunkt: Mapped[str] = mapped_column(String, default="")


engine = create_engine(f"sqlite:///{DB_PATH}", future=True)


def init_db() -> None:
    Base.metadata.create_all(engine)


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
