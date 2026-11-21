"""Wspólny model danych sprawy.

Kluczowa decyzja: KAŻDA wartość (z kwestionariusza, z mocka ZUS albo ze skanu
odczytanego przez Claude) jest zapisana jako FieldValue z informacją o źródle.
Dzięki temu:
  * kwestionariusz pyta tylko o brakujące pola,
  * UI pokazuje "skąd to wiemy" (dokument + strona),
  * wykrywamy sprzeczności między dokumentami.
Nazwy pól = kolumna "Pole" w docs/pytania_kalkulator.md.
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Zrodlo(str, Enum):
    UZYTKOWNIK = "uzytkownik"
    ZUS = "zus"            # symulowane pobranie z systemów ZUS
    DOKUMENT = "dokument"  # odczyt ze skanu (Claude API)
    WYLICZONE = "wyliczone"


class FieldValue(BaseModel):
    wartosc: Any
    zrodlo: Zrodlo
    dokument: str | None = None      # np. "ZAM", "Z-3"
    strona: int | None = None        # numer strony w PDF
    pewnosc: float | None = None     # 0..1, tylko dla odczytu AI
    potwierdzone: bool = False       # użytkownik sprawdził wartość
    zmieniono: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Konflikt(BaseModel):
    pole: str
    wartosci: list[FieldValue]


class Osoba(BaseModel):
    """Profil jednej osoby (matka / ojciec / opiekun)."""
    rola: str = "matka"
    pola: dict[str, FieldValue] = Field(default_factory=dict)

    def get(self, pole: str, default: Any = None) -> Any:
        fv = self.pola.get(pole)
        return fv.wartosc if fv is not None else default


class Sprawa(BaseModel):
    id: str
    osoby: list[Osoba] = Field(default_factory=lambda: [Osoba()])
    konflikty: list[Konflikt] = Field(default_factory=list)
    # Wynik z kartki opisowej ZUS (1. strona zestawu) – TYLKO do porównania/testów,
    # nigdy jako dane wejściowe kalkulatora.
    oczekiwany_wynik: str | None = None
    dokumenty: list[str] = Field(default_factory=list)
