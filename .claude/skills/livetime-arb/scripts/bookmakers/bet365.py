#!/usr/bin/env python3
"""
bet365 adaptér (best-effort kostra).

bet365 je nejtěžší: live data tečou přes vlastní binární websocket protokol
(/zap/) za silnou ochranou. Spolehlivý automatický scraping prakticky
vyžaduje řízený prohlížeč (Playwright) nebo placené odds API.

Tento adaptér proto defaultně NEscrapuje a doporučí:
  - buď zadat kurzy z bet365 ručně (jako na snímku),
  - nebo nasměrovat na vlastní/placený feed přes BET365_LIVE_URL
    (JSON ve formátu, který umí parse()).
"""

from __future__ import annotations

import os
from .base import Bookmaker, get_json, log


class Bet365(Bookmaker):
    name = "bet365"

    LIVE_URL = os.environ.get("BET365_LIVE_URL", "")

    def fetch_live(self, sport: str) -> list:
        if not self.LIVE_URL:
            log("bet365: automatický feed není nastaven (BET365_LIVE_URL). "
                "Zadej kurzy z bet365 ručně – bývá to nejsilnější strana arb.")
            return []
        data = get_json(self.LIVE_URL)
        if not data:
            return []
        try:
            return self.parse(data, sport)
        except Exception as e:                    # noqa: BLE001
            log(f"bet365 parse selhal: {e}")
            return []

    def parse(self, data: dict, sport: str) -> list:
        quotes = []
        for ev in data.get("events", []):
            home = ev.get("home", "?")
            away = ev.get("away", "?")
            for m in ev.get("markets", []):
                line = m.get("line")
                for o in m.get("outcomes", []):
                    quotes.append(self.quote(
                        sport=sport, home=home, away=away,
                        market=m.get("name", "?"),
                        outcome=o.get("name", "?"),
                        odds=o.get("odds"),
                        line=line,
                    ))
        return quotes
