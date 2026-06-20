#!/usr/bin/env python3
"""
canon.py — kanonizace trhů a výsledků na striktní taxonomii.

Cíl: pro arbitráž potřebujeme JISTOTU, že porovnáváme opravdu opačné strany
téhož trhu. Surová data ze sázkovek jsou ale chaos (Betbuilder, exotické trhy,
hráčské sázky, jiné hranice…). Tenhle modul každou kotaci buď zařadí do jasně
definovaného typu, nebo ji ZAHODÍ (vrátí None).

Podporované typy (jen ty se dají bezpečně arbitrážovat):
  1X2      výsledek 3-cestný   → kódy 1 / X / 2
  WINNER2  výsledek 2-cestný   → kódy 1 / 2   (tenis, basket, MMA…)
  OU       nad/pod hranice     → kódy OVER / UNDER  (+ subjekt a line)
  BTTS     oba dají gól         → kódy YES / NO

market_key = "TYP|subjekt|line"  → over/under gólů 2.5 se nikdy nespáruje s
over/under rohů 2.5 ani s jinou hranicí.
"""

from __future__ import annotations
import re
import unicodedata


def s(x: str) -> str:
    x = unicodedata.normalize("NFKD", x or "")
    x = "".join(c for c in x if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", x).lower().strip()


# sporty bez remízy (výsledek je 2-cestný)
TWO_WAY_SPORTS = {"tenis", "tennis", "basketbal", "basketball", "nba",
                  "volejbal", "volleyball", "mma", "ufc", "oktagon", "box",
                  "baseball", "sipky", "darts", "stolni tenis", "table tennis",
                  "americky fotbal", "snooker", "badminton"}

OVER_RE = re.compile(r"\b(nad|vice|over|more)\b|^\s*\+\s*\d")
UNDER_RE = re.compile(r"\b(pod|mene|under|less)\b|^\s*-\s*\d")
DRAW_RE = re.compile(r"^(remiza|draw|x|nerozhodne)$")
YESNO_YES = re.compile(r"^(ano|yes)$")
YESNO_NO = re.compile(r"^(ne|no)$")

# subjekt trhu (čeho se nad/pod týká) — sjednotí různá pojmenování napříč sázkovkami
SUBJECTS = [
    (re.compile(r"\b(esa|aces)\b"), "aces"),
    (re.compile(r"dvojchyb|double fault"), "double_faults"),
    (re.compile(r"\b(gol|gól|goal)\w*"), "goals"),
    (re.compile(r"roh|corner"), "corners"),
    (re.compile(r"karet|karty|card"), "cards"),
    (re.compile(r"\bgem\w*|games\b"), "games"),
    (re.compile(r"\bset\w*\b"), "sets"),
    (re.compile(r"\bbod\w*|points\b"), "points"),
    (re.compile(r"\bfaul|foul"), "fouls"),
    (re.compile(r"\bstrel|shot"), "shots"),
]

RESULT_RE = re.compile(r"vysledek zapasu|^1x2$|\bvitez\b|winner|moneyline|"
                       r"vysledek utkani|kdo vyhraje|^zapas$|full time result|"
                       r"konecny vysledek|^vysledek$")
BTTS_RE = re.compile(r"oba tymy|both teams|btts|oba (daji|vstreli|skoruji)|"
                     r"both teams to score")
# trhy, které NIKDY nearbitrážujeme (i kdyby prošly jinou heuristikou)
BLOCKLIST_RE = re.compile(r"betbuild|betbuilder|prilezitost|dvojtip|double chance|"
                          r"asijsk|handicap|presny vysledek|correct score|"
                          r"strelec|scorer|hrac|player|kdo da|first goal|"
                          r"poradi|method|zpusob|sestava|lineup|minuta|minute")


def _line(outcome: str, line) -> float | None:
    if line not in (None, "", "None"):
        try:
            return float(str(line).replace(",", "."))
        except ValueError:
            pass
    m = re.search(r"(\d+(?:[.,]\d+)?)", outcome or "")
    return float(m.group(1).replace(",", ".")) if m else None


def _subject(market: str, home: str, away: str) -> str | None:
    m = s(market)
    base = None
    for rx, subj in SUBJECTS:
        if rx.search(m):
            base = subj
            break
    if base is None:
        return None
    # týmově specifický total ("Španělsko počet gólů") odlišíme od celozápasového
    H, A = s(home), s(away)
    if H and len(H) > 2 and H in m:
        return base + ":home"
    if A and len(A) > 2 and A in m:
        return base + ":away"
    return base


def canon(market: str, outcome: str, line, home="", away="", sport=""):
    """Vrátí dict {type, subject, line, code, key} nebo None (nezařaditelné)."""
    m = s(market)
    o = s(outcome)
    if not o:
        return None
    if BLOCKLIST_RE.search(m) or BLOCKLIST_RE.search(o):
        return None

    # BTTS (oba dají gól) — jen když trh jasně značí BTTS
    if BTTS_RE.search(m):
        if YESNO_YES.match(o):
            return _mk("BTTS", "btts", None, "YES")
        if YESNO_NO.match(o):
            return _mk("BTTS", "btts", None, "NO")
        return None

    # Over / Under (nad/pod hranice)
    is_over = bool(OVER_RE.search(o))
    is_under = bool(UNDER_RE.search(o))
    if is_over or is_under:
        ln = _line(o, line)
        if ln is None:
            return None
        subj = _subject(market, home, away)
        if subj is None:
            return None        # neznámý subjekt → nebezpečné párovat → zahodit
        return _mk("OU", subj, ln, "OVER" if is_over else "UNDER")

    # Výsledek 1X2 / 2-cestný
    two_way = s(sport) in TWO_WAY_SPORTS
    typ = "WINNER2" if two_way else "1X2"
    if o in ("1", "2"):
        return _mk(typ, "result", None, o)
    if o == "x":
        return None if two_way else _mk("1X2", "result", None, "X")
    if DRAW_RE.match(o):
        return None if two_way else _mk("1X2", "result", None, "X")
    H, A = s(home), s(away)
    # výsledek přes jméno týmu/hráče (jen u zjevně výsledkového trhu nebo holého názvu)
    if (RESULT_RE.search(m) or m in ("", "?")) and not is_over and not is_under:
        if H and (o == H or (len(o) > 2 and o in H)):
            return _mk(typ, "result", None, "1")
        if A and (o == A or (len(o) > 2 and o in A)):
            return _mk(typ, "result", None, "2")
    return None


def _mk(typ, subject, line, code):
    key = f"{typ}|{subject}|{'' if line is None else f'{line:g}'}"
    return {"type": typ, "subject": subject, "line": line, "code": code, "key": key}


# požadované výsledky pro platnou arbitráž daného typu
REQUIRED = {
    "1X2": {"1", "X", "2"},
    "WINNER2": {"1", "2"},
    "OU": {"OVER", "UNDER"},
    "BTTS": {"YES", "NO"},
}


def label(typ, subject, line) -> str:
    subj = {"goals": "góly", "corners": "rohy", "cards": "karty", "aces": "esa",
            "games": "gemy", "points": "body", "sets": "sety",
            "double_faults": "dvojchyby"}.get(subject.split(":")[0], subject)
    side = " (tým)" if subject.endswith((":home", ":away")) else ""
    if typ in ("1X2", "WINNER2"):
        return "Výsledek zápasu" + (" (1X2)" if typ == "1X2" else " (vítěz)")
    if typ == "BTTS":
        return "Oba týmy dají gól"
    if typ == "OU":
        return f"{subj}{side} nad/pod {line:g}"
    return f"{typ} {subject}"
