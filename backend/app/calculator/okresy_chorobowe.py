"""Dni niezdolności do pracy, wynagrodzenie płatnika i okres zasiłku chorobowego – same daty, bez prawa i kwot.

Reguła `rules/zasilek_chorobowy_ciaza.py` ustala PRAWO, a ten moduł rozkłada dni:
  * dni niezdolności = suma dni ze zwolnień (e-ZLA) i okresów wynagrodzenia chorobowego (przerwy między
    zwolnieniami nie liczą się do dni niezdolności – uproszczenie, do wyjaśnienia z mentorami),
  * pracownik: pierwsze dni choroby płaci pracodawca (wynagrodzenie, art. 92 KP), potem zasiłek,
  * zasiłek przysługuje najwyżej przez `okres_zasilkowy_dni.ciaza` dni niezdolności, licząc od pierwszego dnia
    (dni wynagrodzenia wliczają się do tego okresu).
Wszystkie liczby (33, 14, 50, 270, 30, 90) z parametrów.
"""
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

Odcinek = tuple[date, date, str | None]   # od, do (włącznie), kod literowy zwolnienia


def _data(v: Any) -> date | None:
    try:
        return date.fromisoformat(str(v)[:10])
    except (TypeError, ValueError):
        return None


def odcinki_z_pola(wartosc: Any) -> list[Odcinek]:
    """Wartość pola `ezla` / `wynagrodzenie_chorobowe_okres` → odcinki; elementy bez poprawnych dat pomijamy."""
    wynik = []
    for o in wartosc or []:
        od, do = _data(o.get("od")), _data(o.get("do"))
        if od and do and od <= do:
            wynik.append((od, do, o.get("kod") or None))
    return wynik


def dni_odcinka(od: date, do: date) -> list[date]:
    return [od + timedelta(days=i) for i in range((do - od).days + 1)]


def dni_odcinkow(odcinki: list[Odcinek]) -> set[date]:
    return {d for od, do, _ in odcinki for d in dni_odcinka(od, do)}


def poczatek_niezdolnosci(f: dict[str, Any]) -> date | None:
    """Pierwszy dzień niezdolności: najwcześniejszy dzień ze zwolnień albo okresu wynagrodzenia chorobowego."""
    dni = dni_odcinkow(odcinki_z_pola(f.get("ezla")) + odcinki_z_pola(f.get("wynagrodzenie_chorobowe_okres")))
    return min(dni) if dni else None


def okres_wyczekiwania_dni(dobrowolne: bool, p: dict[str, Any]) -> int:
    return p["wyczekiwanie_dni"]["dobrowolne" if dobrowolne else "obowiazkowe"]


def wyczekiwanie_spelnione(poczatek_ubezpieczenia: date, poczatek_niezdolnosci_: date, wymagane: int) -> bool:
    """Niezdolność może zacząć się najwcześniej `wymagane` dni po początku ubezpieczenia (30. dzień po nim)."""
    return (poczatek_niezdolnosci_ - poczatek_ubezpieczenia).days >= wymagane


def pierwszy_dzien_po_wyczekiwaniu(poczatek_ubezpieczenia: date, wymagane: int) -> date:
    return poczatek_ubezpieczenia + timedelta(days=wymagane)


def limit_wynagrodzenia_dni(urodzony: date | None, poczatek: date, p: dict[str, Any]) -> int:
    """33 dni wynagrodzenia chorobowego w roku; 14 dni od roku następującego po tym, w którym pracownik
    ukończył 50 lat (art. 92 KP). Brak daty urodzenia → limit podstawowy."""
    dni = p["wynagrodzenie_chorobowe_dni"]
    if urodzony and poczatek.year - urodzony.year > p["wynagrodzenie_chorobowe_wiek"]:
        return dni["po_50"]
    return dni["standard"]


@dataclass
class Rozliczenie:
    poczatek: date
    dni_niezdolnosci: list[date]                 # wszystkie dni niezdolności (posortowane)
    wynagrodzenie: list[date] = field(default_factory=list)   # dni płatne przez pracodawcę
    wynagrodzenie_zalozone: bool = False         # brak okresu z Z-3 – dni wynagrodzenia zgadnięte z limitu
    zasilek: list[date] = field(default_factory=list)         # dni, za które przysługuje zasiłek
    ucieto_limitem: bool = False                 # część dni poza okresem zasiłkowym

    @property
    def zasilek_od(self) -> date | None:
        return self.zasilek[0] if self.zasilek else None

    @property
    def zasilek_do(self) -> date | None:
        return self.zasilek[-1] if self.zasilek else None


def rozlicz(ezla: list[Odcinek], wynagrodzenie: list[Odcinek], pracownik: bool, limit_wynagrodzenia: int,
            p: dict[str, Any]) -> Rozliczenie:
    """Dni wynagrodzenia i zasiłku. Okres wynagrodzenia z Z-3 (gdy jest) wyznacza koniec płatności pracodawcy;
    bez niego zakładamy, że pracodawca płaci pierwsze `limit_wynagrodzenia` dni niezdolności."""
    dni = sorted(dni_odcinkow(ezla) | dni_odcinkow(wynagrodzenie))
    r = Rozliczenie(poczatek=dni[0], dni_niezdolnosci=dni)
    dozwolone = dni[: p["okres_zasilkowy_dni"]["ciaza"]]
    r.ucieto_limitem = len(dni) > len(dozwolone)
    if not pracownik:
        r.zasilek = dozwolone
        return r
    if wynagrodzenie:
        r.wynagrodzenie = sorted(dni_odcinkow(wynagrodzenie))
    else:
        r.wynagrodzenie, r.wynagrodzenie_zalozone = dni[:limit_wynagrodzenia], True
    koniec = r.wynagrodzenie[-1] if r.wynagrodzenie else None
    r.zasilek = [d for d in dozwolone if koniec is None or d > koniec]
    return r
