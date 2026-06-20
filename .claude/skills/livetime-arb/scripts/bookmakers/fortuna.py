#!/usr/bin/env python3
"""
Fortuna (iFortuna CZ) adaptér (best-effort kostra).

Live nabídka jede přes interní API SPA na ifortuna.cz. Endpoint si ověř
v DevTools a vlož do FORTUNA_LIVE_URL; jinak adaptér vrátí [].
"""

from __future__ import annotations

import os
from .base import Bookmaker, get_json, log


class Fortuna(Bookmaker):
    name = "fortuna"

    LIVE_URL = os.environ.get("FORTUNA_LIVE_URL", "")

    def fetch_live(self, sport: str) -> list:
        if not self.LIVE_URL:
            log("Fortuna: nastav FORTUNA_LIVE_URL nebo zadej kurzy ručně.")
            return []
        data = get_json(self.LIVE_URL)
        if not data:
            return []
        try:
            return self.parse(data, sport)
        except Exception as e:                    # noqa: BLE001
            log(f"Fortuna parse selhal: {e}")
            return []

    def parse(self, data: dict, sport: str) -> list:
        quotes = []
        for ev in data.get("events", data.get("Events", [])):
            home = ev.get("home", ev.get("participant1", "?"))
            away = ev.get("away", ev.get("participant2", "?"))
            for m in ev.get("markets", ev.get("Markets", [])):
                line = m.get("line", m.get("value"))
                for o in m.get("odds", m.get("Odds", [])):
                    quotes.append(self.quote(
                        sport=sport, home=home, away=away,
                        market=m.get("name", m.get("Name", "?")),
                        outcome=o.get("name", o.get("Name", "?")),
                        odds=o.get("value", o.get("Value")),
                        line=line,
                    ))
        return quotes
