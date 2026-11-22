"""Model danych sprawy: Sprawa → Osoby → Pola → lista WartoscPola (docs/architektura.md, rozdz. 3).

Kluczowe zasady:
  * pole osoby przechowuje KILKA wartości z różnych źródeł – żadna nie przepada,
  * każda wartość zna swojego wystawcę (kto za nią ręczy) i kanał (którędy dotarła),
  * dokładnie jedna wartość pola jest `aktywna` – tę widzą reguły i kalkulator;
    wybiera ją `app.merge` (hierarchia wiarygodności albo ręczny wybór użytkownika).

Nie zapisuj wartości bezpośrednio do `Osoba.pola` – zawsze przez `app.merge.dodaj(...)`.
Nazwy pól = kolumna „Pole” w docs/pytania_kalkulator.md.
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Wystawca(str, Enum):
    """Kto ręczy za informację."""
    ZUS = "zus"
    URZAD = "urzad"
    SAD = "sad"
    PRACODAWCA = "pracodawca"
    LEKARZ = "lekarz"
    UZYTKOWNIK = "uzytkownik"
    WYLICZONE = "wyliczone"


class Kanal(str, Enum):
    """Którędy informacja dotarła do aplikacji."""
    MOBYWATEL = "mobywatel"
    RSC = "rsc"
    ZUS_KONTO = "zus_konto"
    ZUS_PLATNIK = "zus_platnik"
    ZUS_HISTORIA = "zus_historia"
    EZLA = "ezla"
    PUE = "pue"
    UPLOAD = "upload"
    KREATOR = "kreator"
    SYSTEM = "system"


class Rola(str, Enum):
    MATKA = "matka"
    OJCIEC = "ojciec"
    DRUGI_RODZIC = "drugi_rodzic"
    DZIECKO = "dziecko"


ROLE_RODZICA = (Rola.MATKA, Rola.OJCIEC, Rola.DRUGI_RODZIC)


def _teraz() -> datetime:
    return datetime.now(timezone.utc)


class WartoscPola(BaseModel):
    """Jedna wartość pola z jednego źródła."""
    id: str = ""                      # nadaje merge.dodaj (w1, w2, … w obrębie sprawy)
    wartosc: Any
    wystawca: Wystawca
    kanal: Kanal
    zrodlo_opis: str                  # gotowy tekst do „Skąd to wiemy”, np. „Konto w ZUS”
    dokument_id: str | None = None    # dla uploadu
    strona: int | None = None
    pewnosc: float = 1.0              # 0–1; < 1 tylko dla odczytu AI
    aktywna: bool = False             # ustawia wyłącznie merge
    utworzono: datetime = Field(default_factory=_teraz)


class Osoba(BaseModel):
    id: str                           # "o1", "o2", …
    rola: Rola
    imie: str | None = None
    zalogowana: bool = False
    login: str | None = None          # konto testowe (symulowane logowanie) – tylko dla osoby zalogowanej
    pola: dict[str, list[WartoscPola]] = Field(default_factory=dict)
    # pole → id wartości wybranej ręcznie przez użytkownika (brak wpisu = wybór automatyczny według hierarchii)
    wybor_reczny: dict[str, str] = Field(default_factory=dict)

    def aktywna(self, pole: str) -> WartoscPola | None:
        return next((w for w in self.pola.get(pole, []) if w.aktywna), None)

    def wartosc(self, pole: str, domyslna: Any = None) -> Any:
        w = self.aktywna(pole)
        return w.wartosc if w is not None else domyslna


class Sprawa(BaseModel):
    id: str
    nazwa: str = "Moja sprawa"
    zdarzenie: str = "urodzenie"      # urodzenie | przysposobienie | rodzina_zastepcza
    utworzono: datetime = Field(default_factory=_teraz)
    wlasciciel: str | None = None     # login osoby zalogowanej; None = sprawa anonimowa
    osoby: list[Osoba] = Field(default_factory=list)
    dokumenty: list[str] = Field(default_factory=list)
    # Wynik ze strony decyzji ZUS – TYLKO do porównania/testów, nigdy jako dane wejściowe.
    oczekiwany_wynik: str | None = None
    liczniki_id: dict[str, int] = Field(default_factory=dict)

    def nowe_id(self, prefiks: str) -> str:
        n = self.liczniki_id.get(prefiks, 0) + 1
        self.liczniki_id[prefiks] = n
        return f"{prefiks}{n}"

    def osoba(self, osoba_id: str) -> Osoba | None:
        return next((o for o in self.osoby if o.id == osoba_id), None)

    def dodaj_osobe(self, rola: Rola, imie: str | None = None, **inne: Any) -> Osoba:
        o = Osoba(id=self.nowe_id("o"), rola=rola, imie=imie, **inne)
        self.osoby.append(o)
        return o

    def wnioskodawca(self) -> Osoba | None:
        """Osoba zalogowana, a gdy nikt nie jest zalogowany – pierwsza osoba (o1)."""
        return next((o for o in self.osoby if o.zalogowana), self.osoby[0] if self.osoby else None)
