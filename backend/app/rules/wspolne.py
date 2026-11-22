"""Wspólne elementy reguł: kontekst wejściowy, wynik reguły, kto wypłaca, teksty kwot i dat.

Zasada: reguła dostaje AKTYWNE fakty (bez pól pytań wykluczonych), wybory scenariusza i parametry.
Nie rzuca wyjątków przy brakach – zwraca nazwy brakujących pól; API zamienia je na pytania z katalogu.
"""
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.formaty import kwota_tekst  # noqa: F401 – re-eksport dla reguł i testów
from app.domain.model import Kanal, WartoscPola, Wystawca
from app.domain.results import KwotaWyniku, OkresWyniku, Powod, Status, Warunek

TYTULY_Z_PLATNIKIEM = ("umowa_o_prace", "zlecenie")   # zasiłek może wypłacać płatnik (art. 61)
TYTULY_DZIALALNOSC = ("dzialalnosc", "wspolpraca")


@dataclass
class Kontekst:
    fakty: dict[str, Any]                       # aktywne wartości osoby
    fakty_dziecka: dict[str, Any] = field(default_factory=dict)
    wybory: dict[str, Any] = field(default_factory=dict)   # Scenariusz.wybory
    pochodzenie: dict[str, WartoscPola] = field(default_factory=dict)  # pole → aktywna WartoscPola
    dzis: date = field(default_factory=date.today)
    prog_pewnosci: float = 0.6


class WynikReguly(BaseModel):
    """Wynik jednej reguły dla jednej osoby – API dokleja osobę, scenariusz i treści pytań."""
    swiadczenie: str
    nazwa: str
    status: Status = Status.BRAK_DANYCH
    podsumowanie: str = ""
    okres: OkresWyniku | None = None
    kwota: KwotaWyniku | None = None
    stawka: str | None = None
    okres_wynagrodzenia: OkresWyniku | None = None
    kto_wyplaca: str | None = None
    kto_wyplaca_opis: str | None = None
    gdzie_zlozyc: str | None = None
    uzasadnienie: list[str] = Field(default_factory=list)
    powody: list[Powod] = Field(default_factory=list)
    warunki: list[Warunek] = Field(default_factory=list)
    brakujace: list[str] = Field(default_factory=list)              # nazwy pól
    co_zrobic: list[str] = Field(default_factory=list)
    orientacyjny: bool = False
    pola_do_potwierdzenia: list[str] = Field(default_factory=list)  # nazwy pól
    ryzyka: list[str] = Field(default_factory=list)
    uwagi: list[str] = Field(default_factory=list)
    podstawa_prawna: list[str] = Field(default_factory=list)


def niepewna(w: WartoscPola, prog: float) -> bool:
    """Wartość „do potwierdzenia”: deklaracja użytkownika albo niepewny odczyt AI."""
    return w.wystawca == Wystawca.UZYTKOWNIK or (w.kanal == Kanal.UPLOAD and w.pewnosc < prog)


def pola_niepewne(k: Kontekst, pola: list[str]) -> list[str]:
    return [p for p in dict.fromkeys(pola) if p in k.pochodzenie and niepewna(k.pochodzenie[p], k.prog_pewnosci)]


def zlagodz_odmowe(w: "WynikReguly", k: Kontekst, pola: list[str]) -> bool:
    """Odmowa („nie przysługuje”) nie może opierać się na wartości odczytanej z dokumentu z pewnością ≤ progu
    (≤, nie <: próg „niepewny odczyt” zostaje bez zmian). Wtedy wynik to „warunkowo” z polami do potwierdzenia."""
    niskie = [p for p in dict.fromkeys(pola) if p in k.pochodzenie and k.pochodzenie[p].kanal == Kanal.UPLOAD
              and k.pochodzenie[p].pewnosc <= k.prog_pewnosci]
    if w.status != Status.NIE_PRZYSLUGUJE or not niskie:
        return False
    w.status = Status.WARUNKOWO
    w.orientacyjny = True
    w.pola_do_potwierdzenia = list(dict.fromkeys(w.pola_do_potwierdzenia + niskie))
    w.warunki.append(Warunek(opis="Dane, na których opiera się odmowa, odczytaliśmy z dokumentu z małą pewnością – "
                                  "sprawdź je i popraw, jeśli są błędne"))
    w.uwagi.append("Odmowa opiera się na danych odczytanych z dokumentu z małą pewnością, dlatego wynik jest "
                   "warunkowy, a nie ostateczny. Sprawdź: " + ", ".join(niskie) + ".")
    w.podsumowanie = "Do sprawdzenia – " + w.podsumowanie
    return True


def kto_wyplaca(f: dict[str, Any], p: dict[str, Any]) -> tuple[str | None, str, bool]:
    """C2 (art. 61): (kto, opis, czy brakuje odpowiedzi C1). Płatnik zgłaszający ponad próg osób wypłaca sam."""
    tytuly = f.get("tytuly") or []
    if any(t in TYTULY_DZIALALNOSC for t in tytuly):
        return "zus", "Zasiłek wypłaci ZUS – prowadzisz działalność (art. 61 ustawy zasiłkowej).", False
    platnik = f.get("platnik_ponad_20") or {}
    odpowiedzi = [platnik.get(t) for t in tytuly if t in TYTULY_Z_PLATNIKIEM]
    if "ponad_20" in odpowiedzi:
        return "platnik", (f"Zasiłek wypłaci pracodawca – zgłasza do ubezpieczenia chorobowego ponad "
                           f"{p['duzy_platnik_powyzej']} osób (art. 61 ustawy zasiłkowej)."), False
    if any(o in (None, "nie_wiem") for o in odpowiedzi):
        return None, (f"Zapytaj w kadrach, ilu ubezpieczonych zgłasza Twój pracodawca. Gdy ponad "
                      f"{p['duzy_platnik_powyzej']} osób – zasiłek wypłaci pracodawca, w innym razie ZUS "
                      "(art. 61 ustawy zasiłkowej)."), True
    return "zus", "Zasiłek wypłaci ZUS (art. 61 ustawy zasiłkowej).", False


def gdzie_zlozyc(kto: str | None, f: dict[str, Any]) -> str:
    if kto == "platnik":
        return "U pracodawcy: wniosek o zasiłek macierzyński (ZAM) złóż w kadrach."
    if kto == "zus":
        if "umowa_o_prace" in (f.get("tytuly") or []):
            return ("W ZUS: wniosek ZAM przez PUE/eZUS albo w placówce. Pracodawca przekaże do ZUS "
                    "zaświadczenie Z-3.")
        return "W ZUS: wniosek ZAM przez PUE/eZUS albo w placówce."
    return "W kadrach albo w ZUS – zależy, kto wypłaca zasiłek."


def dni_tekst(n: int) -> str:
    return "1 dzień" if n == 1 else f"{n} dni"


def tygodnie_tekst(n: int) -> str:
    """Odmiana: 1 tydzień, 2–4 tygodnie (poza 12–14), 5+ tygodni."""
    if n == 1:
        return "1 tydzień"
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return f"{n} tygodnie"
    return f"{n} tygodni"
