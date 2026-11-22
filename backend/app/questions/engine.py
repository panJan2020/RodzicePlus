"""Silnik drzewa pytań: dla każdego pytania z katalogu liczy jego stan.

Stany pytania:
  * AKTYWNE     – warunki `pokaz_gdy` są spełnione; pytanie może mieć odpowiedź albo nie,
  * ZABLOKOWANE – czeka na odpowiedź na pytanie nadrzędne (pole warunku nie ma jeszcze wartości),
  * WYKLUCZONE  – odpowiedź na pytanie nadrzędne wyklucza to pytanie (np. sekcja Q przy umowie o pracę).

Warunki liczymy tylko tutaj – Flutter rysuje gotowy wynik (zakładka „Dane” i kreator).
Zmiana odpowiedzi niczego nie kasuje: wartości pytań wykluczonych zostają w profilu,
ale reguły i kalkulator dostają je odfiltrowane (`aktywne_pola`).
"""
import json
from enum import Enum
from functools import lru_cache
from typing import Any

from pydantic import BaseModel, Field

from app.config import QUESTIONS_FILE
from app.domain.profile import FieldValue, Osoba
from app.extraction.merge import PROG_PEWNOSCI  # odczyt AI poniżej progu = „do sprawdzenia”


class StatusPytania(str, Enum):
    AKTYWNE = "aktywne"
    ZABLOKOWANE = "zablokowane"
    WYKLUCZONE = "wykluczone"


class Opcja(BaseModel):
    wartosc: Any
    etykieta: str


class PytanieWDrzewie(BaseModel):
    id: str
    sekcja: str
    pole: str
    tresc: str
    typ: str
    opcje: list[Opcja] = Field(default_factory=list)
    pomoc: str | None = None
    gdzie_znalezc: str | None = None
    status: StatusPytania
    czeka_na: list[str] = Field(default_factory=list)  # ID pytań, na które trzeba najpierw odpowiedzieć
    wartosc: FieldValue | None = None
    odpowiedziane: bool = False
    do_sprawdzenia: bool = False  # odczyt z dokumentu z niską pewnością


# ---------- katalog ----------

@lru_cache
def _plik() -> dict[str, Any]:
    return json.loads(QUESTIONS_FILE.read_text(encoding="utf-8"))


def katalog() -> list[dict[str, Any]]:
    return _plik()["pytania"]


def sekcje() -> dict[str, str]:
    return _plik()["sekcje"]


@lru_cache
def _po_polu() -> dict[str, dict[str, Any]]:
    return {p["pole"]: p for p in katalog()}


@lru_cache
def _po_id() -> dict[str, dict[str, Any]]:
    return {p["id"]: p for p in katalog()}


def pytanie_dla_pola(pole: str) -> dict[str, Any] | None:
    return _po_polu().get(pole)


def pytanie(id_: str) -> dict[str, Any] | None:
    return _po_id().get(id_)


def pola_z_dokumentow() -> list[dict[str, Any]]:
    """Pola, które Claude może wyciągnąć ze skanów (schemat odczytu)."""
    return [p for p in katalog() if p.get("z_dokumentow")]


# ---------- warunki ----------

def ma_wartosc(fv: FieldValue | None) -> bool:
    if fv is None or fv.wartosc is None:
        return False
    return not (isinstance(fv.wartosc, (list, str)) and len(fv.wartosc) == 0)


def _jako_lista(v: Any) -> list[Any]:
    return v if isinstance(v, list) else [v]


def _warunek(w: dict[str, Any], wartosc: Any) -> bool:
    if "zawiera" in w:
        return w["zawiera"] in _jako_lista(wartosc)
    if "zawiera_ktores" in w:
        return any(x in _jako_lista(wartosc) for x in w["zawiera_ktores"])
    if "rowne" in w:
        return wartosc == w["rowne"]
    if "rozne" in w:
        return wartosc != w["rozne"]
    if "wieksze" in w:
        try:
            return float(wartosc) > float(w["wieksze"])
        except (TypeError, ValueError):
            return False
    raise ValueError(f"Nieznany operator warunku: {w}")


def drzewo(osoba: Osoba) -> list[PytanieWDrzewie]:
    """Wszystkie pytania z katalogu z policzonym stanem (kolejność jak w katalogu)."""
    wyniki: dict[str, tuple[StatusPytania, list[str]]] = {}

    def ocen(p: dict[str, Any], w_trakcie: frozenset[str] = frozenset()) -> tuple[StatusPytania, list[str]]:
        if p["id"] in wyniki:
            return wyniki[p["id"]]
        if p["id"] in w_trakcie:
            raise ValueError(f"Cykl w warunkach katalogu przy pytaniu {p['id']}")
        wykluczone, czeka_na = False, []
        for w in p.get("pokaz_gdy", []):
            rodzic = pytanie_dla_pola(w["pole"])
            if rodzic is None:  # pole spoza katalogu – liczymy tylko wartość
                fv = osoba.pola.get(w["pole"])
                stan_rodzica, czeka_rodzica = StatusPytania.AKTYWNE, []
            else:
                stan_rodzica, czeka_rodzica = ocen(rodzic, w_trakcie | {p["id"]})
                fv = osoba.pola.get(rodzic["pole"])
            if stan_rodzica == StatusPytania.WYKLUCZONE:
                wykluczone = True
            elif stan_rodzica == StatusPytania.ZABLOKOWANE:
                czeka_na += czeka_rodzica  # wskazujemy pytanie, na które da się odpowiedzieć teraz
            elif not ma_wartosc(fv):
                czeka_na.append(rodzic["id"] if rodzic else w["pole"])
            elif not _warunek(w, fv.wartosc):
                wykluczone = True
        if wykluczone:
            wynik = (StatusPytania.WYKLUCZONE, [])
        elif czeka_na:
            wynik = (StatusPytania.ZABLOKOWANE, list(dict.fromkeys(czeka_na)))
        else:
            wynik = (StatusPytania.AKTYWNE, [])
        wyniki[p["id"]] = wynik
        return wynik

    lista = []
    for p in katalog():
        status, czeka_na = ocen(p)
        fv = osoba.pola.get(p["pole"])
        odp = ma_wartosc(fv)
        lista.append(PytanieWDrzewie(
            id=p["id"], sekcja=p["sekcja"], pole=p["pole"], tresc=p["tresc"], typ=p["typ"],
            opcje=[Opcja(**o) for o in p.get("opcje", [])], pomoc=p.get("pomoc"),
            gdzie_znalezc=p.get("gdzie_znalezc"), status=status, czeka_na=czeka_na,
            wartosc=fv, odpowiedziane=odp,
            do_sprawdzenia=bool(odp and fv.pewnosc is not None and fv.pewnosc < PROG_PEWNOSCI
                                and not fv.potwierdzone)))
    return lista


# ---------- widoki drzewa ----------

def nastepne_pytania(osoba: Osoba) -> list[dict[str, Any]]:
    """Dla kreatora: aktywne pytania bez odpowiedzi (z żadnego źródła)."""
    return [pytanie(p.id) for p in drzewo(osoba) if p.status == StatusPytania.AKTYWNE and not p.odpowiedziane]


def aktywne_pola(osoba: Osoba) -> Osoba:
    """Kopia osoby bez wartości pytań zablokowanych i wykluczonych.

    Tego używają reguły i kalkulator. Pola spoza katalogu (np. wynagrodzenia z Z-3) zostają.
    """
    nieaktywne = {p.pole for p in drzewo(osoba) if p.status != StatusPytania.AKTYWNE}
    return Osoba(rola=osoba.rola, pola={k: v for k, v in osoba.pola.items() if k not in nieaktywne})


def pytania_do_uzupelnienia(osoba: Osoba, pola: list[str]) -> list[str]:
    """Zamienia nazwy brakujących pól na ID pytań, na które użytkownik może odpowiedzieć teraz.

    * pytanie aktywne → jego ID,
    * pytanie zablokowane → ID pytań, na które czeka (np. A1),
    * pytanie wykluczone → pomijamy (nie dotyczy tej sytuacji).
    """
    stany = {p.pole: p for p in drzewo(osoba)}
    ids: list[str] = []
    for pole in pola:
        p = stany.get(pole)
        if p is None:
            continue
        if p.status == StatusPytania.AKTYWNE:
            ids.append(p.id)
        elif p.status == StatusPytania.ZABLOKOWANE:
            ids += p.czeka_na
    return list(dict.fromkeys(ids))


class Postep(BaseModel):
    odpowiedziane: int
    aktywne: int


class SekcjaDanych(BaseModel):
    id: str
    tytul: str
    postep: Postep
    pytania: list[PytanieWDrzewie]


class DaneOsoby(BaseModel):
    """Odpowiedź GET /sprawy/{id}/dane – całe drzewo pytań jednej osoby, pogrupowane w sekcje."""
    osoba: int
    rola: str
    postep: Postep
    sekcje: list[SekcjaDanych]


def _postep(pytania: list[PytanieWDrzewie]) -> Postep:
    aktywne = [p for p in pytania if p.status == StatusPytania.AKTYWNE]
    return Postep(odpowiedziane=sum(p.odpowiedziane for p in aktywne), aktywne=len(aktywne))


def dane_osoby(osoba: Osoba, indeks: int = 0) -> DaneOsoby:
    """Sekcje w kolejności słownika `sekcje`; puste sekcje (bez pytań w katalogu) pomijamy."""
    pytania = drzewo(osoba)
    lista = []
    for sid, tytul in sekcje().items():
        w_sekcji = [p for p in pytania if p.sekcja == sid]
        if w_sekcji:
            lista.append(SekcjaDanych(id=sid, tytul=tytul, postep=_postep(w_sekcji), pytania=w_sekcji))
    return DaneOsoby(osoba=indeks, rola=osoba.rola, postep=_postep(pytania), sekcje=lista)
