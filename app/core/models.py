"""Interna datamodeller for pipelinen (rena vardeobjekt, ingen I/O)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, time
from decimal import Decimal

from app.config import Kategori, Kollekttyp, Registreringssatt


@dataclass
class Transaktion:
    """En Swish-inbetalning fran rapporten, en rad."""
    flik: str                        # bladnamn/ansvarsomrade i rapporten
    bokf_datum: date
    trans_datum: date
    valuta_datum: date | None
    mottagarnummer: str
    mottagarnamn: str                # ravarde ur rapporten
    meddelande: str
    orderreferens: str
    tid: time | None
    belopp: Decimal
    clearingnummer: str | None = None
    kontonummer: str | None = None

    # Fylls i av senare steg:
    kategori: Kategori | None = None
    forsamling: str | None = None            # kanoniskt namn (kollekt)
    verksamhet: str | None = None            # gava
    registreringssatt: Registreringssatt | None = None
    andamal: str | None = None
    kollekttyp: Kollekttyp | None = None
    matchad_kalenderdatum: date | None = None   # sparbarhet: vilken kalenderrad
    omatchad_orsak: str | None = None           # satts nar ratt varde saknas


@dataclass
class Kalenderrad:
    forsamling: str          # kanoniskt namn
    kortkod: str
    datum: date
    veckodag: str
    helgdag: str
    typ: Kollekttyp | None   # kan saknas i kalendern
    andamal: str             # kan vara tom strang (andamal ej beslutat)


@dataclass
class KobKollektrad:
    forsamling: str          # kanoniskt (normaliserat)
    forsamling_ra: str       # ravarde ur KOB
    kollektstalle: str
    tillfallesdatum: date | None
    kollekttyp: str          # KOB-text (Forsamlingskollekt/Rikskollekt/Stiftskollekt)
    andamal: str
    inbetalningsmetod: str
    belopp: Decimal
    kalla: str


@dataclass
class KobInsamlingsrad:
    forsamling: str
    mottagare: str
    datum: date | None
    insamlingstyp: str
    beskrivning: str
    oronmarkning: str
    notering: str
    inbetalningsmetod: str
    belopp: Decimal
    kalla: str


@dataclass
class Swishrapport:
    """Resultatet av att lasa in en Swish-rapportfil."""
    filnamn: str
    period: str                      # "YYYY-MM" harlett ur datan
    datumintervall: str
    transaktioner: list[Transaktion] = field(default_factory=list)
