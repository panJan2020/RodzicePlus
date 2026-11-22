"""Wspólny interfejs adapterów źródeł danych (docs/architektura.md, rozdz. 4).

Adapter zwraca słownik `pole → WartoscPola` (jedna wartość na pole z danego źródła) i NICZEGO nie zapisuje –
zapis do sprawy robi zawsze `app.merge.dodaj(...)`, który wybiera aktywną wartość.

Wszystkie adaptery w tym katalogu to SYMULACJE na danych fikcyjnych użytkowników (`sources/dane/<login>.json`).
W produkcji podmienia się tylko implementację `pobierz` (np. wywołanie usługi ZUS) – reszta aplikacji bez zmian.
"""
import json
from datetime import date
from functools import lru_cache
from typing import Any

from app.config import SOURCES_DATA_DIR
from app.domain.model import Kanal, Osoba, Sprawa, WartoscPola, Wystawca


class ZrodloNiedostepne(Exception):
    """Źródła nie da się odpytać dla tej osoby (np. brak zalogowania). Komunikat po polsku dla użytkownika."""


@lru_cache
def _plik(login: str) -> dict[str, Any] | None:
    sciezka = SOURCES_DATA_DIR / f"{login}.json"
    return json.loads(sciezka.read_text(encoding="utf-8")) if sciezka.is_file() else None


def konta() -> dict[str, dict[str, Any]]:
    """Wszystkie fikcyjne konta testowe: login → dane."""
    return {p.stem: _plik(p.stem) for p in sorted(SOURCES_DATA_DIR.glob("*.json"))}


def konto(login: str) -> dict[str, Any] | None:
    return _plik(login)


class Zrodlo:
    """Bazowa klasa adaptera. Podklasa ustawia metadane i implementuje `_pola`."""
    kod: str
    nazwa: str
    wystawca: Wystawca
    kanal: Kanal
    opis: str
    zrodlo_opis: str  # tekst „Skąd to wiemy” przy każdej wartości z tego źródła

    def pobierz(self, sprawa: Sprawa, osoba: Osoba, na_dzien: date | None = None) -> dict[str, WartoscPola]:
        if not osoba.login:
            raise ZrodloNiedostepne("Aby pobrać dane z systemów, zaloguj się przez mObywatela.")
        dane = konto(osoba.login)
        if dane is None:
            raise ZrodloNiedostepne("Nie znaleźliśmy danych dla tego konta.")
        return {pole: self._wartosc(v) for pole, v in self._pola(dane, na_dzien or date.today()).items()
                if v is not None}

    def _pola(self, dane: dict[str, Any], na_dzien: date) -> dict[str, Any]:
        raise NotImplementedError

    def _wartosc(self, v: Any) -> WartoscPola:
        return WartoscPola(wartosc=v, wystawca=self.wystawca, kanal=self.kanal, zrodlo_opis=self.zrodlo_opis)
