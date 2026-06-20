#!/usr/bin/env python3
"""
base.py — společné rozhraní adaptérů sázkovek.

Každý adaptér umí vrátit list "kotací" (viz normalize.py) z live nabídky
daného sportu. Fetch přes sázkovkové stránky je křehký (Cloudflare,
geo-blok, websockety, přihlášení), takže každý adaptér:
  - vrací [] a vypíše varování, když se nepodaří načíst,
  - má dokumentovaný endpoint/postup v docstringu,
  - nikdy neshodí celý sken (chyby jen zaloguje).

Pozn.: Hlavní, vždy funkční cesta skillu je nechat odhady kurzů nasbírat
Clauda (WebFetch) nebo je vložit ručně a spustit arb.py. Adaptéry jsou
volitelné zrychlení, ne tvrdá závislost.
"""

from __future__ import annotations

import sys
import urllib.request
import urllib.error
import json as _json


DEFAULT_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/124.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "cs-CZ,cs;q=0.9,en;q=0.8",
}


def log(msg: str):
    print(f"[livetime-arb] {msg}", file=sys.stderr)


def http_get(url: str, headers: dict = None, timeout: float = 12.0):
    """GET -> (status, text). Při chybě (status, None)."""
    h = dict(DEFAULT_HEADERS)
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:                       # noqa: BLE001
        log(f"GET {url} selhal: {e}")
        return 0, None


def get_json(url: str, headers: dict = None, timeout: float = 12.0):
    status, text = http_get(url, headers, timeout)
    if not text:
        return None
    try:
        return _json.loads(text)
    except ValueError:
        log(f"Odpověď z {url} není JSON (status {status}).")
        return None


class Bookmaker:
    """Předek adaptérů. Potomek přepíše name a fetch_live()."""

    name = "base"

    def fetch_live(self, sport: str) -> list:
        """Vrátí list kotací (dict) pro daný sport. Default: nic."""
        raise NotImplementedError

    def quote(self, sport, home, away, market, outcome, odds, line=None) -> dict:
        return {
            "bookmaker": self.name,
            "sport": sport,
            "home": home, "away": away,
            "market": market,
            "line": line,
            "outcome": outcome,
            "odds": float(odds),
        }
