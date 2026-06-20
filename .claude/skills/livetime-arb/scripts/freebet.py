#!/usr/bin/env python3
"""
freebet.py — bezztrátová extrakce hodnoty z bonusů / free betů (matched betting).

Sázkovky rozdávají uvítací bonusy a free bety. Ty jdou matematicky převést
na (skoro) jistý zisk tím, že na druhé sázkovce vsadíš opačný výsledek.
Tohle je v praxi NEJSTABILNĚJŠÍ +EV cesta (bookmaker to čeká), na rozdíl od
lovení 20% surebetů, které bývají chyba a sázkovka je stornuje.

Dva režimy:

  free2  — FREE BET (stake se nevrací, "SNR") na sázkovce A na výsledek X,
           hotovost na opačný výsledek u sázkovky B.
           Použij, když nemáš sázkovou burzu (v ČR běžné).

  lay    — kvalifikační/free sázka na bookmakerovi + LAY na burze (Betfair…).
           commission = provize burzy (např. 0.02 = 2 %).
"""

from __future__ import annotations

import argparse


def free_two_books(free_stake, odds_a, odds_b):
    """Free bet (SNR) na A @ odds_a; hotovost na opačný výsledek na B @ odds_b.
    Vrátí (cash_na_B, zisk)."""
    cash = free_stake * (odds_a - 1) / odds_b
    profit = cash * (odds_b - 1)            # zisk je v obou scénářích stejný
    return cash, profit


def lay_freebet(free_stake, back_odds, lay_odds, commission, snr=True):
    """Free bet (SNR) na bookmakerovi @ back_odds, lay na burze @ lay_odds.
    Vrátí (lay_stake, závazek, zisk)."""
    # SNR free bet: při výhře získáš (back_odds-1)*stake
    lay_stake = free_stake * (back_odds - (0 if snr else 0)) / (
        lay_odds - commission)
    if snr:
        lay_stake = free_stake * (back_odds - 1) / (lay_odds - commission)
    liability = lay_stake * (lay_odds - 1)
    profit = lay_stake * (1 - commission)   # zisk při prohře sázky (lay vyhraje)
    return lay_stake, liability, profit


def lay_qualifying(back_stake, back_odds, lay_odds, commission):
    """Kvalifikační (reálná) sázka, kterou děláš kvůli odemčení free betu.
    Vrátí (lay_stake, závazek, čistá ztráta/zisk z kvalifikace)."""
    lay_stake = back_stake * back_odds / (lay_odds - commission)
    liability = lay_stake * (lay_odds - 1)
    # když back vyhraje: +back_stake*(back_odds-1) - liability
    # když lay vyhraje:  +lay_stake*(1-commission) - back_stake
    qual = lay_stake * (1 - commission) - back_stake
    return lay_stake, liability, qual


def main():
    p = argparse.ArgumentParser(description="Bezztrátová konverze bonusů/free betů.")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("free2", help="Free bet na A + hotovost na opačný na B")
    a.add_argument("free_stake", type=float, help="výše free betu (Kč)")
    a.add_argument("odds_a", type=float, help="kurz free betu na A")
    a.add_argument("odds_b", type=float, help="kurz opačného výsledku na B")

    l = sub.add_parser("lay", help="Free bet na bookmakerovi + lay na burze")
    l.add_argument("free_stake", type=float)
    l.add_argument("back_odds", type=float)
    l.add_argument("lay_odds", type=float)
    l.add_argument("-c", "--commission", type=float, default=0.02)

    q = sub.add_parser("qual", help="Kvalifikační sázka + lay (cena odemčení bonusu)")
    q.add_argument("back_stake", type=float)
    q.add_argument("back_odds", type=float)
    q.add_argument("lay_odds", type=float)
    q.add_argument("-c", "--commission", type=float, default=0.02)

    args = p.parse_args()

    if args.cmd == "free2":
        cash, profit = free_two_books(args.free_stake, args.odds_a, args.odds_b)
        rate = profit / args.free_stake * 100
        print(f"Free bet {args.free_stake:.0f} Kč @ {args.odds_a:.2f} (A)")
        print(f"→ vsaď {cash:.0f} Kč na opačný výsledek @ {args.odds_b:.2f} (B)")
        print(f"→ jistý zisk ~{profit:.0f} Kč  ({rate:.0f} % z free betu)")
    elif args.cmd == "lay":
        ls, liab, profit = lay_freebet(
            args.free_stake, args.back_odds, args.lay_odds, args.commission)
        print(f"Free bet {args.free_stake:.0f} @ {args.back_odds:.2f}; "
              f"lay {ls:.0f} @ {args.lay_odds:.2f} (závazek {liab:.0f} Kč)")
        print(f"→ jistý zisk ~{profit:.0f} Kč "
              f"({profit/args.free_stake*100:.0f} % z free betu)")
    elif args.cmd == "qual":
        ls, liab, qual = lay_qualifying(
            args.back_stake, args.back_odds, args.lay_odds, args.commission)
        print(f"Back {args.back_stake:.0f} @ {args.back_odds:.2f}; "
              f"lay {ls:.0f} @ {args.lay_odds:.2f} (závazek {liab:.0f} Kč)")
        print(f"→ náklad kvalifikace: {qual:+.0f} Kč (malá ztráta = cena za "
              f"odemčení free betu)")


if __name__ == "__main__":
    main()
