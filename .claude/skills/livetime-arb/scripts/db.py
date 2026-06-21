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
    status    TEXT DEFAULT 'open'   -- open / won / lost / void / settled
);

CREATE TABLE IF NOT EXISTS bankroll (
    bookmaker  TEXT PRIMARY KEY,
    balance    REAL DEFAULT 0,
    max_stake  REAL DEFAULT 0,
    turnover   REAL DEFAULT 0,
    pnl        REAL DEFAULT 0,
    mug        INTEGER DEFAULT 0,
    sharp      INTEGER DEFAULT 0,
    updated_at REAL
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


def _f(x):
    try:
        return float(str(x).replace(",", "."))
    except (TypeError, ValueError):
        return None


def insert_quotes(quotes: list, path: str = None) -> int:
    """Uloží list kotací (dict). Vadné (nečíselný kurz) přeskočí. Vrací počet."""
    ts = time.time()
    rows = []
    for q in quotes:
        odds = _f(q.get("odds"))
        if odds is None or not (1.01 <= odds <= 1000):
            continue                      # přeskoč vadný/nesmyslný kurz
        rows.append((
            q.get("ts", ts), str(q.get("bookmaker") or "?"),
            (str(q.get("sport")) if q.get("sport") is not None else None),
            (str(q.get("home")) if q.get("home") is not None else None),
            (str(q.get("away")) if q.get("away") is not None else None),
            (str(q.get("market")) if q.get("market") is not None else None),
            _f(q.get("line")),
            (str(q.get("outcome")) if q.get("outcome") is not None else None),
            odds,
        ))
    if not rows:
        return 0
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


def list_bets(path: str = None) -> list:
    with connect(path) as con:
        cur = con.execute("SELECT * FROM bets ORDER BY ts DESC")
        rows = []
        for r in cur.fetchall():
            d = dict(r)
            try:
                d["legs"] = json.loads(d.pop("legs_json") or "[]")
            except ValueError:
                d["legs"] = []
            rows.append(d)
        return rows


def set_bet_status(bet_id: int, status: str, path: str = None) -> bool:
    with connect(path) as con:
        cur = con.execute("UPDATE bets SET status=? WHERE id=?",
                          (status, bet_id))
        return cur.rowcount > 0


def get_bankroll(path: str = None) -> list:
    with connect(path) as con:
        cur = con.execute("SELECT bookmaker,balance,max_stake,turnover,pnl,"
                          "mug,sharp,updated_at FROM bankroll ORDER BY bookmaker")
        return [dict(r) for r in cur.fetchall()]


def upsert_bankroll(row: dict, path: str = None):
    import time as _t
    with connect(path) as con:
        con.execute(
            "INSERT INTO bankroll(bookmaker,balance,max_stake,turnover,pnl,"
            "mug,sharp,updated_at) VALUES(?,?,?,?,?,?,?,?) "
            "ON CONFLICT(bookmaker) DO UPDATE SET balance=excluded.balance,"
            "max_stake=excluded.max_stake,turnover=excluded.turnover,"
            "pnl=excluded.pnl,mug=excluded.mug,sharp=excluded.sharp,"
            "updated_at=excluded.updated_at",
            (row["bookmaker"], row.get("balance", 0), row.get("max_stake", 0),
             row.get("turnover", 0), row.get("pnl", 0), row.get("mug", 0),
             row.get("sharp", 0), _t.time()))


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
