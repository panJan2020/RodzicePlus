"""Symulacja danych z konta ubezpieczonego w ZUS (FR-02).

Źródłem są fikcyjne `okresy_ubezpieczenia` z `zus_data.json`. Z nich wyliczamy stan na wskazany dzień:
* czy osoba podlega dziś ubezpieczeniu chorobowemu (i z jakiego tytułu),
* pola profilu sprawy: `tytuly`, `chorobowe_od`, `chorobowe_dobrowolne`, `platnik_ponad_20`.

W produkcji ten moduł zastąpi wywołanie usługi ZUS (dane z CSIZS / PUE) – kształt wyniku może zostać ten sam.
"""
import json
from datetime import date
from typing import Any

from pydantic import BaseModel

from app.config import MOCKS_FILE

TYTULY_OPIS = {
    "umowa_o_prace": "Umowa o pracę",
    "zlecenie": "Umowa zlecenia",
    "dzialalnosc": "Działalność gospodarcza",
    "wspolpraca": "Współpraca przy działalności",
    "dzielo": "Umowa o dzieło",
    "inne": "Inny tytuł",
}


class OkresUbezpieczenia(BaseModel):
    tytul: str
    tytul_opis: str
    platnik: str
    platnik_ponad_20: str | None = None  # "ponad_20" / "do_20" – kto wypłaca zasiłek
    od: date
    do: date | None = None  # None = trwa
    chorobowe: bool
    chorobowe_dobrowolne: bool = False
    aktywny: bool  # czy trwa w dniu `stan_na`


class DaneUbezpieczenia(BaseModel):
    stan_na: date
    ubezpieczony_chorobowo: bool
    podsumowanie: str
    wyjasnienia: list[str]
    okresy: list[OkresUbezpieczenia]
    # Pola profilu sprawy (nazwy = docs/pytania_kalkulator.md)
    tytuly: list[str]
    chorobowe_od: date | None = None
    chorobowe_dobrowolne: bool | None = None
    platnik_ponad_20: str | None = None


def konto(login: str) -> dict[str, Any] | None:
    return json.loads(MOCKS_FILE.read_text(encoding="utf-8"))["uzytkownicy"].get(login)


def _okresy(surowe: list[dict[str, Any]], dzien: date) -> list[OkresUbezpieczenia]:
    wynik = []
    for o in surowe:
        od = date.fromisoformat(o["od"])
        do = date.fromisoformat(o["do"]) if o.get("do") else None
        wynik.append(OkresUbezpieczenia(
            tytul=o["tytul"], tytul_opis=TYTULY_OPIS.get(o["tytul"], o["tytul"]), platnik=o["platnik"],
            platnik_ponad_20=o.get("platnik_ponad_20"), od=od, do=do, chorobowe=o["chorobowe"],
            chorobowe_dobrowolne=o.get("chorobowe_dobrowolne", False),
            aktywny=od <= dzien and (do is None or do >= dzien)))
    return sorted(wynik, key=lambda x: (not x.aktywny, x.od))


def _data(d: date) -> str:
    return d.strftime("%d.%m.%Y")


def dane_ubezpieczenia(dane_konta: dict[str, Any], dzien: date | None = None) -> DaneUbezpieczenia:
    dzien = dzien or date.today()
    okresy = _okresy(dane_konta.get("okresy_ubezpieczenia", []), dzien)
    aktywne = [o for o in okresy if o.aktywny]
    chorobowe = [o for o in aktywne if o.chorobowe]

    tytuly = list(dict.fromkeys(o.tytul for o in aktywne)) or ["brak"]
    platnik = next((o.platnik_ponad_20 for o in aktywne
                    if o.tytul in ("umowa_o_prace", "zlecenie") and o.platnik_ponad_20), None)

    wyjasnienia: list[str] = []
    if chorobowe:
        od = min(o.od for o in chorobowe)
        # Obowiązkowe (np. umowa o pracę) „wygrywa” z dobrowolnym – wtedy okres wyczekiwania jest krótszy.
        dobrowolne = all(o.chorobowe_dobrowolne for o in chorobowe)
        nazwy = ", ".join(o.tytul_opis.lower() for o in chorobowe)
        podsumowanie = f"Podlegasz ubezpieczeniu chorobowemu ({nazwy})."
        wyjasnienia.append(f"Ubezpieczenie chorobowe trwa nieprzerwanie od {_data(od)}.")
        wyjasnienia.append("Ubezpieczenie jest dobrowolne – opłacasz je sam(a)." if dobrowolne
                           else "Ubezpieczenie jest obowiązkowe – zgłasza Cię płatnik.")
        for o in aktywne:
            if not o.chorobowe:
                wyjasnienia.append(f"Z tytułu „{o.tytul_opis.lower()}” ({o.platnik}) nie masz ubezpieczenia "
                                   "chorobowego – nie liczy się do zasiłków.")
    else:
        od, dobrowolne = None, None
        podsumowanie = "Obecnie nie podlegasz ubezpieczeniu chorobowemu."
        zakonczone = [o for o in okresy if o.chorobowe and o.do and o.do < dzien]
        if zakonczone:
            ost = max(zakonczone, key=lambda o: o.do)
            wyjasnienia.append(f"Ostatnie ubezpieczenie chorobowe ({ost.tytul_opis.lower()}, {ost.platnik}) "
                               f"skończyło się {_data(ost.do)}.")
        for o in aktywne:
            wyjasnienia.append(f"{o.tytul_opis} ({o.platnik}) nie daje ubezpieczenia chorobowego.")
        wyjasnienia.append("Bez ubezpieczenia chorobowego w dniu porodu zasiłek macierzyński co do zasady "
                           "nie przysługuje (art. 29 ustawy zasiłkowej). Są wyjątki, np. gdy umowę rozwiązano "
                           "z powodu upadłości lub likwidacji pracodawcy (art. 30 ustawy zasiłkowej).")

    return DaneUbezpieczenia(stan_na=dzien, ubezpieczony_chorobowo=bool(chorobowe), podsumowanie=podsumowanie,
                             wyjasnienia=wyjasnienia, okresy=okresy, tytuly=tytuly, chorobowe_od=od,
                             chorobowe_dobrowolne=dobrowolne, platnik_ponad_20=platnik)


def pola_profilu(dane_konta: dict[str, Any], dzien: date | None = None) -> dict[str, Any]:
    """Wartości do zapisania w profilu sprawy (zrodlo=zus). Pomija puste."""
    u = dane_ubezpieczenia(dane_konta, dzien)
    pola: dict[str, Any] = {
        "tytuly": u.tytuly,
        "chorobowe_od": u.chorobowe_od.isoformat() if u.chorobowe_od else None,
        "chorobowe_dobrowolne": u.chorobowe_dobrowolne,
        "platnik_ponad_20": u.platnik_ponad_20,
    }
    for k in ("data_urodzenia", "etat", "zadluzenie_kwota", "ezla", "srednie_wynagrodzenie_brutto",
              "podstawa_deklarowana_srednia"):
        pola[k] = dane_konta.get(k)
    return {k: v for k, v in pola.items() if v is not None}
