"""CLI for att kora och validera karnpipelinen mot en Swish-rapport.

    uv run cli.py "data/1948 25-05 Uppdelad.xlsx"
    uv run cli.py "data/1948 25-05 Uppdelad.xlsx" --kob-kollekt "data/KOB_ParishCollectionReport (18).xls"
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from app.core.ingest_kob import las_kob_insamling, las_kob_kollekt
from app.core.pipeline import kor_pipeline


def _kr(d: Decimal) -> str:
    return f"{d:>12,.2f}".replace(",", " ")


def main() -> None:
    ap = argparse.ArgumentParser(description="Kollektpipeline - validering")
    ap.add_argument("swish", help="Sokvag till Swish-rapport (.xlsx)")
    ap.add_argument("--kalender", help="Sokvag till andamalskalender (.xlsx)")
    ap.add_argument("--kob-kollekt", help="KOB ParishCollectionReport (.xls) for jamforelse")
    ap.add_argument("--kob-insamling", help="KOB Accounts_Contributions (.xls) for jamforelse")
    args = ap.parse_args()

    res = kor_pipeline(args.swish, args.kalender)
    rap, u = res.rapport, res.underlag

    print(f"\n=== Swish-rapport: {rap.filnamn} ===")
    print(f"Period: {rap.period}   Intervall: {rap.datumintervall}")
    print(f"Antal transaktioner: {len(rap.transaktioner)}")
    total = sum((t.belopp for t in rap.transaktioner), Decimal("0.00"))
    print(f"Total inkommande: {_kr(total)}")

    print(f"\n--- Forsamlingskollekter (F): {len(u.f_poster)} poster ---")
    for p in u.f_poster:
        print(f"  {p.forsamling:24} {p.datum:%Y-%m-%d}  {p.andamal:32} {_kr(p.belopp)}  ({p.antal} tx)")

    print(f"\n--- Riks/Stiftskollekter (R/S): {len(u.rs_grupper)} tillfallen ---")
    for g in u.rs_grupper:
        print(f"  [{g.kollekttyp}] {g.datum:%Y-%m-%d}  {g.andamal:40} summa {_kr(g.summa)}")
        for d in g.delposter:
            print(f"        {d.forsamling:24} {_kr(d.belopp)}  ({d.antal} tx)")

    print(f"\n--- Gava manadssumma: {len(u.gava_manad)} poster ---")
    for p in u.gava_manad:
        print(f"  {p.verksamhet:24} {p.period}  {_kr(p.belopp)}  ({p.antal} tx)")

    print(f"\n--- Gava per andamal (Gavomedelskassan m.fl.): {len(u.gava_per_andamal)} poster ---")
    gsum = defaultdict(lambda: Decimal("0.00"))
    for p in u.gava_per_andamal:
        gsum[p.verksamhet] += p.belopp
    for verksamhet, s in gsum.items():
        print(f"  {verksamhet:24} summa {_kr(s)}  ({sum(1 for p in u.gava_per_andamal if p.verksamhet==verksamhet)} grupper)")

    print(f"\n--- Omatchade/oklassade rader: {len(u.omatchade)} ---")
    orsaker = defaultdict(lambda: [0, Decimal("0.00")])
    for t in u.omatchade:
        k = orsaker[t.omatchad_orsak or "okand"]
        k[0] += 1
        k[1] += t.belopp
    for orsak, (n, s) in sorted(orsaker.items()):
        print(f"  {orsak:52} {n:>4} st  {_kr(s)}")

    # --- Sjalvkontroll: delar = total ---
    delar = (
        sum((p.belopp for p in u.f_poster), Decimal("0.00"))
        + sum((g.summa for g in u.rs_grupper), Decimal("0.00"))
        + sum((p.belopp for p in u.gava_manad), Decimal("0.00"))
        + sum((p.belopp for p in u.gava_per_andamal), Decimal("0.00"))
        + sum((t.belopp for t in u.omatchade), Decimal("0.00"))
    )
    print("\n=== Sjalvkontroll ===")
    print(f"Summa av alla delar: {_kr(delar)}")
    print(f"Total i rapporten:   {_kr(total)}")
    print("  OK - delarna motsvarar totalen" if delar == total
          else f"  AVVIKELSE: {_kr(delar - total)}")

    # --- Valfri jamforelse mot KOB (Swish 1-rader) ---
    if args.kob_kollekt:
        _jamfor_kob_kollekt(args.kob_kollekt, u)
    if args.kob_insamling:
        _jamfor_kob_insamling(args.kob_insamling, u)


def _jamfor_kob_kollekt(sokvag: str, u) -> None:
    rader = [r for r in las_kob_kollekt(sokvag) if r.inbetalningsmetod.strip() == "Swish 1"]
    per_fors = defaultdict(lambda: Decimal("0.00"))
    for r in rader:
        per_fors[r.forsamling] += r.belopp
    swish_per_fors = defaultdict(lambda: Decimal("0.00"))
    for p in u.f_poster:
        swish_per_fors[p.forsamling] += p.belopp
    for g in u.rs_grupper:
        for d in g.delposter:
            swish_per_fors[d.forsamling] += d.belopp
    print("\n=== KOB kollekt (Swish 1) per forsamling: Swish vs KOB ===")
    for fors in sorted(set(per_fors) | set(swish_per_fors)):
        s, k = swish_per_fors[fors], per_fors[fors]
        flagga = "" if s == k else "  <-- DIFF"
        print(f"  {fors:24} swish {_kr(s)}  kob {_kr(k)}{flagga}")


def _jamfor_kob_insamling(sokvag: str, u) -> None:
    rader = [r for r in las_kob_insamling(sokvag) if r.inbetalningsmetod.strip() == "Swish 1"]
    print("\n=== KOB insamling (Swish 1) ===")
    for r in rader:
        print(f"  {r.mottagare:28} {r.beskrivning:32} {_kr(r.belopp)}")
    print("  (jamfor manuellt mot gava-manadssummorna ovan)")


if __name__ == "__main__":
    main()
