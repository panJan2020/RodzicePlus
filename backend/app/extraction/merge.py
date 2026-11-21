"""Scalanie danych z dokumentów z profilem sprawy + wykrywanie sprzeczności.

Zasady pierwszeństwa:
  1. wartość potwierdzona przez użytkownika – nigdy nie nadpisujemy,
  2. dokument z wyższą pewnością,
  3. różne wartości z dokumentów → Konflikt (UI prosi użytkownika o wybór).
"""
from typing import Any

from app.domain.profile import FieldValue, Konflikt, Osoba, Sprawa, Zrodlo

PROG_PEWNOSCI = 0.6  # poniżej – wartość pokazujemy jako "do sprawdzenia"


def _osoba(sprawa: Sprawa, rola: str) -> Osoba:
    for o in sprawa.osoby:
        if o.rola == rola:
            return o
    nowa = Osoba(rola=rola)
    sprawa.osoby.append(nowa)
    return nowa


def scal(sprawa: Sprawa, dane: dict[str, Any]) -> Sprawa:
    if dane.get("oczekiwany_wynik"):
        sprawa.oczekiwany_wynik = dane["oczekiwany_wynik"]

    for item in dane.get("pola", []):
        osoba = _osoba(sprawa, item.get("osoba") or "matka")
        nowa = FieldValue(wartosc=item["wartosc"], zrodlo=Zrodlo.DOKUMENT, dokument=item.get("dokument"),
                          strona=item.get("strona"), pewnosc=item.get("pewnosc"))
        stara = osoba.pola.get(item["pole"])
        if stara is None:
            osoba.pola[item["pole"]] = nowa
        elif stara.potwierdzone:
            continue
        elif stara.wartosc != nowa.wartosc:
            sprawa.konflikty.append(Konflikt(pole=item["pole"], wartosci=[stara, nowa]))
            if (nowa.pewnosc or 0) > (stara.pewnosc or 0):
                osoba.pola[item["pole"]] = nowa

    if dane.get("wynagrodzenia_miesieczne"):
        osoba = _osoba(sprawa, "matka")  # TODO: przypisanie do właściwej osoby
        osoba.pola["wynagrodzenia_miesieczne"] = FieldValue(
            wartosc=dane["wynagrodzenia_miesieczne"], zrodlo=Zrodlo.DOKUMENT, dokument="Z-3")
    return sprawa
