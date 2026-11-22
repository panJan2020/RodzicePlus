"""ZUS – konto ubezpieczonego (symulacja): tytuły i okresy ubezpieczenia, ubezpieczenie chorobowe, etat,
przybliżone wynagrodzenie (RCA) i podstawa składek.

Z fikcyjnych `okresy_ubezpieczenia` liczymy stan na wskazany dzień (`dane_ubezpieczenia`) – ten sam wynik
pokazuje ekran „Moje ubezpieczenie”.
"""
from datetime import date
from typing import Any

from pydantic import BaseModel

from app.domain.model import Kanal, Wystawca
from app.sources.baza import Zrodlo

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
    platnik_ponad_20: bool | None = None  # True – płatnik zgłasza ponad 20 osób (wypłaca zasiłek sam)
    od: date
    do: date | None = None  # None = trwa
    wymiar_etatu: str | None = None
    chorobowe: bool
    chorobowe_dobrowolne: bool = False
    aktywny: bool  # czy trwa w dniu `stan_na`
    zrodlo_opis: str = "Konto w ZUS (symulacja)"


class DaneUbezpieczenia(BaseModel):
    stan_na: date
    ubezpieczony_chorobowo: bool
    podsumowanie: str
    wyjasnienia: list[str]
    okresy: list[OkresUbezpieczenia]


def _ponad_20(v: str | None) -> bool | None:
    return None if v is None else v == "ponad_20"


def _okresy(surowe: list[dict[str, Any]], dzien: date, etat: str | None = None) -> list[OkresUbezpieczenia]:
    wynik = []
    for o in surowe:
        od = date.fromisoformat(o["od"])
        do = date.fromisoformat(o["do"]) if o.get("do") else None
        wynik.append(OkresUbezpieczenia(
            tytul=o["tytul"], tytul_opis=TYTULY_OPIS.get(o["tytul"], o["tytul"]), platnik=o["platnik"],
            platnik_ponad_20=_ponad_20(o.get("platnik_ponad_20")), od=od, do=do,
            wymiar_etatu=etat if o["tytul"] == "umowa_o_prace" else None,
            chorobowe=o["chorobowe"], chorobowe_dobrowolne=o.get("chorobowe_dobrowolne", False),
            aktywny=od <= dzien and (do is None or do >= dzien)))
    return sorted(wynik, key=lambda x: (not x.aktywny, x.od))


def _data(d: date) -> str:
    return d.strftime("%d.%m.%Y")


def okresy_z_pola(wartosc: list[dict[str, Any]], dzien: date) -> list[OkresUbezpieczenia]:
    """Okresy zapisane w polu `okresy_ubezpieczenia` → modele z flagą `aktywny` na wskazany dzień."""
    wynik = []
    for o in wartosc:
        od = date.fromisoformat(o["od"])
        do = date.fromisoformat(o["do"]) if o.get("do") else None
        wynik.append(OkresUbezpieczenia(**{**o, "od": od, "do": do,
                                           "tytul_opis": TYTULY_OPIS.get(o["tytul"], o["tytul"]),
                                           "aktywny": od <= dzien and (do is None or do >= dzien)}))
    return sorted(wynik, key=lambda x: (not x.aktywny, x.od))


def dane_ubezpieczenia(okresy: list[OkresUbezpieczenia], dzien: date) -> DaneUbezpieczenia:
    """Czy osoba podlega w danym dniu ubezpieczeniu chorobowemu – z gotowymi tekstami dla użytkownika."""
    aktywne = [o for o in okresy if o.aktywny]
    chorobowe = [o for o in aktywne if o.chorobowe]

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
                             wyjasnienia=wyjasnienia, okresy=okresy)


class ZusKonto(Zrodlo):
    kod = "zus_konto"
    nazwa = "ZUS – konto ubezpieczonego"
    wystawca = Wystawca.ZUS
    kanal = Kanal.ZUS_KONTO
    opis = "Tytuły i okresy ubezpieczenia, ubezpieczenie chorobowe, wymiar etatu, podstawy składek."
    zrodlo_opis = "Konto w ZUS"

    def _pola(self, dane: dict[str, Any], na_dzien: date) -> dict[str, Any]:
        k = dane.get("zus_konto", {})
        okresy = _okresy(k.get("okresy_ubezpieczenia", []), na_dzien, k.get("etat"))
        aktywne = [o for o in okresy if o.aktywny]
        chorobowe = [o for o in aktywne if o.chorobowe]
        return {
            "okresy_ubezpieczenia": [o.model_dump(mode="json", exclude={"aktywny", "tytul_opis", "zrodlo_opis"})
                                     for o in okresy],
            "tytuly": list(dict.fromkeys(o.tytul for o in aktywne)) or ["brak"],
            "chorobowe": {o.tytul: o.chorobowe for o in aktywne} or None,
            "chorobowe_od": min(o.od for o in chorobowe).isoformat() if chorobowe else None,
            "chorobowe_dobrowolne": all(o.chorobowe_dobrowolne for o in chorobowe) if chorobowe else None,
            "etat": k.get("etat") if any(o.tytul == "umowa_o_prace" for o in aktywne) else None,
            "srednie_wynagrodzenie_brutto": k.get("srednie_wynagrodzenie_brutto"),
            "podstawa_deklarowana_srednia": k.get("podstawa_deklarowana_srednia"),
        }
