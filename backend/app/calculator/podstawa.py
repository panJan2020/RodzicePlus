"""Podstawa wymiaru zasiłku (art. 36–50 ustawy zasiłkowej).

Kwoty liczymy w Decimal. Do groszy zaokrąglamy tylko tam, gdzie robi to ZUS: podstawę wymiaru
(tu) i stawkę dzienną (`kwoty.py`) – nigdzie indziej.

Kolejność ustalania podstawy (`ustal_podstawe`):
  1. poprzedni zasiłek z przerwą krótszą niż miesiąc → ta sama podstawa (art. 43),
  2. pracownik: miesiące z Z-3 (`miesiace[]`, art. 36–38, 45),
  3. pracownik: średnie wynagrodzenie brutto (O4s) – wynik ORIENTACYJNY,
  4. działalność: średnia zadeklarowana podstawa (Q1s) – wynik ORIENTACYJNY.
Pominięte na razie: zmiana etatu w okresie obliczeniowym (art. 40, pole O7), wynagrodzenie z umowy przy
ubezpieczeniu krótszym niż pełny miesiąc (art. 37), zlecenie z Z-3a i wzór art. 48a – etap 2.
"""
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from app.rules.wyliczone import dodaj_miesiace, jako_date, tekst_daty

GR = Decimal("0.01")


def zl(x: float | Decimal | str) -> Decimal:
    return Decimal(str(x)).quantize(GR, rounding=ROUND_HALF_UP)


def _d(x: Any) -> Decimal:
    return Decimal(str(x)) if x is not None else Decimal(0)


@dataclass
class MiesiacWynagrodzenia:
    """Jeden miesiąc z Z-3 (pole O4 `miesiace[]`). Kwoty brutto."""
    skladniki_stale: Decimal | float | str
    skladniki_zmienne: Decimal | float | str = 0
    dni_przepracowane: int = 0
    dni_obowiazujace: int = 0       # dni robocze, które pracownik był obowiązany przepracować
    stale_pelna_kwota: Decimal | float | str | None = None  # pełna stała kwota z umowy (do uzupełnienia)
    miesiac: str | None = None      # "RRRR-MM"

    @classmethod
    def z_pola(cls, m: dict[str, Any]) -> "MiesiacWynagrodzenia":
        return cls(skladniki_stale=m.get("skladniki_stale") or 0, skladniki_zmienne=m.get("skladniki_zmienne") or 0,
                   dni_przepracowane=int(m.get("dni_przepracowane") or 0),
                   dni_obowiazujace=int(m.get("dni_obowiazujace") or 0),
                   stale_pelna_kwota=m.get("stale_pelna_kwota"), miesiac=m.get("miesiac"))


def _netto_skladek(brutto: Decimal, p: dict[str, Any]) -> Decimal:
    return brutto * (Decimal(1) - Decimal(str(p["skladki_pracownika_proc"])))


def minimalna_podstawa(etat: Decimal, p: dict[str, Any]) -> Decimal:
    """Art. 45: minimalne wynagrodzenie minus składki; przy niepełnym etacie proporcjonalnie do wymiaru."""
    return _netto_skladek(_d(p["minimalne_wynagrodzenie"]), p) * min(etat, Decimal(1))


def podstawa_pracownik(miesiace: list[MiesiacWynagrodzenia], etat: Decimal | str | float, p: dict[str, Any],
                       premie_kwartalne_4kw: float = 0.0, premie_roczne: float = 0.0) -> Decimal:
    """Średnia z miesięcy po wyłączeniu/uzupełnieniu (art. 38) minus 13,71%, nie mniej niż minimum (art. 45)."""
    if not miesiace:
        raise ValueError("Brak miesięcy do ustalenia podstawy")
    prog = _d(p["art38_min_czesc_czasu_pracy"])

    def przepracowal_polowe(m: MiesiacWynagrodzenia) -> bool:
        return m.dni_obowiazujace == 0 or Decimal(m.dni_przepracowane) >= prog * m.dni_obowiazujace

    polowa = [m for m in miesiace if przepracowal_polowe(m)]
    # art. 38 ust. 3: jeśli w KAŻDYM miesiącu mniej niż połowa – bierzemy wszystkie (po uzupełnieniu)
    brane = polowa or miesiace

    kwoty: list[Decimal] = []
    for m in brane:
        niepelny = m.dni_obowiazujace and m.dni_przepracowane < m.dni_obowiazujace
        stale = _d(m.stale_pelna_kwota if (niepelny and m.stale_pelna_kwota) else m.skladniki_stale)
        zmienne = _d(m.skladniki_zmienne)
        if niepelny and m.dni_przepracowane:
            zmienne = zmienne / m.dni_przepracowane * m.dni_obowiazujace
        kwoty.append(stale + zmienne)

    srednia_brutto = sum(kwoty) / len(kwoty)
    srednia_brutto += _d(premie_kwartalne_4kw) / 12 + _d(premie_roczne) / 12
    podstawa = max(_netto_skladek(srednia_brutto, p), minimalna_podstawa(_d(etat), p))
    return zl(podstawa)


def podstawa_dobrowolne(podstawy_deklarowane: list[float | str | Decimal], p: dict[str, Any]) -> Decimal:
    """Zleceniobiorca / działalność: średni przychód (podstawa składek) minus 13,71% (art. 48).

    Limit: maksymalna podstawa dobrowolnego ubezpieczenia.
    TODO: wzór art. 48a dla ubezpieczenia krótszego niż 12 miesięcy (działalność) i art. 49.
    """
    if not podstawy_deklarowane:
        raise ValueError("Brak podstaw składek")
    limit = _d(p["max_podstawa_dobrowolne_brutto"])
    kwoty = [min(_d(x), limit) for x in podstawy_deklarowane]
    return zl(_netto_skladek(sum(kwoty) / len(kwoty), p))


# ---------- okres obliczeniowy i wybór sposobu ----------

def okres_obliczeniowy(data_prawa: date, poczatek_ubezpieczenia: date | None, p: dict[str, Any]) -> list[str]:
    """Miesiące "RRRR-MM" przed miesiącem powstania prawa (art. 36 ust. 1).

    Przy ubezpieczeniu krótszym niż okres obliczeniowy – tylko pełne miesiące ubezpieczenia (art. 36 ust. 2).
    Pusta lista = brak pełnego miesiąca (wtedy art. 37 – wynagrodzenie z umowy).
    """
    pierwszy = data_prawa.replace(day=1)
    wynik = []
    for i in range(p["okres_obliczeniowy_mies"], 0, -1):
        m = dodaj_miesiace(pierwszy, -i)
        if poczatek_ubezpieczenia is None or poczatek_ubezpieczenia <= m:
            wynik.append(m.strftime("%Y-%m"))
    return wynik


def podstawa_z_miesiecy(miesiace: list[dict[str, Any]], okres: list[str], etat: Any,
                        p: dict[str, Any]) -> Decimal | None:
    """Podstawa z miesięcy Z-3, które należą do okresu obliczeniowego. None – żaden miesiąc nie pasuje."""
    wybrane = [MiesiacWynagrodzenia.z_pola(m) for m in miesiace if m.get("miesiac") in okres]
    if not wybrane:
        return None
    return podstawa_pracownik(wybrane, etat=_d(etat or 1), p=p)


def podstawa_z_poprzedniego(poprzedni: dict[str, Any] | None, data_prawa: date,
                            p: dict[str, Any]) -> Decimal | None:
    """Art. 43: przerwa między zasiłkami krótsza niż miesiąc kalendarzowy → ta sama podstawa.

    Przerwa liczona od dnia po końcu poprzedniego zasiłku. Wyjątek „zmienił się wymiar etatu” – pomijamy.
    """
    if not poprzedni or not poprzedni.get("data_do") or poprzedni.get("podstawa") is None:
        return None
    pierwszy_dzien_przerwy = jako_date(poprzedni["data_do"]) + timedelta(days=1)
    if data_prawa < dodaj_miesiace(pierwszy_dzien_przerwy, p["art43_przerwa_mies"]):
        return zl(poprzedni["podstawa"])
    return None


@dataclass
class UstaleniePodstawy:
    kwota: Decimal | None = None
    orientacyjny: bool = False
    uwagi: list[str] = field(default_factory=list)
    brakujace: list[str] = field(default_factory=list)
    pola: list[str] = field(default_factory=list)  # pola, z których liczyliśmy


def ustal_podstawe(f: dict[str, Any], data_prawa: date, p: dict[str, Any]) -> UstaleniePodstawy:
    """Podstawa wymiaru dla jednej osoby. Nigdy nie rzuca wyjątku – braki trafiają do `brakujace`."""
    u = UstaleniePodstawy()
    tytuly = f.get("tytuly") or []

    poprzednia = podstawa_z_poprzedniego(f.get("poprzedni_zasilek"), data_prawa, p)
    if poprzednia is not None:
        u.kwota, u.pola = poprzednia, ["poprzedni_zasilek"]
        u.uwagi.append("Podstawa taka sama jak poprzedniego zasiłku – przerwa była krótsza niż miesiąc "
                       "(art. 43 ustawy zasiłkowej).")
        return u

    if "umowa_o_prace" in tytuly:
        return _pracownik(f, data_prawa, p, u)
    if "dzialalnosc" in tytuly or "wspolpraca" in tytuly:
        if f.get("podstawa_deklarowana_srednia"):
            u.kwota = podstawa_dobrowolne([f["podstawa_deklarowana_srednia"]], p)
            u.orientacyjny, u.pola = True, ["podstawa_deklarowana_srednia"]
            u.uwagi.append("Kwota orientacyjna – liczona ze średniej zadeklarowanej podstawy składek.")
        else:
            u.brakujace.append("podstawa_deklarowana_srednia")
        return u
    if "zlecenie" in tytuly:
        u.uwagi.append("Kwotę zasiłku z umowy zlecenia policzymy z zaświadczenia Z-3a – jeszcze tego nie obsługujemy.")
    return u


def _pracownik(f: dict[str, Any], data_prawa: date, p: dict[str, Any], u: UstaleniePodstawy) -> UstaleniePodstawy:
    poczatek = jako_date(f.get("chorobowe_od")) or jako_date(f.get("zatrudnienie_od"))
    okres = okres_obliczeniowy(data_prawa, poczatek, p)
    if not okres:
        u.uwagi.append(f"Ubezpieczenie trwa od {tekst_daty(poczatek)}, krócej niż pełny miesiąc przed powstaniem "
                       "prawa do zasiłku. Wtedy zasiłek liczy się od wynagrodzenia z umowy (art. 37 ustawy "
                       "zasiłkowej) – tego jeszcze nie liczymy.")
        u.brakujace.append("miesiace")
        return u

    if f.get("miesiace"):
        kwota = podstawa_z_miesiecy(f["miesiace"], okres, f.get("etat"), p)
        if kwota is not None:
            u.kwota, u.pola = kwota, ["miesiace", "etat", "chorobowe_od", "zatrudnienie_od"]
            if len(okres) < p["okres_obliczeniowy_mies"]:
                u.uwagi.append(f"Ubezpieczenie trwa krócej niż {p['okres_obliczeniowy_mies']} miesięcy – liczymy "
                               "z pełnych miesięcy ubezpieczenia (art. 36 ust. 2 ustawy zasiłkowej).")
            return u
        u.uwagi.append(f"W zaświadczeniu Z-3 nie ma miesięcy z okresu {okres[0]} – {okres[-1]}.")

    if f.get("srednie_wynagrodzenie_brutto"):
        m = MiesiacWynagrodzenia(skladniki_stale=f["srednie_wynagrodzenie_brutto"])
        u.kwota = podstawa_pracownik([m], etat=_d(f.get("etat") or 1), p=p)
        u.orientacyjny, u.pola = True, ["srednie_wynagrodzenie_brutto", "etat"]
        u.uwagi.append("Kwota orientacyjna – liczona ze średniego wynagrodzenia. Dokładnie policzymy ją "
                       "z zaświadczenia Z-3 od pracodawcy.")
        return u
    u.brakujace.append("srednie_wynagrodzenie_brutto")
    return u
