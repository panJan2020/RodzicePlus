"""Adaptery źródeł danych (sources/): wspólny interfejs, wystawca i kanał, stan ubezpieczenia na dzień."""
from datetime import date

import pytest

from app import merge
from app.domain.model import Kanal, Rola, Sprawa, Wystawca
from app.sources import ZRODLA, ZrodloNiedostepne, konta
from app.sources.zus_konto import dane_ubezpieczenia, okresy_z_pola

DZIEN = date(2026, 11, 21)


def _osoba(login: str | None):
    s = Sprawa(id="sp1")
    return s, s.dodaj_osobe(Rola.MATKA, login=login, zalogowana=login is not None)


def _pobierz(kod: str, login: str, dzien: date = DZIEN) -> dict:
    s, o = _osoba(login)
    return {k: w.wartosc for k, w in ZRODLA[kod].pobierz(s, o, dzien).items()}


def test_rejestr_zrodel_i_dane_kont_testowych():
    assert set(ZRODLA) == {"mobywatel", "zus_konto", "zus_platnik", "ezla"}
    assert {"anna", "marta", "piotr", "kasia"} <= set(konta())


@pytest.mark.parametrize("kod,wystawca,kanal", [
    ("mobywatel", Wystawca.URZAD, Kanal.MOBYWATEL),
    ("zus_konto", Wystawca.ZUS, Kanal.ZUS_KONTO),
    ("zus_platnik", Wystawca.ZUS, Kanal.ZUS_PLATNIK),
    ("ezla", Wystawca.LEKARZ, Kanal.EZLA),
])
def test_adapter_zwraca_wartosci_z_wystawca_i_kanalem(kod, wystawca, kanal):
    s, o = _osoba("anna")
    wynik = ZRODLA[kod].pobierz(s, o, DZIEN)
    assert wynik, kod
    for w in wynik.values():
        assert w.wystawca == wystawca and w.kanal == kanal and w.zrodlo_opis and w.pewnosc == 1.0
        assert w.id == "" and not w.aktywna  # adapter niczego nie zapisuje – robi to merge


def test_adapter_wymaga_zalogowania():
    s, o = _osoba(None)
    with pytest.raises(ZrodloNiedostepne):
        ZRODLA["zus_konto"].pobierz(s, o, DZIEN)


def test_zus_konto_pracownica_ubezpieczona_obowiazkowo():
    p = _pobierz("zus_konto", "anna")
    assert p["tytuly"] == ["umowa_o_prace"] and p["chorobowe"] == {"umowa_o_prace": True}
    assert p["chorobowe_od"] == "2021-03-01" and p["chorobowe_dobrowolne"] is False
    assert p["etat"] == "1.00" and p["srednie_wynagrodzenie_brutto"] == "8200.00"  # kwoty i ułamki jako tekst
    assert p["okresy_ubezpieczenia"][0]["platnik"] == "Hurtownia Przykładowa S.A."


def test_zus_konto_dzialalnosc_chorobowe_dobrowolne():
    p = _pobierz("zus_konto", "marta")
    assert p["tytuly"] == ["dzialalnosc"] and p["chorobowe_dobrowolne"] is True
    assert "etat" not in p and p["podstawa_deklarowana_srednia"] == "5652.00"


def test_zus_konto_zbieg_umowy_i_zlecenia_bez_chorobowego():
    p = _pobierz("zus_konto", "piotr")
    assert p["tytuly"] == ["umowa_o_prace", "zlecenie"]
    assert p["chorobowe"] == {"umowa_o_prace": True, "zlecenie": False}
    assert p["chorobowe_dobrowolne"] is False  # obowiązkowe z umowy o pracę


def test_zus_konto_brak_ubezpieczenia_po_ustaniu_umowy_art29():
    p = _pobierz("zus_konto", "kasia")
    assert p["tytuly"] == ["dzielo"] and "chorobowe_od" not in p
    u = dane_ubezpieczenia(okresy_z_pola(p["okresy_ubezpieczenia"], DZIEN), DZIEN)
    assert u.ubezpieczony_chorobowo is False
    assert any("31.08.2026" in w for w in u.wyjasnienia) and any("art. 29" in w for w in u.wyjasnienia)


def test_zus_konto_stan_na_dzien_w_trakcie_dawnej_umowy():
    p = _pobierz("zus_konto", "kasia", date(2026, 5, 1))
    assert p["tytuly"] == ["umowa_o_prace"] and p["chorobowe_od"] == "2022-01-01"


def test_zus_platnik_slownik_na_tytul():
    assert _pobierz("zus_platnik", "anna")["platnik_ponad_20"] == {"umowa_o_prace": "ponad_20"}
    assert _pobierz("zus_platnik", "piotr")["platnik_ponad_20"] == {"umowa_o_prace": "do_20", "zlecenie": "do_20"}
    marta = _pobierz("zus_platnik", "marta")
    assert "platnik_ponad_20" not in marta and marta["zadluzenie_kwota"] == "312.40"


def test_mobywatel_i_ezla():
    assert _pobierz("mobywatel", "anna") == {"data_urodzenia": "1994-05-12"}
    assert _pobierz("ezla", "anna")["ezla"][0]["kod"] == "B"
    assert _pobierz("ezla", "marta") == {}  # brak zwolnień = brak wartości


def test_pobranie_przez_merge_zus_wygrywa_z_uzytkownikiem():
    s, o = _osoba("anna")
    from app.domain.model import WartoscPola
    merge.dodaj(s, o, "etat", WartoscPola(wartosc="0.50", wystawca=Wystawca.UZYTKOWNIK, kanal=Kanal.KREATOR,
                                          zrodlo_opis="Twoja odpowiedź"), prog=0.6)
    for pole, w in ZRODLA["zus_konto"].pobierz(s, o, DZIEN).items():
        merge.dodaj(s, o, pole, w, prog=0.6)
    assert o.wartosc("etat") == "1.00" and merge.konflikt(o, "etat")
    assert len(o.pola["etat"]) == 2  # wartość użytkownika nie przepada
