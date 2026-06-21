#!/usr/bin/env python3
"""
Livetime Arb Dashboard — backend (čistá Python stdlib, ŽÁDNÉ závislosti).

Spuštění:
    python3 webapp/server.py            # http://localhost:8000
    PORT=9000 python3 webapp/server.py

Servíruje SPA (webapp/static/index.html) a JSON API. Výpočty volá z enginu
ve ../scripts (arb.py, analyze.py, normalize.py, ingest.py, db.py, freebet.py).
Žádný pip, žádný Node — funguje na čistém Pythonu 3.9+.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

# poslední zachycené syrové API odpovědi ze stránek sázkovek (z userscriptu)
RAW = []

def save_raw(book, url, jsonobj):
    txt = json.dumps(jsonobj, ensure_ascii=False)
    RAW.insert(0, {"bookmaker": book, "url": url, "bytes": len(txt),
                   "ts": time.time(), "json": jsonobj})
    del RAW[300:]
    try:
        d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "raw")
        os.makedirs(d, exist_ok=True)
        safe = re.sub(r"[^a-zA-Z0-9]+", "_", (book + "_" + url))[-90:] or "raw"
        with open(os.path.join(d, safe + ".json"), "w", encoding="utf-8") as f:
            f.write(txt)
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "..", "scripts")
STATIC = os.path.join(HERE, "static")
sys.path.insert(0, SCRIPTS)

# DB ulož vedle enginu (../data/odds.db), pokud není přepsáno
os.environ.setdefault("LIVETIME_DB", os.path.join(HERE, "..", "data", "odds.db"))

import db                       # noqa: E402
import normalize                # noqa: E402
import ingest                   # noqa: E402
import freebet                  # noqa: E402
from arb import find_arb        # noqa: E402
from analyze import find_value_bets  # noqa: E402

SEED_LARGE = os.path.join(HERE, "..", "examples", "seed_events_large.json")
SEED_SMALL = os.path.join(HERE, "..", "examples", "seed_events.json")


# ── rizikový štítek ────────────────────────────────────────────────────────

def risk_tier(margin: float) -> dict:
    m = margin * 100
    if m > 8:
        return {"level": "high", "label": "🔴 vysoké",
                "why": "Marže >8 % bývá chyba sázkovky (palpable error) nebo "
                       "rozdílná pravidla trhu — sázkovka může sázku stornovat."}
    if m >= 3:
        return {"level": "mid", "label": "🟠 střední",
                "why": "Live kurzy se rychle hýbou; ověř, že obě nohy stihneš."}
    return {"level": "low", "label": "🟢 nízké",
            "why": "Realistická arbitráž z rozdílu kurzů na likvidním trhu."}


# ── sestavení příležitostí ────────────────────────────────────────────────

def build_opportunities(events: dict, total, bankroll, kelly,
                        min_margin, min_edge, round_to=10,
                        max_margin=20.0, min_books=2) -> dict:
    surebets, values = [], []
    for ev in events.get("events", []):
        for m in ev.get("markets", []):
            a = find_arb(ev["sport"], ev["event"], m["market"], m["quotes"],
                         total, min_margin / 100.0, round_to,
                         min_books=min_books, max_margin=max_margin / 100.0)
            if a:
                d = a.to_dict()
                d["risk"] = risk_tier(a.margin)
                surebets.append(d)
            for vb in find_value_bets(m["quotes"], min_edge / 100.0,
                                      bankroll, kelly):
                vb.update({"market": m["market"], "event": ev["event"],
                           "sport": ev["sport"]})
                values.append(vb)
    surebets.sort(key=lambda x: x["margin"], reverse=True)
    values.sort(key=lambda x: x["edge"], reverse=True)
    return {"surebets": surebets, "values": values}


def diagnostics() -> dict:
    """Co se reálně sbírá a parsuje — ať je vidět, kde to případně drhne."""
    from collections import Counter
    raw_by_book = Counter(r["bookmaker"] for r in RAW)
    parsed_by_book, samples, urls_by_book = Counter(), {}, {}
    try:
        import parse_raw
        for r in RAW:
            try:
                qs = parse_raw.extract(r["bookmaker"], r["json"])
            except Exception:
                qs = []
            parsed_by_book[r["bookmaker"]] += len(qs)
            urls_by_book.setdefault(r["bookmaker"], set()).add(r["url"][:120])
            if qs and r["bookmaker"] not in samples:
                samples[r["bookmaker"]] = qs[:6]
    except Exception as e:
        samples["_error"] = str(e)

    db_quotes = db.recent_quotes(24 * 3600)
    events = normalize.merge_quotes(db_quotes)
    mkt_types = Counter()
    complete_examples = []
    for e in events.get("events", []):
        for m in e["markets"]:
            mkt_types[m["type"]] += 1
            books = sorted({b for codes in m["quotes"].values() for b in codes})
            if len(books) >= 2 and len(complete_examples) < 8:
                complete_examples.append(
                    {"event": e["event"], "market": m["market"], "books": books})

    return {
        "raw_captures_per_book": dict(raw_by_book),
        "parsed_quotes_per_book": dict(parsed_by_book),
        "raw_urls_per_book": {k: sorted(v)[:12] for k, v in urls_by_book.items()},
        "parsed_samples": samples,
        "db_quotes": len(db_quotes),
        "db_books": sorted({q.get("bookmaker") for q in db_quotes}),
        "canonical_events": len(events.get("events", [])),
        "canonical_markets_by_type": dict(mkt_types),
        "markets_with_2plus_books": complete_examples,
        "hint": ("Když parsed_quotes_per_book = 0 u sázkovky, parser netrefuje "
                 "její JSON → pošli mi /api/raw/sample?book=NAZEV. Když markets_"
                 "with_2plus_books je prázdné, nemáš stejný trh od 2 sázkovek."),
    }


def markets_html(show_all: bool = False) -> str:
    """Čitelná stránka: všechny trhy v DB + kurzy per sázkovka (ať je vidět,
    co se s čím porovnává a kde je nesmysl)."""
    events = load_events("db")
    n_markets = n_multi = 0
    body = []
    for ev in sorted(events.get("events", []), key=lambda e: e["event"]):
        rows = []
        mkts = []
        for m in ev["markets"]:
            books = sorted({b for codes in m["quotes"].values() for b in codes})
            mkts.append((len(books), m, books))
        mkts.sort(key=lambda x: -x[0])
        for nbooks, m, books in mkts:
            n_markets += 1
            if nbooks >= 2:
                n_multi += 1
            elif not show_all:
                continue
            codes = list(m["quotes"].keys())
            best = {c: max(bk.values()) for c, bk in m["quotes"].items() if bk}
            S = sum(1 / o for o in best.values()) if len(best) == len(codes) else None
            tag = ""
            if S is not None:
                if S < 1:
                    tag = f"<b style='color:#22c55e'>🟢 ARB +{(1/S-1)*100:.2f}%</b>"
                else:
                    tag = f"<span style='color:#94a3b8'>Σ {S*100:.1f}% (přebití {(S-1)*100:.1f}%)</span>"
            cells = []
            for c in codes:
                bs = " · ".join(f"{b}:{o:.2f}" for b, o in sorted(m["quotes"][c].items()))
                cells.append(f"<td><b>{c}</b><br><span style='color:#93c5fd'>{bs}</span></td>")
            border = "#22c55e" if (S is not None and S < 1) else ("#1d4ed8" if nbooks >= 2 else "#334155")
            rows.append(
                f"<tr style='border-left:3px solid {border}'><td style='min-width:230px'>{m['market']} "
                f"<span style='color:#64748b'>[{nbooks} sáz.]</span><br>{tag}</td>{''.join(cells)}</tr>")
        if rows:
            body.append(f"<h3 style='margin:14px 0 4px'>{ev['event']} "
                        f"<span style='color:#64748b;font-weight:400'>· {ev['sport']}</span></h3>"
                        f"<table>{''.join(rows)}</table>")
    head = (f"<div style='margin-bottom:10px'><b>{len(events.get('events',[]))} zápasů</b> · "
            f"{n_markets} trhů · <b style='color:#22c55e'>{n_multi} trhů od 2+ sázkovek</b> · "
            f"<a href='/markets?all={'0' if show_all else '1'}' style='color:#60a5fa'>"
            f"{'zobrazit jen 2+ sázkovek' if show_all else 'zobrazit i jednosázkovkové'}</a></div>")
    return ("<!doctype html><meta charset=utf-8><title>Trhy</title>"
            "<style>body{background:#0b0f17;color:#e5e9f0;font:13px system-ui;padding:16px}"
            "table{border-collapse:collapse;width:100%;margin-bottom:8px}"
            "td{padding:4px 8px;border:1px solid #1f2a3a;vertical-align:top}"
            "h3{color:#e5e9f0}a{text-decoration:none}</style>"
            + head + ("".join(body) or "<p>Žádné trhy. Nasbírej kurzy přes rozšíření.</p>"))


def load_events(source: str) -> dict:
    if source == "seed":
        path = SEED_LARGE if os.path.exists(SEED_LARGE) else SEED_SMALL
        return json.load(open(path, encoding="utf-8"))
    # default: z DB (čerstvé kotace)
    return normalize.merge_quotes(db.recent_quotes(24 * 3600))


# ── HTTP handler ───────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        elif isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        # CORS — aby userscript běžící na stránce sázkovky mohl posílat kurzy
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, PUT, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):                 # CORS preflight
        self._send(204, b"")

    def _body(self) -> dict:
        n = int(self.headers.get("Content-Length", 0) or 0)
        if not n:
            return {}
        raw = self.rfile.read(n)
        try:
            return json.loads(raw)
        except ValueError:
            return {"_raw": raw.decode("utf-8", "replace")}

    def log_message(self, *a):       # ztiš log
        pass

    # ---- GET ----
    def do_GET(self):
        try:
            self._do_GET()
        except Exception as e:           # nikdy neshodit spojení — vrať čitelnou chybu
            import traceback
            traceback.print_exc()
            try:
                self._send(500, {"error": str(e)})
            except Exception:
                pass

    def _do_GET(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}

        if u.path in ("/", "/index.html"):
            return self._serve_static("index.html")
        if u.path.startswith("/static/"):
            return self._serve_static(u.path[len("/static/"):])

        if u.path == "/api/opportunities":
            events = load_events(q.get("source", "seed"))
            data = build_opportunities(
                events,
                total=float(q.get("total", 1000)),
                bankroll=float(q.get("bankroll", 100000)),
                kelly=float(q.get("kelly", 0.25)),
                min_margin=float(q.get("min_margin", 0)),
                min_edge=float(q.get("min_edge", 2)),
                round_to=int(q.get("round", 10)),
                max_margin=float(q.get("max_margin", 20)),
                min_books=int(q.get("min_books", 2)),
            )
            data["meta"] = {"source": q.get("source", "seed"),
                            "events": len(events.get("events", []))}
            return self._send(200, data)

        if u.path == "/api/raw":            # přehled zachycených API odpovědí
            return self._send(200, {"count": len(RAW), "captures": [
                {"bookmaker": r["bookmaker"], "url": r["url"][:200],
                 "bytes": r["bytes"], "ts": r["ts"]} for r in RAW[:200]]})
        if u.path == "/api/raw/sample":     # poslední celá odpověď (k rozboru)
            book = q.get("book")
            for r in RAW:
                if not book or r["bookmaker"] == book:
                    return self._send(200, r["json"])
            return self._send(404, {"error": "zatím nic zachyceno"})

        if u.path == "/markets":            # čitelný výpis všech trhů + kurzů
            return self._send(200, markets_html(q.get("all") == "1"), "text/html")

        if u.path == "/api/diag":           # diagnostika na reálných datech
            return self._send(200, diagnostics())

        if u.path == "/api/events":
            return self._send(200, load_events(q.get("source", "seed")))
        if u.path == "/api/bets":
            return self._send(200, {"bets": db.list_bets(),
                                    "stats": db.stats()})
        if u.path == "/api/bankroll":
            return self._send(200, {"bankroll": db.get_bankroll()})

        return self._send(404, {"error": "not found"})

    # ---- POST / PATCH / PUT ----
    def do_POST(self):
        u = urlparse(self.path)
        b = self._body()

        if u.path == "/api/raw":            # rozšíření posílá syrový API JSON
            book = b.get("bookmaker", "?")
            save_raw(book, b.get("url", ""), b.get("json"))
            n = 0
            try:
                import parse_raw
                qs = parse_raw.extract(book, b.get("json"))
                n = db.insert_quotes(qs) if qs else 0
            except Exception as e:          # parser nesmí shodit příjem
                print("[parse_raw]", e)
            return self._send(200, {"ok": True, "count": len(RAW), "parsed": n})

        if u.path == "/api/ingest":
            # userscript posílá rovnou pole hotových kotací
            if isinstance(b.get("quotes"), list):
                qs = [x for x in b["quotes"] if isinstance(x, dict) and x.get("odds")]
                n = db.insert_quotes(qs) if qs else 0
                return self._send(200, {"parsed": len(qs), "saved": n,
                                        "preview": qs[:80]})
            text = b.get("text", b.get("_raw", ""))
            mode = b.get("mode", "block")
            if mode == "free":
                ln = b.get("line")
                try:
                    ln = float(str(ln).replace(",", ".")) if ln not in (None, "", "None") else None
                except ValueError:
                    ln = None
                ctx = {"book": b.get("book") or "?", "sport": b.get("sport") or "?",
                       "home": b.get("home") or "?", "away": b.get("away") or "?",
                       "market": b.get("market") or "?", "line": ln}
                quotes = ingest.parse_free(text, ctx)
            else:
                quotes = ingest.parse_block(text)
            n = db.insert_quotes(quotes) if quotes else 0
            return self._send(200, {"parsed": len(quotes), "saved": n,
                                    "preview": quotes[:80]})

        if u.path == "/api/bets":
            return self._send(200, {"id": db.log_bet(b)})

        if u.path == "/api/freebet/calc":
            mode = b.get("mode", "free2")
            if mode == "free2":
                cash, profit = freebet.free_two_books(
                    float(b["free_stake"]), float(b["odds_a"]), float(b["odds_b"]))
                return self._send(200, {"cash": round(cash), "profit": round(profit),
                                        "rate": round(profit / float(b["free_stake"]) * 100, 1)})
            if mode == "lay":
                ls, liab, profit = freebet.lay_freebet(
                    float(b["free_stake"]), float(b["back_odds"]),
                    float(b["lay_odds"]), float(b.get("commission", 0.02)))
                return self._send(200, {"lay_stake": round(ls), "liability": round(liab),
                                        "profit": round(profit)})
            return self._send(400, {"error": "neznámý mode"})

        return self._send(404, {"error": "not found"})

    def do_PATCH(self):
        u = urlparse(self.path)
        b = self._body()
        if u.path.startswith("/api/bets/"):
            bid = int(u.path.rsplit("/", 1)[-1])
            ok = db.set_bet_status(bid, b.get("status", "settled"))
            return self._send(200 if ok else 404, {"ok": ok})
        return self._send(404, {"error": "not found"})

    def do_PUT(self):
        u = urlparse(self.path)
        b = self._body()
        if u.path == "/api/bankroll":
            for row in b.get("bankroll", []):
                db.upsert_bankroll(row)
            return self._send(200, {"bankroll": db.get_bankroll()})
        return self._send(404, {"error": "not found"})

    def _serve_static(self, rel):
        path = os.path.normpath(os.path.join(STATIC, rel))
        if not path.startswith(STATIC) or not os.path.isfile(path):
            return self._send(404, {"error": "not found"})
        ctype = {".html": "text/html", ".js": "application/javascript",
                 ".css": "text/css"}.get(os.path.splitext(path)[1], "text/plain")
        with open(path, "rb") as f:
            return self._send(200, f.read(), ctype)


def main():
    with db.connect():           # založ schéma
        pass
    port = int(os.environ.get("PORT", 8000))
    srv = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"🟢 Livetime Arb Dashboard běží na  http://localhost:{port}")
    print("   Ctrl+C pro ukončení.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nKonec.")


if __name__ == "__main__":
    main()
