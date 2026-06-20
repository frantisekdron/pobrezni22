#!/usr/bin/env bash
# Spustí Livetime Arb Dashboard. Žádné závislosti — jen Python 3.
# Použití:  ./run.sh        (port 8000)
#           PORT=9000 ./run.sh
cd "$(dirname "$0")" || exit 1
PORT="${PORT:-8000}" exec python3 server.py
