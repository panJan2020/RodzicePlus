"""ZUS – dane płatnika (symulacja): czy płatnik zgłasza ponad 20 osób (kto wypłaca zasiłek), zadłużenie składkowe."""
from datetime import date
from typing import Any

from app.domain.model import Kanal, Wystawca
from app.sources.baza import Zrodlo

# Tytuły, przy których zasiłek może wypłacać płatnik (art. 61 ustawy zasiłkowej).
TYTULY_Z_PLATNIKIEM = ("umowa_o_prace", "zlecenie")


class ZusPlatnik(Zrodlo):
    kod = "zus_platnik"
    nazwa = "ZUS – dane płatnika"
    wystawca = Wystawca.ZUS
    kanal = Kanal.ZUS_PLATNIK
    opis = "Liczba osób zgłoszonych przez płatnika (do 20 / ponad 20), zadłużenie składkowe."
    zrodlo_opis = "Dane płatnika w ZUS"

    def _pola(self, dane: dict[str, Any], na_dzien: date) -> dict[str, Any]:
        okresy = dane.get("zus_konto", {}).get("okresy_ubezpieczenia", [])
        aktywne = [o for o in okresy if date.fromisoformat(o["od"]) <= na_dzien
                   and (not o.get("do") or date.fromisoformat(o["do"]) >= na_dzien)]
        platnik = {o["tytul"]: o["platnik_ponad_20"] for o in aktywne
                   if o["tytul"] in TYTULY_Z_PLATNIKIEM and o.get("platnik_ponad_20")}
        return {"platnik_ponad_20": platnik or None,
                "zadluzenie_kwota": dane.get("zus_platnik", {}).get("zadluzenie_kwota")}
