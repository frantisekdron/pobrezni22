#!/usr/bin/env python3
"""
analyze.py — najde VŠECHNY příležitosti, ne jen surebety.

Reportuje dvě kategorie:

  1) SUREBET (arbitráž): součet implik. pravd. < 100 %. Jistý zisk při
     vsazení všech výsledků. Jakákoliv marže (i 0.3 %), seřazeno sestupně.

  2) VALUE BET (+EV single): kurz u jedné sázkovky je vyšší, než odpovídá
     "férové" pravděpodobnosti spočítané z konsensu všech sázkovek (po
     odečtení marže). Není to jistota, ale dlouhodobě +EV. Doporučí vklad
     přes zlomkový Kelly.

Vstup: events JSON (z normalize.py / odds_sample.json) přes soubor/stdin,
nebo --db (vezme čerstvé kotace z lokální DB).
"""

from __future__ import annotations

import argparse
import json
import sys

from arb import find_arb, format_arb, Leg, compute_arb, Arb


def fair_probs(quotes: dict) -> dict:
    """Z kurzů více sázkovek spočítá 'férové' pravd. výsledků (bez marže).

    quotes = {outcome: {book: odds}}  ->  {outcome: fair_prob}
    Metoda: pro každý výsledek průměr implik. pravd. napříč sázkovkami,
    pak normalizace na součet 1 (odstraní overround).
    """
    raw = {}
    for oc, books in quotes.items():
        if not books:
            continue
        ips = [1.0 / o for o in books.values() if o > 1.0]
        if ips:
            raw[oc] = sum(ips) / len(ips)
    S = sum(raw.values())
    if S <= 0:
        return {}
    return {oc: p / S for oc, p in raw.items()}


def kelly_fraction(odds: float, p: float) -> float:
    """Plný Kelly podíl bankrollu. b=odds-1, p=fér pravd., q=1-p."""
    b = odds - 1.0
    if b <= 0:
        return 0.0
    f = (b * p - (1 - p)) / b
    return max(0.0, f)


def find_value_bets(quotes: dict, min_edge: float, bankroll: float,
                    kelly: float, min_books: int = 2,
                    max_edge: float = 0.20) -> list:
    """Vrátí value bety: list dict s book/outcome/odds/edge/fair/stake.

    Pojistky: férová pravd. musí vzejít z konsenzu aspoň `min_books` sázkovek
    (jinak je „value" jen artefakt jediné sázkovky), a výhoda nad `max_edge`
    (20 %) se zahodí jako nejspíš chyba dat.
    """
    fair = fair_probs(quotes)
    out = []
    if len(fair) < 2:
        return out
    all_books = {bk for books in quotes.values() for bk in books}
    if len(all_books) < min_books:           # potřebujeme konsenzus napříč sázkovkami
        return out
    for oc, books in quotes.items():
        fp = fair.get(oc)
        if not fp:
            continue
        for book, odds in books.items():
            edge = odds * fp - 1.0          # EV na 1 Kč vkladu
            if min_edge <= edge <= max_edge:
                f = kelly_fraction(odds, fp) * kelly
                out.append({
                    "outcome": oc, "bookmaker": book, "odds": odds,
                    "fair_prob": fp, "edge": edge,
                    "stake": round(bankroll * f),
                })
    out.sort(key=lambda x: x["edge"], reverse=True)
    return out


def format_value(ev: dict, mkt: str, event: str, sport: str) -> str:
    return ("· VALUE  +{edge:.1f}%  {sport} · {event}\n"
            "    {oc} @ {book} {odds:.2f}  (fér {fair:.0f}%)  → vklad {stake} Kč"
            ).format(edge=ev["edge"] * 100, sport=sport, event=event,
                     oc=ev["outcome"], book=ev["bookmaker"], odds=ev["odds"],
                     fair=ev["fair_prob"] * 100, stake=ev["stake"])


def load_events(args) -> dict:
    if args.db:
        import db
        import normalize
        q = db.recent_quotes(args.max_age)
        return normalize.merge_quotes(q)
    text = open(args.file, encoding="utf-8").read() if args.file else sys.stdin.read()
    return json.loads(text)


def main():
    p = argparse.ArgumentParser(description="Najdi surebety i value bety.")
    p.add_argument("file", nargs="?", help="events JSON (jinak stdin)")
    p.add_argument("--db", action="store_true", help="vezmi kotace z DB")
    p.add_argument("--max-age", type=float, default=600,
                   help="stáří kotací z DB (s), default 600")
    p.add_argument("-T", "--total", type=float, default=1000.0,
                   help="vklad na jeden surebet")
    p.add_argument("-B", "--bankroll", type=float, default=100000.0,
                   help="celkový bankroll pro Kelly value sázky")
    p.add_argument("--kelly", type=float, default=0.25,
                   help="zlomek Kelly (default 0.25 = čtvrt-Kelly, bezpečnější)")
    p.add_argument("--min-margin", type=float, default=0.0,
                   help="min. marže surebetu v %% (default 0 = vše)")
    p.add_argument("--min-edge", type=float, default=2.0,
                   help="min. výhoda value betu v %% (default 2)")
    p.add_argument("-r", "--round", type=int, default=10)
    p.add_argument("--no-value", action="store_true", help="jen surebety")
    args = p.parse_args()
    round_to = None if args.round == 0 else args.round

    events = load_events(args)

    surebets, values = [], []
    for ev in events.get("events", []):
        for m in ev.get("markets", []):
            a = find_arb(ev["sport"], ev["event"], m["market"], m["quotes"],
                         args.total, args.min_margin / 100.0, round_to)
            if a:
                surebets.append(a)
            if not args.no_value:
                for vb in find_value_bets(m["quotes"], args.min_edge / 100.0,
                                          args.bankroll, args.kelly):
                    values.append((vb, m["market"], ev["event"], ev["sport"]))

    surebets.sort(key=lambda x: x.margin, reverse=True)
    values.sort(key=lambda x: x[0]["edge"], reverse=True)

    print("═" * 64)
    print(f"  SUREBETY (arbitráž): {len(surebets)}")
    print("═" * 64)
    for a in surebets:
        print(format_arb(a))
        print()
    if not surebets:
        print("  (žádný surebet nad zadanou marží)\n")

    if not args.no_value:
        print("═" * 64)
        print(f"  VALUE BETY (+EV single, ≥ {args.min_edge:.0f}%): {len(values)}")
        print("═" * 64)
        for vb, mkt, event, sport in values:
            print(format_value(vb, mkt, event, sport))
        if not values:
            print("  (žádný value bet nad zadanou výhodou)")


if __name__ == "__main__":
    main()
