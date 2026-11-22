"""Wyniki zwracane przez reguły i kalkulator."""
from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class Status(str, Enum):
    PRZYSLUGUJE = "przysluguje"
    NIE_PRZYSLUGUJE = "nie_przysluguje"
    BRAK_DANYCH = "brak_danych"


class BrakujacePytanie(BaseModel):
    id: str                          # ID pytania z katalogu, np. "B5" (link do zakładki Dane)
    tresc: str
    gdzie_znalezc: str | None = None # np. "zaświadczenie Z-3, pkt 11"


class WynikUprawnienia(BaseModel):
    swiadczenie: str                 # np. "zasilek_macierzynski"
    status: Status
    uzasadnienie: list[str] = Field(default_factory=list)   # zdania dla użytkownika
    podstawa_prawna: list[str] = Field(default_factory=list)
    brakujace_pola: list[str] = Field(default_factory=list)  # ID pytań do uzupełnienia, np. ["A1", "B7"]
    brakujace_pytania: list[BrakujacePytanie] = Field(default_factory=list)  # to samo z treścią – do UI
    ostrzezenia: list[str] = Field(default_factory=list)     # ryzyka (FR-22)
    kto_wyplaca: str | None = None   # "pracodawca" / "ZUS" (FR-20)


class Okres(BaseModel):
    rodzaj: str          # "macierzynski", "rodzicielski", "ojcowski", ...
    osoba: str           # "matka" / "ojciec"
    od: date
    do: date
    stawka: float
    kwota_miesieczna: float
    kwota_za_okres: float
    uwagi: list[str] = Field(default_factory=list)


class WynikKalkulatora(BaseModel):
    podstawa_wymiaru: float
    okresy: list[Okres]
    suma: float
    ostrzezenia: list[str] = Field(default_factory=list)
    wersja_parametrow: str
