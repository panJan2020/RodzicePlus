"""Całość na prawdziwych sprawach ZUS: odczyt z cache → merge → reguła → porównanie z decyzją ZUS.

PDF-y są tylko lokalnie (data/sprawy_zus/, poza repo) i nie wywołujemy Claude: odczyt idzie wyłącznie z cache
(data/cache/). Brak pliku albo cache → test jest pomijany. Nie zapisujemy tu żadnych danych z dokumentów,
tylko statusy.
"""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import config, merge
from app.domain.model import Kanal, Rola, WartoscPola, Wystawca
from app.extraction import mapowanie, pipeline
from app.main import app
from app.storage import memory

KATALOG = Path(__file__).resolve().parents[2] / "data" / "sprawy_zus"
c = TestClient(app)


class _BrakCache(Exception):
    pass


def _bez_api(*_, **__):
    raise _BrakCache()


def _sprawa_z_cache(nazwa_pliku: str) -> str:
    plik = KATALOG / nazwa_pliku
    if not plik.exists():
        pytest.skip(f"brak lokalnego pliku {nazwa_pliku}")
    sid = c.post("/sprawy").json()["id"]
    s = memory.pobierz(sid)
    try:
        pipeline.przetworz_plik(s, nazwa_pliku, plik.read_bytes(), zapytaj=_bez_api)
    except _BrakCache:
        pytest.skip("brak odczytu w cache (uruchom scripts.odczyt_sprawy)")
    merge.dodaj(s, s.wnioskodawca(), "sytuacja", WartoscPola(wartosc=["ciaza"], wystawca=Wystawca.UZYTKOWNIK,
                                                              kanal=Kanal.KREATOR, zrodlo_opis="test"), rodzaj="fakt")
    memory.zapisz(s)
    return sid


def test_sprawa_anny_odczyt_merge_regula_porownanie_zgodne():
    sid = _sprawa_z_cache("anna_chorobowy_ciaza.pdf")
    assert memory.pobierz(sid).oczekiwany_wynik                           # decyzja ZUS tylko w oczekiwany_wynik
    wynik = next(w for w in c.get(f"/sprawy/{sid}/swiadczenia").json() if w["swiadczenie"] == "zasilek_chorobowy_ciaza")
    assert wynik["status"] == "przysluguje" and wynik["kto_wyplaca"] == "zus"
    p = c.get(f"/sprawy/{sid}/porownanie").json()
    assert p["zgodnosc"] == "zgodne" and p["decyzja_zus"]["rozstrzygniecie"] == "przyznano"


def test_sprawa_z_dzialalnoscia_brak_danych_albo_zgodnosc_porownania():
    sid = _sprawa_z_cache("dzialalnosc_chorobowy_ciaza.pdf")
    wynik = next(w for w in c.get(f"/sprawy/{sid}/swiadczenia").json() if w["swiadczenie"] == "zasilek_chorobowy_ciaza")
    assert wynik["status"] in ("brak_danych", "przysluguje")              # nigdy „nie przysługuje” z niepewnego odczytu
    p = c.get(f"/sprawy/{sid}/porownanie").json()
    assert p["zgodnosc"] in ("zgodne", "nie_do_porownania")
    if wynik["status"] == "brak_danych":
        assert any("Wgraj zwolnienie" in x for x in wynik["co_zrobic"])
