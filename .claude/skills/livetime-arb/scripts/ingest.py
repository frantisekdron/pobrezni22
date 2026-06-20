#!/usr/bin/env python3
"""
ingest.py — import kurzů ze zkopírovaných stránek do kotací (a do DB).

ŽÁDNÉ API. Zkopíruješ live stránku sázkovky (nebo ji načte Claude přes
WebFetch) a vložíš sem. Dva režimy:

1) BLOKOVÝ formát (nejspolehlivější) — direktivy @ nastavují kontext,
   řádky "výsledek | kurz" jsou data:

   @book tipsport
   @sport tenis
   @event Alexander Zverev | Taylor Fritz
   @market Esa v zápase | 28.5
   Nad | 3.00
   Pod | 1.83

   @book bet365
   @market Esa v zápase | 28.5
   Nad | 2.70
   Pod | 1.83

2) VOLNÝ text (--free) — naparsuje "popisek ... kurz" z nalepené stránky;
   kontext (book/event/market/line) dodáš přepínači. Méně spolehlivé,
   vždy si výsledek zkontroluj.

Výstup: kotace JSON na stdout, nebo rovnou do DB přes --db.
"""

from __future__ import annotations

import argparse
import json
import re
import sys

ODDS_RE = re.compile(r"(?<![\d.])(\d{1,3}(?:[.,]\d{1,3})?)(?![\d.])")


def _to_float(s: str):
    return float(s.replace(",", "."))


def parse_block(text: str) -> list:
    ctx = {"book": None, "sport": None, "home": None, "away": None,
           "market": None, "line": None}
    quotes = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("@"):
            key, _, val = line[1:].partition(" ")
            key = key.lower().strip()
            val = val.strip()
            if key == "book":
                ctx["book"] = val
            elif key == "sport":
                ctx["sport"] = val
            elif key == "event":
                # děl jen na oddělovačích, ne na písmenu "v" uvnitř jmen
                if "|" in val:
                    parts = val.split("|")
                else:
                    parts = re.split(r"\s+(?:vs?\.?|–|—|-)\s+", val, maxsplit=1)
                parts = [p.strip() for p in parts if p.strip()]
                if len(parts) >= 2:
                    ctx["home"], ctx["away"] = parts[0], parts[1]
            elif key == "market":
                parts = [p.strip() for p in val.split("|")]
                ctx["market"] = parts[0]
                ctx["line"] = _to_float(parts[1]) if len(parts) > 1 and parts[1] else None
            continue
        # datový řádek: "výsledek | kurz"   nebo  "výsledek    kurz"
        if "|" in line:
            label, _, odds_s = line.rpartition("|")
        else:
            m = list(ODDS_RE.finditer(line))
            if not m:
                continue
            odds_s = m[-1].group(1)
            label = line[:m[-1].start()].strip()
        label = label.strip()
        try:
            odds = _to_float(odds_s.strip())
        except ValueError:
            continue
        if odds <= 1.0:
            continue
        # hranice z popisku, pokud není v @market (např. "Nad 28.5")
        line_val = ctx["line"]
        lm = re.search(r"(\d+(?:[.,]\d+)?)", label)
        if line_val is None and lm and re.search(r"(nad|pod|over|under|více|méně)",
                                                  label, re.I):
            line_val = _to_float(lm.group(1))
        quotes.append({
            "bookmaker": ctx["book"] or "?",
            "sport": ctx["sport"] or "?",
            "home": ctx["home"] or "?", "away": ctx["away"] or "?",
            "market": ctx["market"] or "?",
            "line": line_val,
            "outcome": label or "?",
            "odds": odds,
        })
    return quotes


def parse_free(text: str, ctx: dict) -> list:
    """Z volného textu vytáhne 'popisek ... kurz'. Kontext z ctx."""
    quotes = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = list(ODDS_RE.finditer(line))
        cands = [mm for mm in m if 1.01 <= _to_float(mm.group(1)) <= 100]
        if not cands:
            continue
        odds = _to_float(cands[-1].group(1))
        label = line[:cands[-1].start()].strip(" :\t|-")
        if not label:
            continue
        quotes.append({
            "bookmaker": ctx.get("book", "?"), "sport": ctx.get("sport", "?"),
            "home": ctx.get("home", "?"), "away": ctx.get("away", "?"),
            "market": ctx.get("market", "?"), "line": ctx.get("line"),
            "outcome": label, "odds": odds,
        })
    return quotes


def main():
    p = argparse.ArgumentParser(
        description="Import kurzů ze zkopírovaných stránek do DB.")
    p.add_argument("file", nargs="?", help="soubor s textem (jinak stdin)")
    p.add_argument("--free", action="store_true",
                   help="volný text místo blokového formátu")
    p.add_argument("--book"); p.add_argument("--sport")
    p.add_argument("--home"); p.add_argument("--away")
    p.add_argument("--market"); p.add_argument("--line", type=float)
    p.add_argument("--db", action="store_true", help="ulož do DB místo stdout")
    args = p.parse_args()

    text = open(args.file, encoding="utf-8").read() if args.file else sys.stdin.read()

    if args.free:
        ctx = {"book": args.book or "?", "sport": args.sport or "?",
               "home": args.home or "?", "away": args.away or "?",
               "market": args.market or "?", "line": args.line}
        quotes = parse_free(text, ctx)
    else:
        quotes = parse_block(text)
        # přepínače můžou doplnit chybějící kontext
        for q in quotes:
            for k, a in (("bookmaker", args.book), ("sport", args.sport),
                         ("home", args.home), ("away", args.away),
                         ("market", args.market)):
                if a and (q.get(k) in (None, "?")):
                    q[k] = a
            if args.line is not None and q.get("line") is None:
                q["line"] = args.line

    if args.db:
        import db
        n = db.insert_quotes(quotes)
        print(f"Uloženo {n} kotací do DB.", file=sys.stderr)
    print(json.dumps({"quotes": quotes}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
