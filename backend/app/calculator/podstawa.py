"""Podstawa wymiaru zasiłku (art. 36–50 ustawy zasiłkowej).

Kwoty liczymy w Decimal i zaokrąglamy do groszy dopiero na końcu – float
daje błędy rzędu 0,01 zł, a jurorzy porównują wyniki z decyzjami ZUS.
"""
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

GR = Decimal("0.01")


def zl(x: float | Decimal) -> Decimal:
    return Decimal(str(x)).quantize(GR, rounding=ROUND_HALF_UP)


@dataclass
class MiesiacWynagrodzenia:
    """Jeden miesiąc z Z-3 (pkt 16)."""
    skladniki_stale: float          # brutto
    skladniki_zmienne: float = 0.0  # brutto, w kwocie faktycznej
    dni_przepracowane: int = 0
    dni_obowiazujace: int = 0       # dni robocze, które pracownik był obowiązany przepracować
    stale_pelna_kwota: float | None = None  # pełna stała kwota z umowy (do uzupełnienia)


def _netto_skladek(brutto: Decimal, p: dict[str, Any]) -> Decimal:
    return brutto * (Decimal(1) - Decimal(str(p["skladki_pracownika_proc"])))


def podstawa_pracownik(miesiace: list[MiesiacWynagrodzenia], pelny_etat: bool, p: dict[str, Any],
                       premie_kwartalne_4kw: float = 0.0, premie_roczne: float = 0.0) -> Decimal:
    """Średnia z miesięcy po wyłączeniu/uzupełnieniu (art. 38) minus 13,71%, nie mniej niż minimum (art. 45)."""
    if not miesiace:
        raise ValueError("Brak miesięcy do ustalenia podstawy")

    def przepracowal_polowe(m: MiesiacWynagrodzenia) -> bool:
        return m.dni_obowiazujace == 0 or m.dni_przepracowane * 2 >= m.dni_obowiazujace

    polowa = [m for m in miesiace if przepracowal_polowe(m)]
    # art. 38 ust. 3: jeśli w KAŻDYM miesiącu mniej niż połowa – bierzemy wszystkie (po uzupełnieniu)
    brane = polowa or miesiace

    kwoty: list[Decimal] = []
    for m in brane:
        niepelny = m.dni_obowiazujace and m.dni_przepracowane < m.dni_obowiazujace
        stale = Decimal(str(m.stale_pelna_kwota if (niepelny and m.stale_pelna_kwota) else m.skladniki_stale))
        zmienne = Decimal(str(m.skladniki_zmienne))
        if niepelny and m.dni_przepracowane:
            zmienne = zmienne / m.dni_przepracowane * m.dni_obowiazujace
        kwoty.append(stale + zmienne)

    srednia_brutto = sum(kwoty) / len(kwoty)
    srednia_brutto += Decimal(str(premie_kwartalne_4kw)) / 12 + Decimal(str(premie_roczne)) / 12
    podstawa = _netto_skladek(srednia_brutto, p)

    if pelny_etat:
        minimum = _netto_skladek(Decimal(str(p["minimalne_wynagrodzenie"])), p)
        podstawa = max(podstawa, minimum)
    return zl(podstawa)


def podstawa_dobrowolne(podstawy_deklarowane: list[float], p: dict[str, Any]) -> Decimal:
    """Zleceniobiorca / działalność: średni przychód (podstawa składek) minus 13,71% (art. 48).

    Limit: maksymalna podstawa dobrowolnego ubezpieczenia.
    TODO: wzór art. 48a dla ubezpieczenia krótszego niż 12 miesięcy (działalność) i art. 49.
    """
    if not podstawy_deklarowane:
        raise ValueError("Brak podstaw składek")
    limit = Decimal(str(p["max_podstawa_dobrowolne_brutto"]))
    kwoty = [min(Decimal(str(x)), limit) for x in podstawy_deklarowane]
    return zl(_netto_skladek(sum(kwoty) / len(kwoty), p))
