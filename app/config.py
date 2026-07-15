"""Konstanter, konfiguration och frodata for kollektverktyget.

Mottagarmappning och forsamlingsalias fros harifran (bekraftade mot
maj 2026-datan). I Fas 2 flyttas de till SQLite och blir redigerbara i UI:t.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from dotenv import load_dotenv

# --- Sokvagar ---------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
DATA_DIR = Path(os.environ.get("HAVEN_DATA_DIR", BASE_DIR / "data"))
KALENDER_FIL = os.environ.get("HAVEN_KALENDER_FIL", "2026 - Kollektändamål.xlsx")
KOB_KOLLEKT_GLOB = os.environ.get("HAVEN_KOB_KOLLEKT_GLOB", "KOB_ParishCollectionReport*.xls")
KOB_INSAMLING_GLOB = os.environ.get("HAVEN_KOB_INSAMLING_GLOB", "KOB_Accounts_Contributions*.xls")
DB_PATH = Path(os.environ.get("HAVEN_DB", BASE_DIR / "haven.db"))

HOST = os.environ.get("HAVEN_HOST", "0.0.0.0")
PORT = int(os.environ.get("HAVEN_PORT", "8000"))


# --- Domankategorier --------------------------------------------------------

class Kategori(str, Enum):
    KOLLEKT = "kollekt"
    GAVA = "gava"


class Kollekttyp(str, Enum):
    """Bokstav i andamalskalendern -> KOB:s kollekttyp."""
    F = "F"  # Forsamlingskollekt
    R = "R"  # Rikskollekt
    S = "S"  # Stiftskollekt

    @property
    def kob_namn(self) -> str:
        return {
            "F": "Församlingskollekt",
            "R": "Rikskollekt",
            "S": "Stiftskollekt",
        }[self.value]


class Registreringssatt(str, Enum):
    MANADSSUMMA = "manadssumma"
    PER_ANDAMAL = "per_andamal"


# Inbetalningsmetoden ar alltid denna i pastoratets fall (spec 6.6).
INBETALNINGSMETOD = "Swish 1"


# --- Forsamlingar (kollektmottagare) ----------------------------------------

@dataclass(frozen=True)
class Forsamling:
    kanoniskt: str
    kortkod: str          # bladnamn i andamalskalendern
    alias: tuple[str, ...] = field(default_factory=tuple)


# Kanoniskt namn = KOB-formen (det handlaggaren ser och skriver i KOB).
# Swish-stavningen och andra varianter ligger som alias.
FORSAMLINGAR: tuple[Forsamling, ...] = (
    Forsamling("Härnösands domkyrkoförsamling", "DK", ("Domkyrkoförsamlingen",)),
    Forsamling("Hemsö församling", "HE", ("Hemsö Församling",)),
    Forsamling("Häggdångers församling", "HÄ", ("Häggdångers Församling",)),
    Forsamling("Högsjö församling", "HÖ", ("Högsjö Församling",)),
    Forsamling("Stigsjö församling", "ST", ("Stigsjö Församling",)),
    Forsamling("Säbrå församling", "SÄ", ("Säbrå Församling",)),
    Forsamling("Viksjö församling", "VI", ("Viksjö Församling",)),
)


# --- Mottagarmappning (Mottagarnamn i Swish -> kategori) ---------------------

@dataclass(frozen=True)
class Mottagare:
    namn: str                       # sa som det star i Swish-rapporten
    kategori: Kategori
    # For kollekt: kopplas till forsamling via namn/alias.
    # For gava: verksamhet + registreringssatt.
    verksamhet: str | None = None
    registreringssatt: Registreringssatt | None = None


# Frovarden bekraftade mot maj 2026 (alla mottagare i datan finns med).
MOTTAGARE: tuple[Mottagare, ...] = (
    # Kollektmottagare (forsamlingar)
    Mottagare("Domkyrkoförsamlingen", Kategori.KOLLEKT),
    Mottagare("Hemsö Församling", Kategori.KOLLEKT),
    Mottagare("Häggdångers Församling", Kategori.KOLLEKT),
    Mottagare("Högsjö Församling", Kategori.KOLLEKT),
    Mottagare("Stigsjö Församling", Kategori.KOLLEKT),
    Mottagare("Säbrå Församling", Kategori.KOLLEKT),
    Mottagare("Viksjö Församling", Kategori.KOLLEKT),
    # Gavomottagare (verksamheter)
    Mottagare("ACT Svenska Kyrkan", Kategori.GAVA, "ACT Svenska Kyrkan",
              Registreringssatt.MANADSSUMMA),
    Mottagare("Barn & Unga", Kategori.GAVA, "Barn & Unga",
              Registreringssatt.MANADSSUMMA),
    Mottagare("Diakoni", Kategori.GAVA, "Diakoni",
              Registreringssatt.MANADSSUMMA),
    Mottagare("Musik", Kategori.GAVA, "Musik",
              Registreringssatt.MANADSSUMMA),
    Mottagare("Gåvomedelskassan", Kategori.GAVA, "Gåvomedelskassan",
              Registreringssatt.PER_ANDAMAL),
)


# Nyckelord for att koppla KOB-insamlingsrader (mottagare/beskrivning/notering)
# till ratt verksamhet vid gavoavstamning. KOB skriver t.ex. "Swish pastoratet
# maj" pa mottagaren "Act Svenska kyrkan" och "Swish pastoratet diakoni maj".
GAVA_NYCKELORD: dict[str, tuple[str, ...]] = {
    "ACT Svenska Kyrkan": ("act",),
    "Diakoni": ("diakoni",),
    "Musik": ("musik",),
    "Barn & Unga": ("barn", "unga"),
    "Gåvomedelskassan": ("gåvomedel", "gavomedel"),
}
