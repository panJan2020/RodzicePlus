"""Wyniki zwracane przez API świadczeń i kalkulatora (docs/api.md 3.6–3.7).

Kod zwraca PODZBIÓR pól z kontraktu – pola, których jeszcze nie liczymy (np. okres i kwota w wyniku świadczenia,
scenariusze), dochodzą razem z regułami. Kwoty i stawki zawsze jako tekst ("1234.56", "0.815").
"""
from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class Status(str, Enum):
    PRZYSLUGUJE = "przysluguje"
    NIE_PRZYSLUGUJE = "nie_przysluguje"
    BRAK_DANYCH = "brak_danych"


class BrakujacePole(BaseModel):
    pytanie_id: str                  # ID pytania z katalogu, np. "B5" (link do „Moich danych”)
    tresc: str
    gdzie_znalezc: str | None = None # np. "zaświadczenie Z-3, pkt 11"


class Powod(BaseModel):
    pole: str
    wartosc: str | None = None
    komunikat: str


class WynikSwiadczenia(BaseModel):
    swiadczenie: str                 # np. "zasilek_macierzynski"
    nazwa: str
    osoba_id: str
    status: Status
    uzasadnienie: list[str] = Field(default_factory=list)   # zdania dla użytkownika
    powody: list[Powod] = Field(default_factory=list)        # przy nie_przysluguje
    brakujace_pola: list[BrakujacePole] = Field(default_factory=list)  # przy brak_danych
    kto_wyplaca: str | None = None   # "platnik" | "zus"
    kto_wyplaca_opis: str | None = None
    podstawa_prawna: list[str] = Field(default_factory=list)
    wersja_parametrow: str


class OkresKalkulatora(BaseModel):
    rodzaj: str          # "macierzynski", "rodzicielski", ...
    osoba_id: str | None # None – drugi rodzic, którego nie ma jeszcze w sprawie
    od: date
    do: date
    tygodnie: int
    stawka: str
    kwota_miesieczna: str
    kwota_za_okres: str
    uwagi: list[str] = Field(default_factory=list)


class OsobaKalkulatora(BaseModel):
    osoba_id: str
    podstawa_wymiaru: str
    suma: str


class WynikKalkulatora(BaseModel):
    scenariusz_id: str
    wersja_parametrow: str
    osoby: list[OsobaKalkulatora]
    okresy: list[OkresKalkulatora]
    suma: str
    ostrzezenia: list[str] = Field(default_factory=list)
    bledy_wyborow: list[str] = Field(default_factory=list)
