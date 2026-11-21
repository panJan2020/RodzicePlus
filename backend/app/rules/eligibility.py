"""Reguły prawa do świadczeń (FR-07..FR-10). Zwracają TAK / NIE / BRAK_DANYCH + uzasadnienie.

Zasada: każda funkcja dotyczy jednego świadczenia, nie rzuca wyjątków przy brakach,
tylko zwraca BRAK_DANYCH z listą pól do uzupełnienia (checklista w UI).
"""
from typing import Any, Callable

from app.domain.profile import Osoba
from app.domain.results import Status, WynikUprawnienia


def _kto_wyplaca(o: Osoba) -> str:
    tytuly = o.get("tytuly", [])
    if "dzialalnosc" in tytuly or "wspolpraca" in tytuly:
        return "ZUS"
    return "pracodawca (płatnik)" if o.get("platnik_ponad_20") == "ponad_20" else "ZUS"


def zasilek_macierzynski(o: Osoba, p: dict[str, Any]) -> WynikUprawnienia:
    w = WynikUprawnienia(swiadczenie="zasilek_macierzynski", status=Status.BRAK_DANYCH,
                         podstawa_prawna=["art. 29 ustawy zasiłkowej"])
    for pole in ("tytuly", "ubezpieczony_w_dniu_zdarzenia"):
        if o.get(pole) is None:
            w.brakujace_pola.append(pole)
    tytuly = o.get("tytuly", [])
    if any(t in tytuly for t in ("zlecenie", "dzialalnosc", "wspolpraca")) and "umowa_o_prace" not in tytuly \
            and o.get("chorobowe_dobrowolne") is None:
        w.brakujace_pola.append("chorobowe_dobrowolne")
    if w.brakujace_pola:
        w.uzasadnienie.append("Uzupełnij dane, aby ustalić prawo do zasiłku.")
        return w

    if o.get("ubezpieczony_w_dniu_zdarzenia") is False:
        # TODO: wyjątki – art. 30 (upadłość/likwidacja/śmierć pracodawcy, wyrok, umowa przedłużona do porodu)
        w.status = Status.NIE_PRZYSLUGUJE
        w.uzasadnienie.append("W dniu porodu (przyjęcia dziecka) nie podlegasz ubezpieczeniu chorobowemu.")
        return w

    zadluzenie = o.get("zadluzenie_kwota") or 0
    prog = p["minimalne_wynagrodzenie"] * p["prog_zadluzenia_proc_min_wyn"]
    if zadluzenie > prog:
        w.status = Status.NIE_PRZYSLUGUJE
        w.uzasadnienie.append(
            f"Zadłużenie składkowe {zadluzenie:.2f} zł przekracza {prog:.2f} zł – zasiłek przysługuje "
            "dopiero po spłacie (masz na nią 6 miesięcy).")
        w.podstawa_prawna.append("art. 2a ustawy zasiłkowej")
        return w

    w.status = Status.PRZYSLUGUJE
    w.uzasadnienie.append("W dniu powstania prawa podlegasz ubezpieczeniu chorobowemu.")
    w.kto_wyplaca = _kto_wyplaca(o)
    return w


# Rejestr – dopisujcie kolejne świadczenia (chorobowy w ciąży, ojcowski, uzupełniający, ...).
REGULY: dict[str, Callable[[Osoba, dict[str, Any]], WynikUprawnienia]] = {
    "zasilek_macierzynski": zasilek_macierzynski,
}


def ocen_wszystko(o: Osoba, p: dict[str, Any]) -> list[WynikUprawnienia]:
    return [regula(o, p) for regula in REGULY.values()]
