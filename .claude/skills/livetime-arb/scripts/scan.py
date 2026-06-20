#!/usr/bin/env python3
"""
scan.py — kompletní sken: posbírá kurzy z adaptérů sázkovek, sloučí je,
spáruje stejné zápasy/trhy a najde arbitráže (surebets).

Použití:
  python3 scan.py --sport tenis --books tipsport betano bet365 fortuna \\
      --total 1000 --min-margin 1.0

Když adaptéry nic nevrátí (sázkovky blokují automatický přístup), použij:
  - ruční výpočet:        python3 arb.py calc 3.00 1.83 --labels "Nad" "Pod"
  - sken z JSON nabídek:  python3 arb.py scan examples/odds_sample.json
  - sloučení kotací:      python3 normalize.py quotes.json | python3 arb.py scan /dev/stdin

Workflow přes Clauda (doporučeno): Claude nasbírá live kurzy (WebFetch /
ruční vstup), uloží je jako list kotací, spustí normalize.py + arb.py scan.
"""

from __future__ import annotations

import argparse
import json
import sys

import bookmakers
from normalize import merge_quotes
from arb import scan_quotes_file  # noqa: F401  (pro symetrii)
from arb import find_arb, format_arb


def gather(sport: str, books: list) -> list:
    quotes = []
    for name in books:
        bk = bookmakers.get(name)
        if not bk:
            print(f"[livetime-arb] neznámá sázkovka: {name}", file=sys.stderr)
            continue
        got = bk.fetch_live(sport)
        print(f"[livetime-arb] {name}: {len(got)} kotací", file=sys.stderr)
        quotes += got
    return quotes


def run(sport, books, total, min_margin, round_to, as_json):
    quotes = gather(sport, books)
    if not quotes:
        print("Žádné kurzy nenačteny. Zadej je ručně (viz arb.py / "
              "examples/odds_sample.json).", file=sys.stderr)
        return 1

    events = merge_quotes(quotes)
    arbs = []
    for ev in events.get("events", []):
        for m in ev.get("markets", []):
            a = find_arb(ev["sport"], ev["event"], m["market"],
                         m["quotes"], total, min_margin / 100.0, round_to)
            if a:
                arbs.append(a)
    arbs.sort(key=lambda x: x.margin, reverse=True)

    if as_json:
        print(json.dumps([a.to_dict() for a in arbs],
                         ensure_ascii=False, indent=2))
        return 0

    if not arbs:
        print("Žádná arbitráž nad zadanou marží nenalezena.")
        return 0
    print(f"Nalezeno {len(arbs)} příležitostí:\n")
    for a in arbs:
        print(format_arb(a))
        print()
    return 0


def main():
    p = argparse.ArgumentParser(description="Sken livetime arbitráže.")
    p.add_argument("--sport", default="tenis")
    p.add_argument("--books", nargs="+",
                   default=["tipsport", "betano", "bet365", "fortuna"])
    p.add_argument("-T", "--total", type=float, default=1000.0)
    p.add_argument("-m", "--min-margin", type=float, default=0.0,
                   help="minimální marže v %%")
    p.add_argument("-r", "--round", type=int, default=1)
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    round_to = None if args.round == 0 else args.round
    sys.exit(run(args.sport, args.books, args.total,
                 args.min_margin, round_to, args.json))


if __name__ == "__main__":
    main()
