"""Kwoty zasiłku: stawka dzienna (1/30), kwota za okres, kwota miesięczna, podwyższenie do świadczenia rodzicielskiego.

Zaokrąglenia jak w ZUS: stawka dzienna do groszy, potem × liczba dni (art. 11 ust. 4 – zasiłek za każdy dzień).
Kwota miesięczna to informacja dla użytkownika (podstawa × stawka), pokazywana w groszach.
"""
from calendar import monthrange
from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from app.calculator.podstawa import zl


def miesieczny(podstawa: Decimal, stawka: float | Decimal) -> Decimal:
    return zl(podstawa * Decimal(str(stawka)))


def dzienny(podstawa: Decimal, stawka: float | Decimal, p: dict[str, Any]) -> Decimal:
    """Art. 36 ust. 3 (stosowany do zasiłku macierzyńskiego): 1/30 kwoty miesięcznej, zaokrąglona do groszy."""
    return zl(podstawa * Decimal(str(stawka)) / p["dzielnik_dzienny"])


def za_okres(podstawa: Decimal, stawka: float | Decimal, dni: int, p: dict[str, Any]) -> Decimal:
    """Stawka dzienna (już w groszach) × liczba dni – bez dodatkowego zaokrąglania."""
    return dzienny(podstawa, stawka, p) * dni


@dataclass
class GrupaStawki:
    stawka: Decimal
    dni: int
    dzienna: Decimal


def kwota_za_dni(podstawa: Decimal, stawki_dni: list[Decimal], p: dict[str, Any]) -> tuple[Decimal, list[GrupaStawki]]:
    """Zasiłek chorobowy: stawka dzienna (zaokrąglona do groszy) × liczba dni, osobno dla każdej stawki
    (np. 100% za dni z kodem B i 80% za pozostałe). `stawki_dni` – stawka każdego dnia zasiłku."""
    grupy = [GrupaStawki(s, n, dzienny(podstawa, s, p)) for s, n in sorted(Counter(stawki_dni).items(), reverse=True)]
    return sum((g.dzienna * g.dni for g in grupy), Decimal(0)), grupy


def z_podwyzszeniem(kwota_miesieczna: Decimal, p: dict[str, Any]) -> tuple[Decimal, bool]:
    """Art. 31 ust. 3a: podwyższenie do kwoty świadczenia rodzicielskiego.

    DO POTWIERDZENIA (docs Z.2): porównujemy kwotę brutto; Poradnik mówi o kwocie po zaliczce na PIT.
    """
    minimum = zl(p["swiadczenie_rodzicielskie"])
    if kwota_miesieczna < minimum:
        return minimum, True
    return kwota_miesieczna, False


def za_okres_podwyzszony(od: date, do: date, p: dict[str, Any]) -> Decimal:
    """Art. 31 ust. 3c: kwota świadczenia rodzicielskiego za każdy pełny miesiąc kalendarzowy,
    za niepełny – proporcjonalnie (kwota × dni / dni w tym miesiącu, w groszach).

    DO POTWIERDZENIA: sposób liczenia niepełnego miesiąca – sprawdzić na decyzjach ZUS.
    """
    kwota = zl(p["swiadczenie_rodzicielskie"])
    suma, dzien = Decimal(0), od
    while dzien <= do:
        dni_w_miesiacu = monthrange(dzien.year, dzien.month)[1]
        koniec_miesiaca = dzien.replace(day=dni_w_miesiacu)
        ostatni = min(koniec_miesiaca, do)
        dni = (ostatni - dzien).days + 1
        suma += kwota if dni == dni_w_miesiacu else zl(kwota * dni / dni_w_miesiacu)
        dzien = ostatni + timedelta(days=1)
    return suma
