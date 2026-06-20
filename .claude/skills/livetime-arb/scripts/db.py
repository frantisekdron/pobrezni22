#!/usr/bin/env python3
"""
db.py — vlastní lokální databáze kurzů (SQLite, bez závislostí).

Ukládá kotace s časovou značkou, takže máme historii a můžeme:
  - skenovat arbitráže/value bety nad aktuálním snapshotem,
  - vidět, jak se kurz hýbal (důležité pro live),
  - vést deník vsazených arbitráží (P/L).

Tabulky:
  quotes(id, ts, bookmaker, sport, home, away, market, line, outcome, odds)
  bets(id, ts, event, market, legs_json, total, payout, profit, margin, status)
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from contextlib import contextmanager

DB_PATH = os.environ.get(
    "LIVETIME_DB",
    os.path.join(os.path.dirname(__file__), "..", "data", "odds.db"),
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS quotes (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    ts        REAL NOT NULL,
    bookmaker TEXT NOT NULL,
    sport     TEXT,
    home      TEXT,
    away      TEXT,
    market    TEXT,
    line      REAL,
    outcome   TEXT,
    odds      REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_quotes_recent ON quotes(ts);
CREATE INDEX IF NOT EXISTS ix_quotes_match  ON quotes(sport, home, away, market);

CREATE TABLE IF NOT EXISTS bets (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    ts        REAL NOT NULL,
    event     TEXT,
    market    TEXT,
    legs_json TEXT,
    total     REAL,
    payout    REAL,
    profit    REAL,
    margin    REAL,
    status    TEXT DEFAULT 'open'   -- open / won / settled / voided
);
"""


@contextmanager
def connect(path: str = None):
    p = path or DB_PATH
    os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
    con = sqlite3.connect(p)
    con.row_factory = sqlite3.Row
    try:
        con.executescript(SCHEMA)
        yield con
        con.commit()
    finally:
        con.close()


def insert_quotes(quotes: list, path: str = None) -> int:
    """Uloží list kotací (dict). Vrací počet vložených."""
    ts = time.time()
    rows = [(
        q.get("ts", ts), q.get("bookmaker", "?"), q.get("sport"),
        q.get("home"), q.get("away"), q.get("market"),
        q.get("line"), q.get("outcome"), float(q["odds"]),
    ) for q in quotes]
    with connect(path) as con:
        con.executemany(
            "INSERT INTO quotes(ts,bookmaker,sport,home,away,market,line,"
            "outcome,odds) VALUES(?,?,?,?,?,?,?,?,?)", rows)
    return len(rows)


def recent_quotes(max_age_sec: float = 600, path: str = None) -> list:
    """Vrátí kotace ne starší než max_age_sec (default 10 min) jako list dict."""
    cutoff = time.time() - max_age_sec
    with connect(path) as con:
        cur = con.execute(
            "SELECT bookmaker,sport,home,away,market,line,outcome,odds,ts "
            "FROM quotes WHERE ts >= ? ORDER BY ts DESC", (cutoff,))
        return [dict(r) for r in cur.fetchall()]


def log_bet(bet: dict, path: str = None) -> int:
    with connect(path) as con:
        cur = con.execute(
            "INSERT INTO bets(ts,event,market,legs_json,total,payout,profit,"
            "margin,status) VALUES(?,?,?,?,?,?,?,?,?)",
            (time.time(), bet.get("event"), bet.get("market"),
             json.dumps(bet.get("legs", []), ensure_ascii=False),
             bet.get("total"), bet.get("payout"), bet.get("profit"),
             bet.get("margin"), bet.get("status", "open")))
        return cur.lastrowid


def stats(path: str = None) -> dict:
    with connect(path) as con:
        q = con.execute("SELECT COUNT(*) n, MAX(ts) last FROM quotes").fetchone()
        b = con.execute(
            "SELECT COUNT(*) n, COALESCE(SUM(profit),0) pnl FROM bets").fetchone()
        return {"quotes": q["n"], "last_quote_ts": q["last"],
                "bets": b["n"], "realized_pnl": b["pnl"]}


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Správa lokální DB kurzů.")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init", help="vytvoř DB")
    sub.add_parser("stats", help="statistiky DB")
    pc = sub.add_parser("clear", help="smaž staré kotace")
    pc.add_argument("--older-than", type=float, default=86400,
                    help="smaž kotace starší než N sekund (default 1 den)")
    args = p.parse_args()

    if args.cmd == "init":
        with connect():
            pass
        print(f"DB připravena: {os.path.abspath(DB_PATH)}")
    elif args.cmd == "stats":
        print(json.dumps(stats(), ensure_ascii=False, indent=2))
    elif args.cmd == "clear":
        with connect() as con:
            n = con.execute("DELETE FROM quotes WHERE ts < ?",
                            (time.time() - args.older_than,)).rowcount
        print(f"Smazáno {n} starých kotací.")
