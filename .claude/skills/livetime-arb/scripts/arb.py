#!/usr/bin/env python3
"""
arb.py — jádro pro hledání arbitráže (surebet / "livetime") a výpočet vkladů.

Arbitráž = vsadíme VŠECHNY možné výsledky jednoho trhu, každý u sázkovky
s nejvyšším kurzem, tak, že součet implikovaných pravděpodobností je < 100 %.
Pak je výplata stejná ať padne cokoliv -> zaručený zisk.

Math (ověřeno proti snímkům z WhatsApp/ChatGPT):
  implikovaná pravd. výsledku i:  p_i = 1 / kurz_i
  S = suma(p_i)
  S < 1  =>  arbitráž existuje
  zisk (marže) = 1/S - 1
  vklad na výsledek i (pro celkový vklad T):  vklad_i = T * p_i / S
  výplata (ať padne cokoliv) = T / S

Příklad ze snímku: kurzy 3.00 a 1.83, T = 1000 Kč
  p = [0.3333, 0.5464], S = 0.8798
  marže = 1/0.8798 - 1 = 13.66 %
  vklady = [379 Kč, 621 Kč], výplata ~1137 Kč, zisk ~137 Kč   ✔ sedí
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from typing import Optional


# ──────────────────────────────────────────────────────────────────────────
# Datové typy
# ──────────────────────────────────────────────────────────────────────────

@dataclass
class Leg:
    """Jedna noha arbitráže = konkrétní výsledek u konkrétní sázkovky."""
    outcome: str        # název výsledku, např. "Nad 28.5" / "1" / "Pod 28.5"
    bookmaker: str      # tipsport / betano / bet365 / fortuna ...
    odds: float         # kurz
    stake: float = 0.0  # doporučený vklad (dopočítá se)


@dataclass
class Arb:
    """Nalezená arbitrážní příležitost na jednom trhu."""
    sport: str
    event: str          # "Alexander Zverev – Fritz Taylor"
    market: str         # "Esa v zápase – hranice 28.5"
    legs: list          # list[Leg]
    sum_prob: float     # S
    margin: float       # zisk jako podíl (0.1366 = 13.66 %)
    total_stake: float  # T
    payout: float       # výplata ať padne cokoliv
    profit: float       # zaručený zisk v Kč

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


# ──────────────────────────────────────────────────────────────────────────
# Jádro výpočtu
# ──────────────────────────────────────────────────────────────────────────

def implied_prob(odds: float) -> float:
    if odds <= 1.0:
        raise ValueError(f"Kurz musí být > 1.0, dostal jsem {odds}")
    return 1.0 / odds


def compute_arb(
    legs: list,
    total_stake: float = 1000.0,
    round_to: Optional[int] = 1,
) -> tuple:
    """Z listu Leg (každý jiný výsledek, ideálně nejvyšší kurz na trhu)
    spočítá S, marži a rozdělení vkladů.

    Vrací (sum_prob, margin, legs_s_vklady, payout, profit).
    Když round_to != None, vklady se zaokrouhlí a payout/profit se přepočítá
    z reálně zaokrouhlených vkladů (worst-case = nejnižší výplata).
    """
    if len(legs) < 2:
        raise ValueError("Arbitráž potřebuje aspoň 2 výsledky.")

    probs = [implied_prob(l.odds) for l in legs]
    S = sum(probs)

    for l, p in zip(legs, probs):
        l.stake = total_stake * p / S

    if round_to is not None:
        for l in legs:
            l.stake = round(l.stake / round_to) * round_to

    # Reálná výplata = pro každou nohu (vklad_i * kurz_i). Při zaokrouhlení
    # se nohy mírně liší -> garantovaný zisk = nejhorší (nejnižší) výplata.
    payouts = [l.stake * l.odds for l in legs]
    real_total = sum(l.stake for l in legs)
    payout = min(payouts)
    profit = payout - real_total
    margin = (1.0 / S) - 1.0

    return S, margin, legs, payout, profit


def best_legs_across_books(market_quotes: dict) -> list:
    """Z nabídek více sázkovek vybere pro každý výsledek nejvyšší kurz.

    market_quotes = {
        "Nad 28.5": {"tipsport": 3.00, "betano": 2.90},
        "Pod 28.5": {"bet365": 1.83, "fortuna": 1.80},
    }
    -> [Leg("Nad 28.5","tipsport",3.00), Leg("Pod 28.5","bet365",1.83)]
    """
    legs = []
    for outcome, books in market_quotes.items():
        if not books:
            continue
        book, odds = max(books.items(), key=lambda kv: kv[1])
        legs.append(Leg(outcome=outcome, bookmaker=book, odds=float(odds)))
    return legs


def find_arb(
    sport: str,
    event: str,
    market: str,
    market_quotes: dict,
    total_stake: float = 1000.0,
    min_margin: float = 0.0,
    round_to: Optional[int] = 1,
    min_books: int = 2,
    max_margin: float = 0.20,
) -> Optional[Arb]:
    """Vrátí Arb, jen pokud marže v <min_margin, max_margin> a nohy jsou
    aspoň ze `min_books` RŮZNÝCH sázkovek.

    Pojistky proti nesmyslům:
    - `min_books=2`: arbitráž musí být napříč sázkovkami. Když všechny nohy
      vyjdou u jedné sázkovky, je to vždy chyba dat (sázkovka má marži) → None.
    - `max_margin=0.20`: marže nad 20 % je u reálných trhů prakticky vždy
      chyba parsování / nesedící trhy → raději nezobrazit než lhát.
    """
    legs = best_legs_across_books(market_quotes)
    if len(legs) < 2:
        return None
    if len({l.bookmaker for l in legs}) < min_books:
        return None
    S, margin, legs, payout, profit = compute_arb(legs, total_stake, round_to)
    if margin < min_margin or margin > max_margin:
        return None
    return Arb(
        sport=sport, event=event, market=market, legs=legs,
        sum_prob=S, margin=margin, total_stake=total_stake,
        payout=payout, profit=profit,
    )


# ──────────────────────────────────────────────────────────────────────────
# Formátování výstupu
# ──────────────────────────────────────────────────────────────────────────

def format_arb(a: Arb) -> str:
    L = []
    L.append("─" * 64)
    L.append(f"🟢 SUREBET  ({a.margin*100:.2f} % zaručený zisk)")
    L.append(f"   {a.sport} · {a.event}")
    L.append(f"   Trh: {a.market}")
    L.append("")
    L.append(f"   {'Výsledek':<16}{'Sázkovka':<12}{'Kurz':>7}{'Vklad':>10}")
    for l in a.legs:
        L.append(f"   {l.outcome:<16}{l.bookmaker:<12}{l.odds:>7.2f}{l.stake:>9.0f} Kč")
    L.append("")
    L.append(f"   Celkový vklad: {sum(l.stake for l in a.legs):.0f} Kč"
             f"  →  výplata ~{a.payout:.0f} Kč  →  zisk ~{a.profit:.0f} Kč")
    L.append(f"   Suma implik. pravd.: {a.sum_prob*100:.2f} %  "
             f"(< 100 % = arbitráž)")
    L.append("─" * 64)
    return "\n".join(L)


def scan_quotes_file(
    path: str,
    total_stake: float = 1000.0,
    min_margin: float = 0.0,
    round_to: Optional[int] = 1,
) -> list:
    """Načte JSON s nabídkami a vrátí seznam nalezených arbitráží.

    Formát JSON viz examples/odds_sample.json.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    arbs = []
    for ev in data.get("events", []):
        for m in ev.get("markets", []):
            a = find_arb(
                sport=ev.get("sport", "?"),
                event=ev.get("event", "?"),
                market=m.get("market", "?"),
                market_quotes=m.get("quotes", {}),
                total_stake=total_stake,
                min_margin=min_margin,
                round_to=round_to,
            )
            if a:
                arbs.append(a)
    arbs.sort(key=lambda x: x.margin, reverse=True)
    return arbs


# ──────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────

def _cli():
    p = argparse.ArgumentParser(
        description="Hledá arbitráž (surebet) a počítá rozdělení vkladů.")
    sub = p.add_subparsers(dest="cmd", required=True)

    # calc: rychlý výpočet z kurzů na příkazové řádce
    pc = sub.add_parser("calc", help="Spočítej arbitráž z kurzů")
    pc.add_argument("odds", nargs="+", type=float,
                    help="kurzy jednotlivých výsledků, např. 3.00 1.83")
    pc.add_argument("-T", "--total", type=float, default=1000.0,
                    help="celkový vklad (default 1000)")
    pc.add_argument("-r", "--round", type=int, default=1,
                    help="zaokrouhlení vkladů (default 1 Kč; 0 = bez)")
    pc.add_argument("--labels", nargs="*", default=None,
                    help="názvy výsledků (volitelné)")
    pc.add_argument("--books", nargs="*", default=None,
                    help="názvy sázkovek (volitelné)")

    # scan: projdi JSON soubor s nabídkami
    ps = sub.add_parser("scan", help="Najdi arbitráže v JSON souboru nabídek")
    ps.add_argument("file", help="cesta k JSON (viz examples/odds_sample.json)")
    ps.add_argument("-T", "--total", type=float, default=1000.0)
    ps.add_argument("-m", "--min-margin", type=float, default=0.0,
                    help="minimální marže v %% (default 0)")
    ps.add_argument("-r", "--round", type=int, default=1)
    ps.add_argument("--json", action="store_true", help="výstup jako JSON")

    args = p.parse_args()
    round_to = None if getattr(args, "round", 1) == 0 else getattr(args, "round", 1)

    if args.cmd == "calc":
        labels = args.labels or [f"Výsledek {i+1}" for i in range(len(args.odds))]
        books = args.books or [f"book{i+1}" for i in range(len(args.odds))]
        legs = [Leg(labels[i] if i < len(labels) else f"V{i+1}",
                    books[i] if i < len(books) else f"book{i+1}",
                    o) for i, o in enumerate(args.odds)]
        S, margin, legs, payout, profit = compute_arb(legs, args.total, round_to)
        a = Arb("?", "manuální výpočet", "?", legs, S, margin,
                args.total, payout, profit)
        print(format_arb(a))
        if margin <= 0:
            print("\n⚠️  Marže ≤ 0 → NENÍ to arbitráž (suma pravd. ≥ 100 %).")
        return

    if args.cmd == "scan":
        arbs = scan_quotes_file(args.file, args.total,
                                args.min_margin / 100.0, round_to)
        if args.json:
            print(json.dumps([a.to_dict() for a in arbs],
                              ensure_ascii=False, indent=2))
            return
        if not arbs:
            print("Žádná arbitráž nad zadanou marží nenalezena.")
            return
        print(f"Nalezeno {len(arbs)} příležitostí:\n")
        for a in arbs:
            print(format_arb(a))
            print()


if __name__ == "__main__":
    _cli()
