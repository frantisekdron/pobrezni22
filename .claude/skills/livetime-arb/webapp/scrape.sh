#!/usr/bin/env bash
# Plně automatický scraper kurzů řízeným prohlížečem (Playwright).
# Nainstaluje si vše sám a spustí sběr. Dashboard musí běžet zvlášť:
#   v jiném okně:  python3 server.py
#
# Použití:   bash scrape.sh
set -e
cd "$(dirname "$0")"

echo "▶ Připravuji prostředí (jednorázově to chvíli trvá)…"
python3 -m venv .venv 2>/dev/null || true
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install -q --upgrade pip
python -m pip install -q playwright
echo "▶ Stahuji prohlížeč Chromium pro automatizaci…"
python -m playwright install chromium

echo "▶ Spouštím scraper. Otevře se okno prohlížeče — nech ho běžet."
echo "  (Dashboard musí běžet v jiném okně: python3 server.py)"
python scraper.py
