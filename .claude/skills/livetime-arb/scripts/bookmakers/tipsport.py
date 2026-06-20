#!/usr/bin/env python3
"""
Tipsport adaptér.

POZOR: Tipsport nemá veřejné, dokumentované API. Live nabídka jede přes
interní REST/websocket, který se mění a může vyžadovat cookies/region CZ.
Tenhle adaptér je proto best-effort kostra:

  1) zkusí volitelný endpoint (TIPSPORT_LIVE_URL z prostředí),
  2) když nic nedostane, vrátí [] a sken pokračuje dál.

`parse(data)` ukazuje, jak z očekávaného JSONu udělat kotace —
uprav podle reálné odpovědi, kterou si ověříš v DevTools (Network).
"""

from __future__ import annotations

import os
from .base import Bookmaker, get_json, log


class Tipsport(Bookmaker):
    name = "tipsport"

    # Endpoint si ověř v prohlížeči (DevTools → Network → XHR na live stránce).
    LIVE_URL = os.environ.get("TIPSPORT_LIVE_URL", "")

    def fetch_live(self, sport: str) -> list:
        if not self.LIVE_URL:
            log("Tipsport: nastav TIPSPORT_LIVE_URL nebo zadej kurzy ručně.")
            return []
        data = get_json(self.LIVE_URL)
        if not data:
            return []
        try:
            return self.parse(data, sport)
        except Exception as e:                    # noqa: BLE001
            log(f"Tipsport parse selhal: {e}")
            return []

    def parse(self, data: dict, sport: str) -> list:
        """Vzorová transformace -> uprav podle reálné struktury."""
        quotes = []
        for ev in data.get("matches", data.get("events", [])):
            home = ev.get("home") or ev.get("participantHome", "?")
            away = ev.get("away") or ev.get("participantAway", "?")
            for m in ev.get("markets", []):
                line = m.get("line")
                for o in m.get("outcomes", m.get("odds", [])):
                    quotes.append(self.quote(
                        sport=sport, home=home, away=away,
                        market=m.get("name", "?"),
                        outcome=o.get("name", o.get("type", "?")),
                        odds=o.get("odds", o.get("value")),
                        line=line,
                    ))
        return quotes
