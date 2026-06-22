#!/usr/bin/env python3
"""
Integrační test celého řetězce na REALISTICKÝCH datech ze 3 sázkovek:
  syrový API JSON (tvar jako Tipsport list / Fortuna / Betano-Kambi)
  → parse_raw → normalize (canon + sanitace) → arb.

Spusť: python3 tests/test_integration.py   (nebo přes pytest)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import parse_raw          # noqa: E402
import normalize          # noqa: E402
from arb import find_arb  # noqa: E402

# ── realistické tvary API ──────────────────────────────────────────────────

TIPSPORT = {"matches": [{
    "sport": "Fotbal - muži", "superSport": "Fotbal",
    "participantHome": "Plzeň", "participantVisiting": "Baník",
    "oppRows": [{"oppsTab": [
        {"label": "1", "type": "1", "odd": 1.80, "bettingEnabled": True},
        {"label": "10", "type": "1x", "odd": 1.20, "bettingEnabled": True},
        {"label": "0", "type": "x", "odd": 3.60, "bettingEnabled": True},
        {"label": "02", "type": "x2", "odd": 2.00, "bettingEnabled": True},
        {"label": "2", "type": "2", "odd": 4.50, "bettingEnabled": True},
    ]}]}]}

FORTUNA = {"event": {"homeName": "Plzeň", "awayName": "Baník"}, "markets": [
    {"name": "Výsledek zápasu", "events": [
        {"name": "1", "odds": "1.85"}, {"name": "Remíza", "odds": "3.50"},
        {"name": "2", "odds": "4.60"}]},
    {"name": "Počet gólů v zápasu", "events": [
        {"name": "Více než 2.5", "odds": "2.10", "value": 2.5},
        {"name": "Méně než 2.5", "odds": "1.80", "value": 2.5}]},
    # betbuilder se musí zahodit
    {"name": "Betbuilder: 3 příležitosti", "events": [
        {"name": "kombinace", "odds": "5.00"}]},
]}

BETANO = {"events": [{"homeName": "Plzeň", "awayName": "Baník", "betOffers": [
    {"criterion": {"label": "Výsledek zápasu"}, "outcomes": [
        {"label": "1", "odds": 1.90}, {"label": "X", "odds": 3.40},
        {"label": "2", "odds": 4.30}]},
    {"criterion": {"label": "Počet gólů v zápasu"}, "outcomes": [
        {"label": "Více než 2.5", "odds": 1.95, "line": 2.5},
        {"label": "Méně než 2.5", "odds": 1.95, "line": 2.5}]},
]}]}


def _pipeline():
    quotes = (parse_raw.extract("tipsport", TIPSPORT)
              + parse_raw.extract("fortuna", FORTUNA)
              + parse_raw.extract("betano", BETANO))
    events = normalize.merge_quotes(quotes)
    arbs = []
    for ev in events["events"]:
        for m in ev["markets"]:
            a = find_arb(ev["sport"], ev["event"], m["market"], m["quotes"], 1000)
            if a:
                arbs.append(a)
    return quotes, events, arbs


def test_parsers_produce_quotes():
    q = (parse_raw.extract("tipsport", TIPSPORT)
         + parse_raw.extract("fortuna", FORTUNA)
         + parse_raw.extract("betano", BETANO))
    books = {x["bookmaker"] for x in q}
    assert books == {"tipsport", "fortuna", "betano"}


def test_one_event_three_books():
    _, events, _ = _pipeline()
    assert len(events["events"]) == 1
    ev = events["events"][0]
    assert "Plzeň" in ev["event"] and "Baník" in ev["event"]


def test_betbuilder_dropped():
    _, events, _ = _pipeline()
    labels = [m["market"] for m in events["events"][0]["markets"]]
    assert not any("uilder" in s or "íležitost" in s for s in labels)


def test_1x2_present_no_arb():
    _, events, arbs = _pipeline()
    mtypes = {m["type"] for m in events["events"][0]["markets"]}
    assert "1X2" in mtypes
    # 1X2 přes 3 efektivní knihy nemá být surebet
    assert not any(a.market.startswith("Výsledek") for a in arbs)


def test_goals_ou_arb_cross_book():
    _, _, arbs = _pipeline()
    ou = [a for a in arbs if "ól" in a.market]   # góly nad/pod
    assert len(ou) == 1
    a = ou[0]
    assert a.margin > 0
    assert len({l.bookmaker for l in a.legs}) == 2     # napříč 2 sázkovkami
    # nohy = OVER (fortuna 2.10) a UNDER (betano 1.95)
    legs = {l.outcome: (l.bookmaker, l.odds) for l in a.legs}
    assert legs["OVER"] == ("fortuna", 2.10)
    assert legs["UNDER"] == ("betano", 1.95)


def _run():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    bad = 0
    for fn in fns:
        try:
            fn()
            print(f"  ✔ {fn.__name__}")
        except AssertionError as e:
            bad += 1
            print(f"  ✘ {fn.__name__}: {e}")
    q, ev, arbs = _pipeline()
    print(f"\n  kotací: {len(q)} · zápasů: {len(ev['events'])} · "
          f"trhů: {len(ev['events'][0]['markets'])} · surebetů: {len(arbs)}")
    for a in arbs:
        print(f"    🟢 +{a.margin*100:.2f}% {a.market} | " +
              ", ".join(f"{l.outcome}@{l.bookmaker} {l.odds}" for l in a.legs))
    print(f"\n  {len(fns)-bad}/{len(fns)} prošlo")
    return bad


if __name__ == "__main__":
    sys.exit(1 if _run() else 0)
