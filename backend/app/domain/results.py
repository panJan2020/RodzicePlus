"""Wyniki zwracane przez API świadczeń i kalkulatora (docs/api.md 3.6–3.7).

Kwoty i stawki zawsze jako tekst ("1234.56", "0.815"). Pola, których jeszcze nie liczymy (scenariusze,
drugi rodzic), dochodzą razem z regułami.
"""
from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class Status(str, Enum):
    PRZYSLUGUJE = "przysluguje"
    WARUNKOWO = "warunkowo"          # spełnione, ale zależne od przyszłego zdarzenia (np. ubezpieczenie w dniu porodu)
    BRAK_DANYCH = "brak_danych"
    NIE_PRZYSLUGUJE = "nie_przysluguje"


class BrakujacePole(BaseModel):
    pytanie_id: str                  # ID pytania z katalogu, np. "B5" (link do „Moich danych”)
    tresc: str
    gdzie_znalezc: str | None = None # np. "zaświadczenie Z-3, pkt 11"


class Powod(BaseModel):
    pole: str
    wartosc: str | None = None
    komunikat: str


class Warunek(BaseModel):
    """Warunek wyniku `warunkowo` – przyszłe zdarzenie, od którego zależy prawo."""
    opis: str
    ryzyko: str | None = None        # kod ryzyka (content/ryzyka), np. "brak_ubezpieczenia_w_dniu_porodu"


class OkresWyniku(BaseModel):
    od: date
    do: date
    tygodnie: int | None = None      # urlopy – liczba tygodni
    dni: int | None = None           # zasiłek chorobowy – liczba dni zasiłku (bez przerw między zwolnieniami)


class KwotaWyniku(BaseModel):
    miesieczna: str
    za_okres: str
    stawka: str
    stawka_dzienna: str
    podstawa_wymiaru: str
    brutto: bool = True


class WynikSwiadczenia(BaseModel):
    swiadczenie: str                 # np. "zasilek_macierzynski_urlop_macierzynski"
    nazwa: str
    osoba_id: str
    scenariusz_id: str
    status: Status
    podsumowanie: str                # jedno zdanie dla użytkownika
    okres: OkresWyniku | None = None
    kwota: KwotaWyniku | None = None # None – nie da się jeszcze policzyć (braki w `brakujace_pola`)
    stawka: str | None = None        # "1.00" | "0.80" – gdy znamy stawkę, a kwoty jeszcze nie liczymy (zasiłek chorobowy)
    okres_wynagrodzenia: OkresWyniku | None = None   # zasiłek chorobowy: wynagrodzenie, które wypłaca pracodawca
    kto_wyplaca: str | None = None   # "platnik" | "zus" | None (nie wiemy – patrz kto_wyplaca_opis)
    kto_wyplaca_opis: str | None = None
    gdzie_zlozyc: str | None = None
    uzasadnienie: list[str] = Field(default_factory=list)   # zdania dla użytkownika
    powody: list[Powod] = Field(default_factory=list)        # przy nie_przysluguje
    warunki: list[Warunek] = Field(default_factory=list)     # przy warunkowo
    brakujace_pola: list[BrakujacePole] = Field(default_factory=list)  # braki do prawa, okresu albo kwoty
    co_zrobic: list[str] = Field(default_factory=list)
    orientacyjny: bool = False
    pola_do_potwierdzenia: list[BrakujacePole] = Field(default_factory=list)
    ryzyka: list[str] = Field(default_factory=list)          # kody ryzyk
    uwagi: list[str] = Field(default_factory=list)           # przybliżenia, założenia, „do potwierdzenia”
    podstawa_prawna: list[str] = Field(default_factory=list)
    wersja_parametrow: str


class OkresKalkulatora(BaseModel):
    rodzaj: str          # "macierzynski", "rodzicielski", ...
    osoba_id: str | None # None – drugi rodzic, którego nie ma jeszcze w sprawie
    od: date
    do: date
    tygodnie: int
    stawka: str
    stawka_dzienna: str
    kwota_miesieczna: str
    kwota_za_okres: str
    uwagi: list[str] = Field(default_factory=list)


class OsobaKalkulatora(BaseModel):
    osoba_id: str
    podstawa_wymiaru: str
    suma: str
    powrot_do_pracy: date


class WynikKalkulatora(BaseModel):
    scenariusz_id: str
    wersja_parametrow: str
    osoby: list[OsobaKalkulatora]
    okresy: list[OkresKalkulatora]
    suma: str
    orientacyjny: bool = False
    ostrzezenia: list[str] = Field(default_factory=list)
    bledy_wyborow: list[str] = Field(default_factory=list)
