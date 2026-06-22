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
    # over/under pozná i když je v popisku číslo ("nad 28.5", "vice nez 28.5")
    if re.search(r"\b(nad|vice|over|more)\b", s):
        return "Over"
    if re.search(r"\b(pod|mene|under|less)\b", s):
        return "Under"
    m = {"1": "1", "x": "X", "2": "2",
         "remiza": "X", "draw": "X", "home": "1", "away": "2"}
    return m.get(s, s.capitalize())


def event_matches(sport, home, away, c_sport, c_home, c_away) -> bool:
    """Spáruje zápas s klastrem podle účastníků (bijektivně). Sport blokuje,
    JEN když je u obou znám a liší se — neznámý sport ('?') nepárování nebrání
    (generický parser sport nezná, jinak by se tentýž zápas rozdělil)."""
    s1 = strip_accents((sport or "").lower()).strip()
    s2 = strip_accents((c_sport or "").lower()).strip()
    if s1 and s2 and s1 != "?" and s2 != "?" and s1 != s2:
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
    """list kotací -> events JSON pro arb.py.

    Striktní kanonizace: každá kotace se přes canon.canon() zařadí do jasně
    definovaného typu trhu (1X2/WINNER2/OU/BTTS) a kódu výsledku, nebo se
    ZAHODÍ. Zápasy páruje fuzzy klastrováním. Do výstupu jdou jen trhy s
    KOMPLETNÍ sadou opačných výsledků (např. OVER i UNDER téže hranice).
    """
    import canon as _canon

    clusters = []   # každý: {sport, home, away, markets:{key:{type,subject,line,codes}}}

    for q in quotes:
        try:                                   # jeden vadný kurz nesmí shodit celý dotaz
            sport = str(q.get("sport") or "?")
            home = str(q.get("home") or "?")
            away = str(q.get("away") or "?")
            try:
                odds = float(str(q.get("odds")).replace(",", "."))
            except (TypeError, ValueError):
                continue
            if not (1.01 <= odds <= 1000):
                continue
            c = _canon.canon(q.get("market", ""), q.get("outcome", ""),
                             q.get("line"), home, away, sport)
            if not c:
                continue
            book = str(q.get("bookmaker") or "?")

            cl = None
            for cc in clusters:
                if event_matches(sport, home, away, cc["sport"], cc["home"], cc["away"]):
                    cl = cc
                    break
            if cl is None:
                cl = {"sport": sport, "home": home, "away": away, "markets": {}}
                clusters.append(cl)
            if len(home) > len(cl["home"]):
                cl["home"] = home
            if len(away) > len(cl["away"]):
                cl["away"] = away
            if cl["sport"] in ("?", "") and sport not in ("?", ""):
                cl["sport"] = sport          # převezmi známý sport (kvůli párování)

            m = cl["markets"].setdefault(c["key"], {
                "type": c["type"], "subject": c["subject"], "line": c["line"],
                "codes": defaultdict(dict)})
            prev = m["codes"][c["code"]]
            if book not in prev or odds > prev[book]:
                prev[book] = odds
        except Exception:
            continue

    out = {"events": []}
    for c in clusters:
        ev = {"sport": c["sport"],
              "event": f"{c['home']} – {c['away']}", "markets": []}
        for mk, m in c["markets"].items():
            if m["type"] == "RESULT":
                # 1X2 (s remízou) vs WINNER2 (bez) podle sportu ZÁPASU
                two = _canon.is_two_way(c["sport"])
                req = {"1", "2"} if two else {"1", "X", "2"}
                disp_type = "WINNER2" if two else "1X2"
            else:
                req = _canon.REQUIRED.get(m["type"], set())
                disp_type = m["type"]
            have = set(m["codes"].keys())
            if not req or not req.issubset(have):    # neúplný trh → vynech
                continue
            quotes = {code: dict(m["codes"][code]) for code in req}
            # SANITACE: zahoď sázkovku, jejíž VLASTNÍ kurzy na tomhle trhu dají
            # Σ < 99 % (u jedné kanceláře nemožné → chyba parsování nad/pod).
            all_books = {b for code in req for b in quotes[code]}
            for b in all_books:
                own = [quotes[code][b] for code in req if b in quotes[code]]
                if len(own) >= 2 and sum(1.0 / o for o in own) < 0.99:
                    for code in req:
                        quotes[code].pop(b, None)
            if any(not quotes[code] for code in req):  # po sanaci chybí strana
                continue
            ev["markets"].append({
                "type": disp_type, "line": m["line"],
                "market": _canon.label(disp_type, m["subject"], m["line"]),
                "quotes": quotes,
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
