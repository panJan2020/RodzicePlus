"""Scenariusz domyślny – wybory budowane z faktów (docs/pytania_kalkulator.md, sekcja V, ostatni akapit).

Dopóki nie ma ekranu scenariuszy, kalkulator liczy tylko scenariusz domyślny:
  * `wniosek_81_5` = True, gdy w faktach jest data złożenia wniosku (`wniosek_81_5_data`) i mieści się
    w terminie z parametrów (`wniosek_jednolita_dni` od porodu / przyjęcia dziecka – art. 31 ust. 3 ustawy
    zasiłkowej); w innym razie wariant 100% / 70%.
"""
from datetime import date
from typing import Any

from app.rules import wyliczone

SCENARIUSZ_DOMYSLNY = "domyslny"


def data_zdarzenia(fakty: dict[str, Any]) -> date | None:
    """Dzień porodu (albo przewidywany dzień porodu, dopóki dziecko się nie urodziło)."""
    return wyliczone.data_zdarzenia(fakty)


def wniosek_81_5_w_terminie(fakty: dict[str, Any], p: dict[str, Any]) -> bool:
    wniosek, zdarzenie = fakty.get("wniosek_81_5_data"), data_zdarzenia(fakty)
    if not wniosek or zdarzenie is None:
        return False
    return (date.fromisoformat(wniosek) - zdarzenie).days <= p["wniosek_jednolita_dni"]


def domyslny(fakty: dict[str, Any], p: dict[str, Any]) -> dict[str, Any]:
    """Wybory scenariusza domyślnego (klucze jak `Scenariusz.wybory` w docs/api.md 3.7)."""
    return {"wniosek_81_5": wniosek_81_5_w_terminie(fakty, p)}
