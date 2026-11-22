"""Pomocnicze funkcje na datach – bez zależności od reguł i kalkulatora (przerywa cykl importów
`calculator.podstawa` ↔ `rules`)."""
from calendar import monthrange
from datetime import date
from typing import Any


def jako_date(v: Any) -> date | None:
    return date.fromisoformat(str(v)[:10]) if v else None


def tekst_daty(d: date) -> str:
    return d.strftime("%d.%m.%Y")


def dodaj_miesiace(d: date, n: int) -> date:
    """Ten sam dzień n miesięcy później (koniec miesiąca, gdy takiego dnia nie ma)."""
    m = d.month - 1 + n
    rok, mies = d.year + m // 12, m % 12 + 1
    return date(rok, mies, min(d.day, monthrange(rok, mies)[1]))
