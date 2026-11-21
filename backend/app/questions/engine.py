"""Silnik kwestionariusza: które pytania pokazać, czego brakuje.

Warunki są liczone w backendzie, a Flutter tylko renderuje listę pytań.
Dzięki temu logika prawna nie jest dublowana w Dart.
"""
import json
from functools import lru_cache
from typing import Any

from app.config import QUESTIONS_FILE
from app.domain.profile import Osoba


@lru_cache
def katalog() -> list[dict[str, Any]]:
    return json.loads(QUESTIONS_FILE.read_text(encoding="utf-8"))["pytania"]


def _warunek_spelniony(osoba: Osoba, w: dict[str, Any]) -> bool:
    wartosc = osoba.get(w["pole"])
    if wartosc is None:
        return False
    if "zawiera" in w:
        return w["zawiera"] in (wartosc if isinstance(wartosc, list) else [wartosc])
    if "zawiera_ktores" in w:
        lista = wartosc if isinstance(wartosc, list) else [wartosc]
        return any(x in lista for x in w["zawiera_ktores"])
    if "rowne" in w:
        return wartosc == w["rowne"]
    return False


def widoczne_pytania(osoba: Osoba) -> list[dict[str, Any]]:
    return [p for p in katalog()
            if all(_warunek_spelniony(osoba, w) for w in p.get("pokaz_gdy", []))]


def nastepne_pytania(osoba: Osoba) -> list[dict[str, Any]]:
    """Widoczne pytania, na które jeszcze nie ma odpowiedzi (z żadnego źródła)."""
    return [p for p in widoczne_pytania(osoba) if p["pole"] not in osoba.pola]


def pola_z_dokumentow() -> list[dict[str, Any]]:
    """Pola, które Claude ma próbować odczytać ze skanów."""
    return [p for p in katalog() if p.get("z_dokumentow")]
