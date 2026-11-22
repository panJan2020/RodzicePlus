"""Silnik drzewa pytań: dla każdej osoby w sprawie liczy stan pytań z katalogu.

Stany pytania:
  * AKTYWNE     – warunki `pokaz_gdy` są spełnione; pytanie może mieć aktywną wartość albo nie,
  * ZABLOKOWANE – czeka na odpowiedź na pytanie nadrzędne (pole warunku nie ma jeszcze aktywnej wartości),
  * WYKLUCZONE  – odpowiedź na pytanie nadrzędne wyklucza to pytanie (np. sekcja Q przy umowie o pracę).

Komu zadajemy pytanie – kolumna `osoba` w katalogu: `rodzic` (matka / ojciec / drugi rodzic), `matka`, `ojciec`,
`dziecko`, `wnioskodawca` (osoba zalogowana albo o1). Warunek na polu, które nie dotyczy tej osoby (np. A1 `sytuacja`
w pytaniu dziecka), czytamy od wnioskodawcy.

Warunki liczymy tylko tutaj – Flutter rysuje gotowy wynik („Moje dane” i kreator).
Zmiana odpowiedzi niczego nie kasuje: wartości pytań wykluczonych zostają w profilu,
ale reguły i kalkulator dostają je odfiltrowane (`fakty`).
"""
import json
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import Enum
from functools import lru_cache
from typing import Any

from pydantic import BaseModel, Field

from app import merge
from app.config import QUESTIONS_FILE
from app.domain.model import ROLE_RODZICA, Kanal, Osoba, Rola, Sprawa, WartoscPola
from app.merge.scalanie import prog_pewnosci


class StatusPytania(str, Enum):
    AKTYWNE = "aktywne"
    ZABLOKOWANE = "zablokowane"
    WYKLUCZONE = "wykluczone"


class Opcja(BaseModel):
    wartosc: Any
    etykieta: str


class WartoscPolaApi(WartoscPola):
    do_sprawdzenia: bool = False  # niepewny odczyt AI (pewność poniżej progu z parametrów)


class Pytanie(BaseModel):
    """Element DaneOsoby i odpowiedzi /pytania (docs/api.md 3.2)."""
    id: str
    sekcja: str
    pole: str
    tresc: str
    typ: str
    opcje: list[Opcja] = Field(default_factory=list)
    pomoc: str | None = None
    gdzie_znalezc: str | None = None
    rodzaj: str
    edytowalne: bool                  # czy użytkownik może odpowiedzieć (kreator w źródłach, nie „tylko podgląd”)
    klucze: list[Opcja] = Field(default_factory=list)  # pola „na tytuł”: tytuły, dla których podajemy odpowiedź
    status: StatusPytania
    czeka_na: list[str] = Field(default_factory=list)  # ID pytań, na które trzeba najpierw odpowiedzieć
    wartosci: list[WartoscPolaApi] = Field(default_factory=list)
    aktywna_wartosc_id: str | None = None
    wybor_aktywnej: str = "automatyczny"  # automatyczny | uzytkownik
    konflikt: bool = False


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


def edytowalne(q: dict[str, Any]) -> bool:
    return q["typ"] != "okresy" and "kreator" in q.get("zrodla", []) and q["rodzaj"] in ("fakt", "plan")


# ---------- komu zadajemy pytanie ----------

def dotyczy(q: dict[str, Any], sprawa: Sprawa, osoba: Osoba) -> bool:
    for kod in q.get("osoba", ["rodzic"]):
        if kod == "wnioskodawca" and osoba is sprawa.wnioskodawca():
            return True
        if kod == "rodzic" and osoba.rola in ROLE_RODZICA:
            return True
        if kod == osoba.rola.value:
            return True
    return False


def osoba_dla_pola(sprawa: Sprawa, osoba: Osoba, pole: str) -> Osoba:
    """Czyje pole sprawdza warunek: tej osoby, jeśli pytanie jej dotyczy, w innym razie wnioskodawcy."""
    q = pytanie_dla_pola(pole)
    if q is None or dotyczy(q, sprawa, osoba):
        return osoba
    return sprawa.wnioskodawca() or osoba


# ---------- warunki ----------

def ma_wartosc(w: WartoscPola | None) -> bool:
    if w is None or w.wartosc is None:
        return False
    return not (isinstance(w.wartosc, (list, str, dict)) and len(w.wartosc) == 0)


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
            return Decimal(str(wartosc)) > Decimal(str(w["wieksze"]))
        except InvalidOperation:
            return False
    raise ValueError(f"Nieznany operator warunku: {w}")


class _Stany:
    """Liczy stany pytań w sprawie (z pamięcią wyników dla par osoba–pytanie)."""

    def __init__(self, sprawa: Sprawa):
        self.sprawa = sprawa
        self.wyniki: dict[tuple[str, str], tuple[StatusPytania, list[str]]] = {}

    def ocen(self, q: dict[str, Any], osoba: Osoba, w_trakcie: frozenset = frozenset()) -> tuple[StatusPytania, list[str]]:
        klucz = (osoba.id, q["id"])
        if klucz in self.wyniki:
            return self.wyniki[klucz]
        if klucz in w_trakcie:
            raise ValueError(f"Cykl w warunkach katalogu przy pytaniu {q['id']}")
        if not dotyczy(q, self.sprawa, osoba):
            return StatusPytania.WYKLUCZONE, []
        wykluczone, czeka_na = False, []
        for w in q.get("pokaz_gdy", []):
            wlasciciel = osoba_dla_pola(self.sprawa, osoba, w["pole"])
            nadrzedne = pytanie_dla_pola(w["pole"])
            if nadrzedne is None:  # pole spoza katalogu – liczymy tylko wartość
                stan, czeka = StatusPytania.AKTYWNE, []
            else:
                stan, czeka = self.ocen(nadrzedne, wlasciciel, w_trakcie | {klucz})
            aktywna = wlasciciel.aktywna(w["pole"])
            if stan == StatusPytania.WYKLUCZONE:
                wykluczone = True
            elif stan == StatusPytania.ZABLOKOWANE:
                czeka_na += czeka  # wskazujemy pytanie, na które da się odpowiedzieć teraz
            elif not ma_wartosc(aktywna):
                czeka_na.append(nadrzedne["id"] if nadrzedne else w["pole"])
            elif not _warunek(w, aktywna.wartosc):
                wykluczone = True
        if wykluczone:
            wynik = (StatusPytania.WYKLUCZONE, [])
        elif czeka_na:
            wynik = (StatusPytania.ZABLOKOWANE, list(dict.fromkeys(czeka_na)))
        else:
            wynik = (StatusPytania.AKTYWNE, [])
        self.wyniki[klucz] = wynik
        return wynik


def _klucze_tytulow(q: dict[str, Any], osoba: Osoba) -> list[Opcja]:
    """Pole „na tytuł”: aktywne tytuły osoby, które spełniają warunek pytania (np. tylko zlecenie i działalność)."""
    tytuly = osoba.wartosc("tytuly") or []
    dozwolone = None
    for w in q.get("pokaz_gdy", []):
        if w["pole"] == "tytuly":
            dozwolone = w.get("zawiera_ktores") or [w.get("zawiera")]
    etykiety = {o["wartosc"]: o["etykieta"] for o in pytanie_dla_pola("tytuly")["opcje"]}
    return [Opcja(wartosc=t, etykieta=etykiety.get(t, t)) for t in tytuly
            if (dozwolone is None or t in dozwolone) and t in etykiety]


def drzewo(sprawa: Sprawa, osoba: Osoba) -> list[Pytanie]:
    """Pytania z katalogu, które dotyczą tej osoby, z policzonym stanem (kolejność jak w katalogu)."""
    stany, prog = _Stany(sprawa), prog_pewnosci()
    lista = []
    for q in katalog():
        if not dotyczy(q, sprawa, osoba):
            continue
        status, czeka_na = stany.ocen(q, osoba)
        wartosci = osoba.pola.get(q["pole"], [])
        aktywna = next((w for w in wartosci if w.aktywna), None)
        lista.append(Pytanie(
            id=q["id"], sekcja=q["sekcja"], pole=q["pole"], tresc=q["tresc"], typ=q["typ"],
            opcje=[Opcja(**o) for o in q.get("opcje", [])], pomoc=q.get("pomoc"),
            gdzie_znalezc=q.get("gdzie_znalezc"), rodzaj=q["rodzaj"], edytowalne=edytowalne(q),
            klucze=_klucze_tytulow(q, osoba) if q.get("na_tytul") else [],
            status=status, czeka_na=czeka_na,
            wartosci=[WartoscPolaApi(**w.model_dump(), do_sprawdzenia=w.kanal == Kanal.UPLOAD and w.pewnosc < prog)
                      for w in wartosci],
            aktywna_wartosc_id=aktywna.id if aktywna and ma_wartosc(aktywna) else None,
            wybor_aktywnej=merge.wybor_aktywnej(osoba, q["pole"]), konflikt=merge.konflikt(osoba, q["pole"])))
    return lista


# ---------- widoki drzewa ----------

def nastepne_pytania(sprawa: Sprawa, osoba: Osoba) -> list[Pytanie]:
    """Dla kreatora: aktywne pytania bez aktywnej wartości, na które użytkownik może odpowiedzieć."""
    return [p for p in drzewo(sprawa, osoba)
            if p.status == StatusPytania.AKTYWNE and p.edytowalne and p.aktywna_wartosc_id is None]


def liczba_brakujacych(sprawa: Sprawa) -> int:
    return sum(len(nastepne_pytania(sprawa, o)) for o in sprawa.osoby)


def fakty(sprawa: Sprawa, osoba: Osoba) -> dict[str, Any]:
    """Aktywne wartości osoby bez pól pytań zablokowanych i wykluczonych – tego używają reguły i kalkulator.

    Pola spoza katalogu (np. miesiące wynagrodzeń z Z-3) zostają.
    """
    nieaktywne = {p.pole for p in drzewo(sprawa, osoba) if p.status != StatusPytania.AKTYWNE}
    return {k: v for k, v in merge.aktywne_wartosci(osoba).items() if k not in nieaktywne}


def pytania_do_uzupelnienia(sprawa: Sprawa, osoba: Osoba, pola: list[str]) -> list[str]:
    """Zamienia nazwy brakujących pól na ID pytań, na które użytkownik może odpowiedzieć teraz.

    * pytanie aktywne → jego ID,
    * pytanie zablokowane → ID pytań, na które czeka (np. A1),
    * pytanie wykluczone albo niedotyczące osoby → pomijamy.
    """
    stany = {p.pole: p for p in drzewo(sprawa, osoba)}
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


# ---------- odpowiedzi użytkownika ----------

class BlednaOdpowiedz(ValueError):
    """Wartość nie pasuje do typu pytania. Komunikat po polsku dla użytkownika."""


def _dziesietna(v: Any) -> str:
    try:
        return str(Decimal(str(v).replace(",", ".").replace(" ", "")).quantize(Decimal("0.01")))
    except InvalidOperation:
        raise BlednaOdpowiedz("Podaj liczbę, np. 1234,56.") from None


def _jedna(q: dict[str, Any], v: Any) -> Any:
    typ = q["typ"]
    if typ == "kwota" or (typ == "liczba" and q.get("dziesietna")):
        return _dziesietna(v)
    if typ == "liczba":
        d = Decimal(_dziesietna(v))
        if d != d.to_integral_value():
            raise BlednaOdpowiedz("Podaj liczbę całkowitą.")
        return int(d)
    if typ == "tak_nie":
        if not isinstance(v, bool):
            raise BlednaOdpowiedz("Wybierz „Tak” albo „Nie”.")
        return v
    if typ == "data":
        try:
            return date.fromisoformat(str(v)[:10]).isoformat()
        except ValueError:
            raise BlednaOdpowiedz("Podaj datę w formacie RRRR-MM-DD.") from None
    dozwolone = [o["wartosc"] for o in q.get("opcje", [])]
    if typ == "wybor":
        if v not in dozwolone:
            raise BlednaOdpowiedz("Wybierz jedną z podanych odpowiedzi.")
        return v
    if typ == "wielokrotny":
        if not isinstance(v, list) or any(x not in dozwolone for x in v):
            raise BlednaOdpowiedz("Wybierz odpowiedzi z listy.")
        return list(dict.fromkeys(v))
    raise BlednaOdpowiedz("Na to pytanie nie można odpowiedzieć ręcznie.")


def normalizuj(q: dict[str, Any], v: Any) -> Any:
    """Odpowiedź z formularza → wartość pola (kwoty i ułamki jako tekst, liczby całkowite jako liczby)."""
    if q.get("na_tytul"):
        if not isinstance(v, dict):
            raise BlednaOdpowiedz("Podaj odpowiedź dla każdego tytułu.")
        return {str(k): _jedna(q, x) for k, x in v.items() if x is not None}
    return _jedna(q, v)


# A2 („Kim jesteś dla dziecka?”) aktualizuje Osoba.rola – rola jest źródłem prawdy (docs/architektura.md, rozdz. 3).
ROLA_Z_ODPOWIEDZI = {"matka": Rola.MATKA, "ojciec": Rola.OJCIEC}


def rola_z_odpowiedzi(wartosc: Any) -> Rola:
    return ROLA_Z_ODPOWIEDZI.get(wartosc, Rola.DRUGI_RODZIC)


# ---------- dane osoby (GET /sprawy/{id}/dane) ----------

class Postep(BaseModel):
    odpowiedziane: int
    aktywne: int


class SekcjaDanych(BaseModel):
    id: str
    tytul: str
    postep: Postep
    pytania: list[Pytanie]


class OsobaSkrot(BaseModel):
    id: str
    rola: Rola
    imie: str | None = None


class DaneOsoby(BaseModel):
    osoba: OsobaSkrot
    postep: Postep
    sekcje: list[SekcjaDanych]


def _postep(pytania: list[Pytanie]) -> Postep:
    aktywne = [p for p in pytania if p.status == StatusPytania.AKTYWNE]
    return Postep(odpowiedziane=sum(p.aktywna_wartosc_id is not None for p in aktywne), aktywne=len(aktywne))


def dane_osoby(sprawa: Sprawa, osoba: Osoba) -> DaneOsoby:
    """Sekcje w kolejności słownika `sekcje`; sekcje bez pytań dla tej osoby pomijamy."""
    pytania = drzewo(sprawa, osoba)
    lista = []
    for sid, tytul in sekcje().items():
        w_sekcji = [p for p in pytania if p.sekcja == sid]
        if w_sekcji:
            lista.append(SekcjaDanych(id=sid, tytul=tytul, postep=_postep(w_sekcji), pytania=w_sekcji))
    return DaneOsoby(osoba=OsobaSkrot(id=osoba.id, rola=osoba.rola, imie=osoba.imie),
                     postep=_postep(pytania), sekcje=lista)
