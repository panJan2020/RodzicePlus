"""Reguły prawa do świadczeń (docs/architektura.md, rozdz. 7).

Jedna funkcja na świadczenie (albo grupę świadczeń ze wspólnym ustaleniem prawa). Funkcja dostaje
`Kontekst` (aktywne fakty, wybory scenariusza) i parametry, zwraca listę `WynikReguly`.
Reguła dotyczy osób o rolach z `DLA_ROL` – dla pozostałych API jej nie uruchamia.
"""
from datetime import date
from typing import Any, Callable

from app.calculator.okresy_chorobowe import poczatek_niezdolnosci
from app.rules import wyliczone
from app.rules.wspolne import Kontekst, WynikReguly
from app.rules.zasilek_chorobowy_ciaza import zasilek_chorobowy_ciaza
from app.rules.zasilek_macierzynski import zasilek_macierzynski

Regula = Callable[[Kontekst, dict[str, Any]], list[WynikReguly]]

# Rejestr – dopisujcie kolejne świadczenia (ojcowski, uzupełniający, ...).
REGULY: dict[str, Regula] = {
    "zasilek_macierzynski": zasilek_macierzynski,
    "zasilek_chorobowy_ciaza": zasilek_chorobowy_ciaza,
}
DLA_ROL: dict[str, tuple[str, ...]] = {
    "zasilek_macierzynski": ("matka",),
    "zasilek_chorobowy_ciaza": ("matka",),
}
# Pola, z których korzysta reguła – do „Skąd te dane?” (w wyniku trafiają tylko te, które mają aktywną wartość).
POLA_WEJSCIOWE: dict[str, tuple[str, ...]] = {
    "zasilek_macierzynski": (
        "sytuacja", "data_porodu", "pdp", "liczba_dzieci", "tytuly", "chorobowe", "chorobowe_od", "chorobowe_dobrowolne",
        "okresy_ubezpieczenia", "platnik_ponad_20", "etat", "umowa_do", "miesiace", "srednie_wynagrodzenie_brutto",
        "podstawa_deklarowana", "podstawa_deklarowana_srednia", "zadluzenie_kwota", "poprzedni_zasilek"),
    "zasilek_chorobowy_ciaza": (
        "ezla", "ezla_kod_b", "pdp", "data_porodu", "tytuly", "chorobowe", "chorobowe_od", "chorobowe_dobrowolne",
        "zatrudnienie_od", "okresy_ubezpieczenia", "platnik_ponad_20", "wynagrodzenie_chorobowe_okres", "miesiace",
        "podstawa_deklarowana", "podstawa_60_proc", "data_urodzenia", "poprzedni_zasilek"),
}
# Dzień powstania prawa – do wyboru wersji parametrów (fakty, wybory scenariusza → data albo None).
DATA_PRAWA: dict[str, Callable[[dict[str, Any], dict[str, Any]], date | None]] = {
    "zasilek_macierzynski": wyliczone.data_prawa,
    "zasilek_chorobowy_ciaza": lambda f, wybory: poczatek_niezdolnosci(f),
}
