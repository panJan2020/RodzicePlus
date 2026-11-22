"""Adaptery źródeł danych (symulacje). Rejestr `ZRODLA`: kod → adapter.

Dodajemy tylko źródła, dla których mamy dane. Kolejne (rsc, zus_historia, pue) – razem z funkcjami, które ich potrzebują.
"""
from app.sources.baza import Zrodlo, ZrodloNiedostepne, konta, konto
from app.sources.ezla import Ezla
from app.sources.mobywatel import Mobywatel
from app.sources.zus_konto import ZusKonto
from app.sources.zus_platnik import ZusPlatnik

ZRODLA: dict[str, Zrodlo] = {z.kod: z for z in (Mobywatel(), ZusKonto(), ZusPlatnik(), Ezla())}

__all__ = ["ZRODLA", "Zrodlo", "ZrodloNiedostepne", "konta", "konto"]
