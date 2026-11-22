"""mObywatel / rejestr PESEL (symulacja): dane osobowe zalogowanej osoby."""
from datetime import date
from typing import Any

from app.domain.model import Kanal, Wystawca
from app.sources.baza import Zrodlo


class Mobywatel(Zrodlo):
    kod = "mobywatel"
    nazwa = "mObywatel (rejestr PESEL)"
    wystawca = Wystawca.URZAD
    kanal = Kanal.MOBYWATEL
    opis = "Imię, nazwisko, data urodzenia."
    zrodlo_opis = "mObywatel (rejestr PESEL)"

    def _pola(self, dane: dict[str, Any], na_dzien: date) -> dict[str, Any]:
        return {"data_urodzenia": dane.get("mobywatel", {}).get("data_urodzenia")}
