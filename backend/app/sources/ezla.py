"""e-ZLA (symulacja): zwolnienia lekarskie z kodami (kod „B” = ciąża)."""
from datetime import date
from typing import Any

from app.domain.model import Kanal, Wystawca
from app.sources.baza import Zrodlo


class Ezla(Zrodlo):
    kod = "ezla"
    nazwa = "e-ZLA – zwolnienia lekarskie"
    wystawca = Wystawca.LEKARZ
    kanal = Kanal.EZLA
    opis = "Okresy niezdolności do pracy i kody zwolnień (kod B – ciąża)."
    zrodlo_opis = "e-ZLA"

    def _pola(self, dane: dict[str, Any], na_dzien: date) -> dict[str, Any]:
        return {"ezla": dane.get("ezla") or None}
