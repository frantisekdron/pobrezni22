#!/usr/bin/env python3
"""
Testy jádra livetime-arb. Spusť:
    python3 -m pytest tests/ -q
nebo bez pytestu:
    python3 tests/test_engine.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from arb import Leg, compute_arb, find_arb           # noqa: E402
from analyze import fair_probs, kelly_fraction, find_value_bets  # noqa: E402
from normalize import merge_quotes, names_match, norm_outcome    # noqa: E402
from freebet import free_two_books                   # noqa: E402


def approx(a, b, tol=0.5):
    return abs(a - b) <= tol


def test_surebet_reference():
    """Referenční příklad ze snímku: 3.00 + 1.83 => 13.66 %, 379/621 Kč."""
    legs = [Leg("Nad", "tipsport", 3.00), Leg("Pod", "bet365", 1.83)]
    S, margin, legs, payout, profit = compute_arb(legs, 1000, round_to=1)
    assert approx(margin * 100, 13.66, 0.05)
    stakes = {l.outcome: l.stake for l in legs}
    assert approx(stakes["Nad"], 379, 1)
    assert approx(stakes["Pod"], 621, 1)
    assert approx(profit, 136, 2)


def test_not_an_arb():
    """1.90 + 1.90 = overround 105 % => není arbitráž (find_arb vrátí None)."""
    a = find_arb("x", "y", "m",
                 {"A": {"b1": 1.90}, "B": {"b2": 1.90}}, 1000, 0.0)
    assert a is None                # záporná marže pod práh 0 => None


def test_threeway_arb():
    """1X2 3.50/3.60/3.90 => ~21.97 % arb."""
    a = find_arb("fotbal", "A-B", "1X2",
                 {"1": {"b": 3.50}, "X": {"b2": 3.60}, "2": {"b3": 3.90}}, 1000)
    assert approx(a.margin * 100, 21.97, 0.1)
    assert len(a.legs) == 3


def test_best_odds_across_books():
    """Vybere nejvyšší kurz na každý výsledek napříč sázkovkami."""
    a = find_arb("tenis", "Z-F", "Esa",
                 {"Nad": {"tipsport": 3.00, "betano": 2.85},
                  "Pod": {"bet365": 1.83, "fortuna": 1.80}}, 1000)
    books = {l.outcome: l.bookmaker for l in a.legs}
    assert books["Nad"] == "tipsport"
    assert books["Pod"] == "bet365"


def test_fair_probs_sum_to_one():
    fp = fair_probs({"1": {"a": 2.0}, "2": {"b": 2.0}})
    assert approx(sum(fp.values()), 1.0, 0.001)


def test_kelly_positive_only_on_edge():
    # férová pravd. 0.5, kurz 2.5 => kladná výhoda => kladný Kelly
    assert kelly_fraction(2.5, 0.5) > 0
    # kurz 1.5 při férové 0.5 => záporná výhoda => Kelly 0
    assert kelly_fraction(1.5, 0.5) == 0


def test_value_bet_detection():
    vbs = find_value_bets(
        {"Nad": {"tipsport": 3.00}, "Pod": {"bet365": 1.83}},
        min_edge=0.05, bankroll=100000, kelly=0.25)
    assert len(vbs) >= 1
    assert all(v["edge"] >= 0.05 for v in vbs)


def test_fuzzy_name_matching():
    assert names_match("Alexander Zverev", "Zverev A.")
    assert names_match("A. Zverev", "Zverev Alexander")
    assert not names_match("Zverev", "Fritz")


def test_norm_outcome_with_line():
    assert norm_outcome("Nad 28.5") == "Over"
    assert norm_outcome("Pod 28.5") == "Under"
    assert norm_outcome("více než 28.5") == "Over"


def test_merge_quotes_pairs_four_books():
    quotes = [
        {"bookmaker": "tipsport", "sport": "tenis", "home": "Alexander Zverev",
         "away": "Taylor Fritz", "market": "Esa", "line": 28.5,
         "outcome": "Nad", "odds": 3.00},
        {"bookmaker": "bet365", "sport": "tenis", "home": "Zverev A.",
         "away": "Fritz T.", "market": "Aces", "line": 28.5,
         "outcome": "Pod", "odds": 1.83},
    ]
    merged = merge_quotes(quotes)
    assert len(merged["events"]) == 1          # spárováno do jednoho zápasu
    mkt = merged["events"][0]["markets"][0]
    assert "Over 28.5" in mkt["quotes"]
    assert "Under 28.5" in mkt["quotes"]


def test_freebet_two_books_profit():
    cash, profit = free_two_books(1000, 2.0, 2.1)
    assert profit > 0
    assert approx(cash, 476, 2)


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"  ✔ {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"  �’ {fn.__name__}: {e}")
    print(f"\n{len(fns)-failed}/{len(fns)} testů prošlo.")
    return failed


if __name__ == "__main__":
    sys.exit(1 if _run_all() else 0)
