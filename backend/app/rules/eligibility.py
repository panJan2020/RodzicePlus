"""Reguły prawa do świadczeń. Zwracają przysługuje / nie przysługuje / brak danych + uzasadnienie.

Zasada: każda funkcja dotyczy jednego świadczenia, nie rzuca wyjątków przy brakach,
tylko zwraca BRAK_DANYCH z listą pól do uzupełnienia (checklista w UI).

Funkcja reguły:
  * dostaje `fakty` – AKTYWNE wartości osoby (bez pól pytań wykluczonych) – i parametry,
  * do `brakujace` wpisuje NAZWY pól (np. "tytuly") – tak łatwiej pisać reguły,
  * warstwa API zamienia je na ID pytań (np. "B1") z treścią dla UI.
"""
from decimal import Decimal
from typing import Any, Callable

from pydantic import BaseModel, Field

from app.domain.results import Powod, Status
from app.rules import wyliczone


class WynikReguly(BaseModel):
    swiadczenie: str
    nazwa: str
    status: Status = Status.BRAK_DANYCH
    uzasadnienie: list[str] = Field(default_factory=list)
    powody: list[Powod] = Field(default_factory=list)
    brakujace: list[str] = Field(default_factory=list)   # nazwy pól
    kto_wyplaca: str | None = None
    kto_wyplaca_opis: str | None = None
    podstawa_prawna: list[str] = Field(default_factory=list)


def kto_wyplaca(f: dict[str, Any], p: dict[str, Any]) -> tuple[str, str]:
    """Płatnik zgłaszający ponad próg osób wypłaca sam; w innym razie i przy działalności – ZUS (art. 61)."""
    tytuly = f.get("tytuly") or []
    if "dzialalnosc" in tytuly or "wspolpraca" in tytuly:
        return "zus", "Zasiłek wypłaci ZUS (prowadzisz działalność)."
    platnik = f.get("platnik_ponad_20") or {}
    if any(platnik.get(t) == "ponad_20" for t in tytuly):
        return "platnik", (f"Zasiłek wypłaci pracodawca – zgłasza do ubezpieczenia chorobowego ponad "
                           f"{p['duzy_platnik_powyzej']} osób (art. 61 ustawy zasiłkowej).")
    return "zus", "Zasiłek wypłaci ZUS (art. 61 ustawy zasiłkowej)."


def zasilek_macierzynski(f: dict[str, Any], p: dict[str, Any]) -> WynikReguly:
    w = WynikReguly(swiadczenie="zasilek_macierzynski", nazwa="Zasiłek macierzyński",
                    podstawa_prawna=["art. 29 ustawy zasiłkowej"])
    ub = wyliczone.ubezpieczony_w_dniu(f, wyliczone.data_zdarzenia(f), p)
    w.brakujace += ub.brakujace
    w.brakujace = list(dict.fromkeys(w.brakujace))
    if w.brakujace:
        w.uzasadnienie.append("Uzupełnij dane, aby ustalić prawo do zasiłku.")
        return w

    if ub.wartosc is False:
        # TODO: wyjątki – art. 30 (upadłość/likwidacja/śmierć pracodawcy, wyrok, umowa przedłużona do porodu)
        w.status = Status.NIE_PRZYSLUGUJE
        w.uzasadnienie += ub.uzasadnienie
        w.powody.append(Powod(pole="ubezpieczony_w_dniu_zdarzenia", wartosc="nie",
                              komunikat="Brak ubezpieczenia chorobowego w dniu porodu."))
        return w

    zadluzenie = Decimal(str(f.get("zadluzenie_kwota") or "0"))
    prog = (Decimal(str(p["minimalne_wynagrodzenie"])) * Decimal(str(p["prog_zadluzenia_proc_min_wyn"]))) \
        .quantize(Decimal("0.01"))
    if zadluzenie > prog:
        w.status = Status.NIE_PRZYSLUGUJE
        w.uzasadnienie.append(
            f"Zadłużenie składkowe {zadluzenie} zł przekracza {prog} zł – zasiłek przysługuje "
            "dopiero po spłacie (masz na nią 6 miesięcy).")
        w.powody.append(Powod(pole="zadluzenie_kwota", wartosc=str(zadluzenie),
                              komunikat=f"Zadłużenie powyżej {prog} zł."))
        w.podstawa_prawna.append("art. 2a ustawy zasiłkowej")
        return w

    w.status = Status.PRZYSLUGUJE
    w.uzasadnienie.append("W dniu powstania prawa podlegasz ubezpieczeniu chorobowemu.")
    w.kto_wyplaca, w.kto_wyplaca_opis = kto_wyplaca(f, p)
    return w


# Rejestr – dopisujcie kolejne świadczenia (chorobowy w ciąży, ojcowski, uzupełniający, ...).
REGULY: dict[str, Callable[[dict[str, Any], dict[str, Any]], WynikReguly]] = {
    "zasilek_macierzynski": zasilek_macierzynski,
}
