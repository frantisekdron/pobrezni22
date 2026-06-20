#!/usr/bin/env python3
"""
parse_raw.py — generický extraktor kurzů ze syrového API JSONu sázkovek.

Sázkovky vrací kurzy v různě zanořeném JSONu. Tenhle modul JSON rekurzivně
projde, drží kontext (zápas home/away, název trhu) a vytáhne „kotace"
(výsledek + kurz + případná hranice). Funguje bez znalosti přesných názvů
polí — hledá podle běžných klíčů. Není 100% (názvy trhů se napříč sázkovkami
liší), ale rozjede tok dat; přesné mapování se doladí na reálných datech.
"""

from __future__ import annotations
import re

ODDS_KEYS = {"odds", "oddsdecimal", "decimalodds", "price", "rate", "oddsvalue",
             "koeficient", "kurz", "decimal", "oddvalue", "currentodds"}
NAME_KEYS = {"name", "label", "caption", "selectionname", "oddsname", "shortname",
             "outcomename", "betname", "title", "type", "headername", "selname"}
MARKET_CHILD_KEYS = {"selections", "outcomes", "odds", "selectionlist", "oddslist",
                     "items", "rows", "runners", "bets", "betoffers", "events"}
MARKET_NAME_KEYS = ("marketname", "markettype", "templatename", "criterion",
                    "marketdescription", "name", "caption", "title", "label")
HOME_KEYS = {"homename", "home", "participanthome", "competitor1", "team1",
             "hometeam", "name1", "homecompetitor"}
AWAY_KEYS = {"awayname", "away", "participantaway", "competitor2", "team2",
             "awayteam", "name2", "awaycompetitor"}
# jen explicitní klíče zápasu (NE generické name/caption — to mají i trhy)
EVENT_NAME_KEYS = ("eventname", "fixturename", "matchname", "participantsname")
LINE_KEYS = {"handicap", "line", "sbv", "specialbetvalue", "hodnota", "goals",
             "total", "threshold", "value", "hranicehodnota"}


def fnum(x):
    try:
        return float(str(x).replace(",", "."))
    except Exception:
        return None


def _odds(d, km):
    for kl in ODDS_KEYS:
        if kl in km:
            f = fnum(d[km[kl]])
            if f and 1.01 <= f <= 1000:
                return f
    return None


def _name(d, km):
    for kl in NAME_KEYS:
        if kl in km:
            v = d[km[kl]]
            if isinstance(v, str) and v.strip() and len(v) < 60:
                return v.strip()
    return None


def _line(d, km, oddsval):
    for kl in LINE_KEYS:
        if kl in km:
            f = fnum(d[km[kl]])
            if f is not None and -300 < f < 300 and f != oddsval:
                return f
    return None


def _event(d, km):
    h = a = None
    for kl in HOME_KEYS:
        if kl in km and isinstance(d[km[kl]], str) and d[km[kl]].strip():
            h = d[km[kl]].strip()
    for kl in AWAY_KEYS:
        if kl in km and isinstance(d[km[kl]], str) and d[km[kl]].strip():
            a = d[km[kl]].strip()
    if h and a:
        return h, a
    for kl in EVENT_NAME_KEYS:
        if kl in km and isinstance(d[km[kl]], str):
            s = d[km[kl]]
            # oddělovač MUSÍ být "vs"/"–"/"-" se spacy (ne holé "v" uvnitř názvu)
            parts = re.split(r"\s+(?:vs\.?|–|—|·|-)\s+", s)
            if len(parts) == 2 and all(len(x.strip()) > 1 for x in parts) \
                    and not s[:2].strip().isdigit():
                return parts[0].strip(), parts[1].strip()
    return None, None


def _market(d, km):
    if not any(k in km and isinstance(d[km[k]], list) for k in MARKET_CHILD_KEYS):
        return None
    for kl in MARKET_NAME_KEYS:
        if kl in km:
            v = d[km[kl]]
            if isinstance(v, str) and v.strip():
                return v.strip()[:60]
            if isinstance(v, dict):                 # např. Kambi criterion.label
                for kk in ("label", "name", "englishlabel"):
                    if isinstance(v.get(kk), str) and v[kk].strip():
                        return v[kk].strip()[:60]
    return None


def extract(book, obj, sport="?"):
    quotes = []

    def walk(node, ctx):
        if isinstance(node, dict):
            km = {k.lower(): k for k in node}
            h, a = _event(node, km)
            if not h:
                # zápas bývá v sourozeneckém bloku (event/match/fixture) vedle markets
                for v in node.values():
                    if isinstance(v, dict):
                        h2, a2 = _event(v, {k.lower(): k for k in v})
                        if h2:
                            h, a = h2, a2
                            break
            if h:
                ctx = dict(ctx, home=h, away=a)
            mk = _market(node, km)
            if mk:
                ctx = dict(ctx, market=mk)
            ov = _odds(node, km)
            nm = _name(node, km)
            if ov and nm:
                quotes.append({
                    "bookmaker": book, "sport": ctx.get("sport", sport),
                    "home": ctx.get("home", "?"), "away": ctx.get("away", "?"),
                    "market": ctx.get("market", "?"), "line": _line(node, km, ov),
                    "outcome": nm, "odds": ov,
                })
            for v in node.values():
                walk(v, ctx)
        elif isinstance(node, list):
            for v in node:
                walk(v, ctx)

    walk(obj, {"home": "?", "away": "?", "market": "?", "sport": sport})

    seen, out = set(), []
    for q in quotes:
        k = (q["home"], q["away"], q["market"], q["outcome"], q["odds"])
        if k not in seen:
            seen.add(k)
            out.append(q)
    return out


if __name__ == "__main__":
    import json, sys
    data = json.load(open(sys.argv[1]) if len(sys.argv) > 1 else sys.stdin)
    book = sys.argv[2] if len(sys.argv) > 2 else "?"
    qs = extract(book, data)
    print(f"vytaženo {len(qs)} kotací")
    for q in qs[:40]:
        print(f"  [{q['market']}] {q['home']}-{q['away']} · {q['outcome']} = {q['odds']}"
              + (f" (line {q['line']})" if q['line'] is not None else ""))
