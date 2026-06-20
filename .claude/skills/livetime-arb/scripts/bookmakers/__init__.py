"""Adaptéry sázkovek pro livetime-arb."""

from .tipsport import Tipsport
from .betano import Betano
from .bet365 import Bet365
from .fortuna import Fortuna

ALL = {
    "tipsport": Tipsport,
    "betano": Betano,
    "bet365": Bet365,
    "fortuna": Fortuna,
}


def get(name: str):
    cls = ALL.get(name.lower())
    return cls() if cls else None
