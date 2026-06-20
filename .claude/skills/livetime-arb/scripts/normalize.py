#!/usr/bin/env python3
"""
normalize.py — sjednocení názvů a párování zápasů/trhů napříč sázkovkami.

Každá sázkovka píše jména jinak ("Alexander Zverev", "Zverev A.",
"A. Zverev"). Tenhle modul názvy znormalizuje a spáruje stejné zápasy
a stejné trhy, aby je arb.py mohl porovnat.

Vstup = list "kotací" (quotes) z jednotlivých sázkovek:
  {
    "bookmaker": "tipsport",
    "sport": "tenis",
    "home": "Alexander Zverev", "away": "Taylor Fritz",
    "market": "Esa v zápase",          # typ trhu
    "line": 28.5,                       # hranice (over/under), nebo None
    "outcome": "Nad",                   # "Nad"/"Pod" nebo "1"/"X"/"2"
    "odds": 3.00
  }

Výstup = events JSON ve formátu, který čte arb.py `scan`.
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from collections import defaultdict


# ── normalizace textu ─────────────────────────────────────────────────────

def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s)
                   if not unicodedata.combining(c))


def name_tokens(s: str) -> set:
    """Množina 'významných' tokenů jména (bez iniciál a krátkých slov).
    'Alexander Zverev' -> {alexander, zverev}; 'Zverev A.' -> {zverev}."""
    s = strip_accents(s or "").lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return {t for t in s.split() if len(t) >= 3}


def names_match(a: str, b: str) -> bool:
    """Stejný hráč/tým? Stačí překryv příjmení -> zvládne i iniciály."""
    ta, tb = name_tokens(a), name_tokens(b)
    if not ta or not tb:
        return False
    return bool(ta & tb)


def norm_market(s: str) -> str:
    s = strip_accents(s or "").lower().strip()
    s = re.sub(r"\s+", " ", s)
    aliases = {
        "esa": "aces", "esa v zapase": "aces", "aces": "aces",
        "vysledek zapasu": "1x2", "1x2": "1x2", "vitez": "1x2",
        "pocet gemu": "games", "games": "games",
        "celkem dvojchyb": "double_faults", "dvojchyby": "double_faults",
    }
    return aliases.get(s, s)


def norm_outcome(s: str) -> str:
    s = strip_accents(s or "").lower().strip()
    m = {
        "nad": "Over", "vice": "Over", "over": "Over", "more": "Over",
        "pod": "Under", "mene": "Under", "under": "Under", "less": "Under",
        "1": "1", "x": "X", "2": "2",
    }
    return m.get(s, s.capitalize())


def event_matches(sport, home, away, c_sport, c_home, c_away) -> bool:
    """Spáruje zápas s klastrem: stejný sport a oba účastníci se shodují
    (bijektivně, ať jsou uvedení v jakémkoliv pořadí)."""
    if strip_accents((sport or "").lower()) != strip_accents((c_sport or "").lower()):
        return False
    direct = names_match(home, c_home) and names_match(away, c_away)
    swap = names_match(home, c_away) and names_match(away, c_home)
    return direct or swap


def market_key(market: str, line) -> str:
    base = norm_market(market)
    if line is None or line == "":
        return base
    return f"{base}@{float(line):g}"


# ── sloučení kotací do events JSON ────────────────────────────────────────

def merge_quotes(quotes: list) -> dict:
    """list kotací -> events JSON pro arb.py scan.

    Zápasy páruje fuzzy klastrováním (překryv příjmení), takže
    'Alexander Zverev' a 'Zverev A.' skončí v jednom zápase.
    """
    clusters = []   # každý: dict se sport/home/away/markets(mk->oc->{book:odds})

    for q in quotes:
        sport = q.get("sport", "?")
        home = q.get("home", "?")
        away = q.get("away", "?")
        mk = market_key(q.get("market", ""), q.get("line"))
        oc = norm_outcome(q.get("outcome", ""))
        line = q.get("line")
        if line is not None and oc in ("Over", "Under"):
            oc = f"{oc} {float(line):g}"
        book = q.get("bookmaker", "?")
        odds = float(q["odds"])

        cl = None
        for c in clusters:
            if event_matches(sport, home, away, c["sport"], c["home"], c["away"]):
                cl = c
                break
        if cl is None:
            cl = {
                "sport": sport, "home": home, "away": away,
                "markets": defaultdict(lambda: defaultdict(dict)),
                "mkt_names": {},
            }
            clusters.append(cl)
        # preferuj delší (úplnější) jména pro zobrazení
        if len(home) > len(cl["home"]):
            cl["home"] = home
        if len(away) > len(cl["away"]):
            cl["away"] = away
        cl["mkt_names"][mk] = q.get("market", mk)

        prev = cl["markets"][mk][oc]
        if book not in prev or odds > prev[book]:
            prev[book] = odds

    out = {"events": []}
    for c in clusters:
        ev = {"sport": c["sport"],
              "event": f"{c['home']} – {c['away']}", "markets": []}
        for mk, quotes_by_oc in c["markets"].items():
            if len(quotes_by_oc) < 2:   # arbitráž potřebuje ≥2 výsledky
                continue
            ev["markets"].append({
                "market": c["mkt_names"].get(mk, mk),
                "quotes": {oc: dict(books) for oc, books in quotes_by_oc.items()},
            })
        if ev["markets"]:
            out["events"].append(ev)
    return out


def main():
    """Načte list kotací z STDIN nebo souborů a vypíše events JSON."""
    import argparse
    p = argparse.ArgumentParser(
        description="Sloučí kotace z více sázkovek do events JSON pro arb.py")
    p.add_argument("files", nargs="*",
                   help="JSON soubory s listem kotací (nebo {'quotes':[...]})")
    args = p.parse_args()

    quotes = []
    if args.files:
        for fp in args.files:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
            quotes += data.get("quotes", data) if isinstance(data, dict) else data
    else:
        data = json.load(sys.stdin)
        quotes = data.get("quotes", data) if isinstance(data, dict) else data

    print(json.dumps(merge_quotes(quotes), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
