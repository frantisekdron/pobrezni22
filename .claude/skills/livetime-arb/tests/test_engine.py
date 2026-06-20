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
import canon                                          # noqa: E402


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
    """1X2 3.50/3.60/3.90 => ~21.97 % arb (max_margin zvednut, jinak filtr skryje)."""
    a = find_arb("fotbal", "A-B", "1X2",
                 {"1": {"b": 3.50}, "X": {"b2": 3.60}, "2": {"b3": 3.90}}, 1000,
                 max_margin=1.0)
    assert approx(a.margin * 100, 21.97, 0.1)
    assert len(a.legs) == 3


def test_filter_same_bookmaker():
    """Obě nohy u jedné sázkovky = chyba dat → None."""
    a = find_arb("x", "y", "O/U",
                 {"Over": {"betano": 3.50}, "Under": {"betano": 3.50}}, 1000)
    assert a is None


def test_filter_absurd_margin():
    """Marže > 20 % (default strop) = nejspíš chyba → None, i napříč sázkovkami."""
    a = find_arb("x", "y", "m",
                 {"A": {"book1": 3.5}, "B": {"book2": 3.5}}, 1000)
    assert a is None
    # se zvednutým stropem se zobrazí
    assert find_arb("x", "y", "m",
                    {"A": {"book1": 3.5}, "B": {"book2": 3.5}}, 1000,
                    max_margin=1.0) is not None


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
    assert mkt["type"] == "OU"                 # kanonický typ
    assert "OVER" in mkt["quotes"] and "UNDER" in mkt["quotes"]
    assert mkt["quotes"]["OVER"]["tipsport"] == 3.00
    assert mkt["quotes"]["UNDER"]["bet365"] == 1.83


def test_canon_blocks_garbage():
    """Betbuilder / exotické trhy se nekanonizují (nearbitrážovatelné)."""
    assert canon.canon("Góly Dembele (Betbuilder: 3 příležitosti)", "3 příležitosti", None) is None
    assert canon.canon("Asijský handicap", "Německo -0.75", None) is None
    assert canon.canon("Přesný výsledek", "2 - 1", None) is None


def test_canon_over_under():
    """Nad/Pod gólů → OU se subjektem goals a hranicí."""
    c = canon.canon("Počet gólů v zápasu", "Více než 2.5", 2.5)
    assert c["type"] == "OU" and c["code"] == "OVER" and c["subject"] == "goals" and c["line"] == 2.5
    c = canon.canon("Počet rohů v zápasu", "Méně než 9.5", None)
    assert c["type"] == "OU" and c["code"] == "UNDER" and c["subject"] == "corners" and c["line"] == 9.5
    # góly a rohy se NESMÍ spárovat (jiný subjekt)
    assert canon.canon("Počet gólů", "Nad 2.5", 2.5)["key"] != canon.canon("Počet rohů", "Nad 2.5", 2.5)["key"]


def test_merge_drops_incomplete_market():
    """Trh jen s jednou stranou (Over bez Under) se nezobrazí."""
    merged = merge_quotes([
        {"bookmaker": "tipsport", "sport": "fotbal", "home": "A", "away": "B",
         "market": "Počet rohů v zápasu", "outcome": "Nad 9.5", "odds": 1.9}])
    assert merged["events"] == []          # neúplný trh → žádný zápas


def test_real_cross_book_arb_via_merge():
    """O/U gólů 2.5 napříč dvěma sázkovkami → platná arbitráž."""
    merged = merge_quotes([
        {"bookmaker": "tipsport", "sport": "fotbal", "home": "Slavia", "away": "Sparta",
         "market": "Počet gólů v zápasu", "outcome": "Více než 2.5", "odds": 2.10},
        {"bookmaker": "fortuna", "sport": "fotbal", "home": "Slavia", "away": "Sparta",
         "market": "Počet gólů v zápasu", "outcome": "Méně než 2.5", "odds": 2.05}])
    m = merged["events"][0]["markets"][0]
    a = find_arb("fotbal", "Slavia – Sparta", m["market"], m["quotes"], 1000)
    assert a is not None and a.margin > 0
    assert len({l.bookmaker for l in a.legs}) == 2


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
