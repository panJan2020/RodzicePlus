"""Kwoty zasiłku: stawka miesięczna, dzienna (1/30), za okres, podwyższenie do świadczenia rodzicielskiego."""
from decimal import Decimal
from typing import Any

from app.calculator.podstawa import zl


def miesieczny(podstawa: Decimal, stawka: float) -> Decimal:
    return zl(podstawa * Decimal(str(stawka)))


def dzienny(podstawa: Decimal, stawka: float, p: dict[str, Any]) -> Decimal:
    return zl(podstawa * Decimal(str(stawka)) / p["dzielnik_dzienny"])


def za_okres(podstawa: Decimal, stawka: float, dni: int, p: dict[str, Any]) -> Decimal:
    """Zasiłek przysługuje za każdy dzień, także wolny (art. 11 ust. 4).

    UWAGA: ZUS liczy stawkę dzienną zaokrągloną do groszy × liczba dni.
    Sprawdźcie na sprawach testowych, czy wyniki zgadzają się co do grosza.
    """
    return zl(dzienny(podstawa, stawka, p) * dni)


def z_podwyzszeniem(kwota_miesieczna: Decimal, p: dict[str, Any]) -> tuple[Decimal, bool]:
    """Art. 31 ust. 3a: podwyższenie do kwoty świadczenia rodzicielskiego.

    TODO (pytanie do mentorów): porównujemy kwotę brutto czy po zaliczce PIT (Poradnik mówi: po PIT).
    """
    minimum = Decimal(str(p["swiadczenie_rodzicielskie"]))
    if kwota_miesieczna < minimum:
        return minimum, True
    return kwota_miesieczna, False
