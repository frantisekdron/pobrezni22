#!/usr/bin/env python3
"""
Betano adaptér (best-effort kostra).

Betano CZ (Kaizen Gaming) má vlastní sportsbook backend; live nabídka jede
přes interní API + websockety, často chráněné. Adaptér zkusí volitelný
BETANO_LIVE_URL a jinak vrátí [].
"""

from __future__ import annotations

import os
from .base import Bookmaker, get_json, log


class Betano(Bookmaker):
    name = "betano"

    LIVE_URL = os.environ.get("BETANO_LIVE_URL", "")

    def fetch_live(self, sport: str) -> list:
        if not self.LIVE_URL:
            log("Betano: nastav BETANO_LIVE_URL nebo zadej kurzy ručně.")
            return []
        data = get_json(self.LIVE_URL)
        if not data:
            return []
        try:
            return self.parse(data, sport)
        except Exception as e:                    # noqa: BLE001
            log(f"Betano parse selhal: {e}")
            return []

    def parse(self, data: dict, sport: str) -> list:
        quotes = []
        for ev in data.get("events", data.get("data", [])):
            home = ev.get("homeName") or ev.get("home", "?")
            away = ev.get("awayName") or ev.get("away", "?")
            for m in ev.get("markets", []):
                line = m.get("handicap", m.get("line"))
                for s in m.get("selections", m.get("outcomes", [])):
                    quotes.append(self.quote(
                        sport=sport, home=home, away=away,
                        market=m.get("name", m.get("type", "?")),
                        outcome=s.get("name", "?"),
                        odds=s.get("price", s.get("odds")),
                        line=line,
                    ))
        return quotes
