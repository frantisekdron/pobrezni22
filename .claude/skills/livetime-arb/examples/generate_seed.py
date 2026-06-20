#!/usr/bin/env python3
"""
generate_seed.py — vygeneruje větší realistický demo dataset (events JSON).

Namíchá ~25 zápazů napříč sporty s kontrolovaným rozložením:
  - část má malý surebet (0,5–3 %) = realistické,
  - pár má větší surebet (5–15 %) = vzácné / rizikové,
  - jeden "past" 20 %+ (palpable error),
  - zbytek jen value bety nebo nic.

Spusť:  python3 examples/generate_seed.py > examples/seed_events_large.json
Determin.: seed RNG je fixní, takže výstup je stabilní.
"""

import json
import random

random.seed(42)

POOLS = {
    "fotbal": ([("Slavia", "Sparta"), ("Plzeň", "Baník"), ("Bayern", "Dortmund"),
                ("Arsenal", "Chelsea"), ("Real Madrid", "Barcelona"),
                ("Inter", "Milán"), ("PSG", "Marseille"), ("Liverpool", "Everton")],
               ["1X2", "ou_goals"]),
    "tenis": ([("Alexander Zverev", "Taylor Fritz"), ("Sinner", "Medvedev"),
               ("Alcaraz", "Djokovič"), ("Rune", "Rublev"),
               ("Swiatek", "Sabalenková")],
              ["winner2", "ou_aces", "ou_games"]),
    "basketbal": ([("Nymburk", "Brno"), ("Lakers", "Celtics"),
                   ("Real", "Barcelona")], ["ou_points", "winner2"]),
    "hokej": ([("Sparta", "Třinec"), ("Pardubice", "Vítkovice"),
               ("Boston", "Toronto")], ["1X2", "ou_goals"]),
}

BOOKS = ["tipsport", "betano", "bet365", "fortuna"]

MARKET_DEF = {
    "1X2": ("Výsledek zápasu (1X2)", ["1", "X", "2"], None),
    "winner2": ("Vítěz zápasu", ["1", "2"], None),
    "ou_goals": ("Počet gólů", ["Nad", "Pod"], [2.5, 3.5]),
    "ou_aces": ("Esa v zápase", ["Nad", "Pod"], [22.5, 28.5]),
    "ou_games": ("Počet gemů", ["Nad", "Pod"], [22.5]),
    "ou_points": ("Celkem bodů", ["Nad", "Pod"], [158.5, 210.5]),
}


def fair_odds(n):
    """Náhodné férové pravd. n výsledků -> férové kurzy (bez marže)."""
    ps = [random.uniform(0.2, 1.0) for _ in range(n)]
    s = sum(ps)
    ps = [p / s for p in ps]
    return [1.0 / p for p in ps]


def book_odds(fair, margin, noise):
    """Kurz sázkovky = fér / (1+margin) s malým šumem, zaokr. na 0.01."""
    o = fair / (1 + margin) * random.uniform(1 - noise, 1 + noise)
    return round(max(1.01, o), 2)


def make_event(sport, pair, mkey, scenario):
    label, outcomes, lines = MARKET_DEF[mkey]
    line = random.choice(lines) if lines else None
    fo = fair_odds(len(outcomes))
    market_name = label + (f" – hranice {line:g}" if line is not None else "")

    # ne každá sázkovka nabízí každý trh (jako v praxi) -> míň náhodných arbů
    covering = random.sample(BOOKS, random.randint(2, 4))
    quotes = {}
    for i, oc in enumerate(outcomes):
        key = f"{oc} {line:g}" if line is not None else oc
        quotes[key] = {}
        for b in covering:
            # většina sázkovek má marži ~6,5 %
            quotes[key][b] = book_odds(fo[i], 0.065, 0.012)
        # injektuj scénář na JEDEN výsledek u JEDNÉ sázkovky (vyšší kurz)
        if scenario and i == 0:
            boost = {"small": 0.09, "big": 0.18, "trap": 0.40,
                     "value": 0.07}[scenario]
            b = random.choice(covering)
            quotes[key][b] = round(fo[i] * (1 + boost), 2)

    return {"sport": sport, "event": f"{pair[0]} – {pair[1]}",
            "markets": [{"market": market_name, "quotes": quotes}]}


def main():
    scenarios = (["small"] * 6 + ["big"] * 2 + ["trap"] * 1 +
                 ["value"] * 8 + [None] * 8)
    random.shuffle(scenarios)

    events = []
    used = set()
    sports = list(POOLS.keys())
    for sc in scenarios:
        sport = random.choice(sports)
        pairs, mkeys = POOLS[sport]
        for _ in range(20):
            pair = random.choice(pairs)
            mkey = random.choice(mkeys)
            sig = (sport, pair, mkey)
            if sig not in used:
                used.add(sig)
                break
        ev = make_event(sport, pair, mkey, sc)
        if sc == "trap":
            ev["markets"][0]["market"] += " — POZOR: extrémní kurz = pravděpodobně chyba"
        events.append(ev)

    print(json.dumps({"_comment": "Vygenerováno generate_seed.py (seed=42). "
                      "ZÁMĚRNĚ bohatý demo set pro testování řazení/filtrů UI — "
                      "v realitě je surebetů řádově míň. Mix surebetů, value betů a pasti.",
                      "events": events}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
