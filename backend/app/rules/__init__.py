"""Reguły prawa do świadczeń (docs/architektura.md, rozdz. 7).

Jedna funkcja na świadczenie (albo grupę świadczeń ze wspólnym ustaleniem prawa). Funkcja dostaje
`Kontekst` (aktywne fakty, wybory scenariusza) i parametry, zwraca listę `WynikReguly`.
Reguła dotyczy osób o rolach z `DLA_ROL` – dla pozostałych API jej nie uruchamia.
"""
from typing import Any, Callable

from app.rules.wspolne import Kontekst, WynikReguly
from app.rules.zasilek_macierzynski import zasilek_macierzynski

Regula = Callable[[Kontekst, dict[str, Any]], list[WynikReguly]]

# Rejestr – dopisujcie kolejne świadczenia (chorobowy w ciąży, ojcowski, uzupełniający, ...).
REGULY: dict[str, Regula] = {
    "zasilek_macierzynski": zasilek_macierzynski,
}
DLA_ROL: dict[str, tuple[str, ...]] = {
    "zasilek_macierzynski": ("matka",),
}
