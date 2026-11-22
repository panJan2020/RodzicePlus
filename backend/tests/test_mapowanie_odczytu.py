"""Odczyt dokumentu → Dokument + WartoscPola (bez wywołań Claude – zapisane, fikcyjne odpowiedzi).

Sprawdzamy: wystawcę wg typu dokumentu, numer strony z oryginalnego pliku, pismo ZUS bez pól,
decyzję tylko w `oczekiwany_wynik`, brak zgadywania kodu B, usuwanie dokumentu z jego wartościami.
"""
import io
import json
from pathlib import Path

import pytest
from pypdf import PdfWriter

from app import config, merge
from app.domain.model import Kanal, Rola, Sprawa, Wystawca
from app.extraction import mapowanie, pipeline
from app.extraction.podzial import Fragment

FIKSTURA = json.loads((Path(__file__).parent / "fixtures" / "odczyt" / "sprawa_przykladowa.json").read_text("utf-8"))


def _sprawa():
    s = Sprawa(id="sp")
    s.dodaj_osobe(Rola.MATKA, zalogowana=True)
    return s


def _pusty_pdf(n: int) -> bytes:
    w = PdfWriter()
    for _ in range(n):
        w.add_blank_page(width=595, height=842)
    b = io.BytesIO()
    w.write(b)
    return b.getvalue()


def falszywe_zapytaj(wywolane: list[str]):
    """Zamiast Claude: odpowiedzi z fikstury według etapu."""
    def zapytaj(pdf_bytes, polecenie, schemat, etap):
        wywolane.append(etap)
        dane = FIKSTURA["klasyfikacja"] if etap == "klasyfikacja" else FIKSTURA["odczyt"][etap.split(":", 1)[1]]
        return {"dane": dane, "info": {"etap": etap, "model": "test", "czas_s": 0, "tokeny_wejscie": 0,
                                       "tokeny_wyjscie": 0}}
    return zapytaj


@pytest.fixture(autouse=True)
def bez_cache(monkeypatch):
    monkeypatch.setattr(config, "CACHE_ODCZYTU", False)


@pytest.fixture
def po_odczycie():
    s, wywolane = _sprawa(), []
    wynik = pipeline.przetworz_plik(s, "sprawa.pdf", _pusty_pdf(FIKSTURA["liczba_stron"]),
                                    zapytaj=falszywe_zapytaj(wywolane))
    return s, wynik, wywolane


def test_jedno_wywolanie_klasyfikacji_i_jedno_na_dokument_z_polami(po_odczycie):
    _, wynik, wywolane = po_odczycie
    assert wywolane == ["klasyfikacja", "odczyt:ZAS-53", "odczyt:pismo_ZUS"] + ["odczyt:Z-3"] * 4 + \
        ["odczyt:zrzut_systemu_ZUS", "odczyt:decyzja_ZUS"]
    assert [d.typ for d in wynik.dokumenty] == ["ZAS-53", "pismo_ZUS", "Z-3", "Z-3", "Z-3", "Z-3",
                                                "zrzut_systemu_ZUS", "decyzja_ZUS"]


def test_wystawca_wg_typu_i_strona_z_oryginalnego_pliku(po_odczycie):
    s, wynik, _ = po_odczycie
    matka = s.osoby[0]
    z3 = wynik.dokumenty[2]
    etat = next(w for w in matka.pola["etat"] if w.dokument_id == z3.id)
    assert etat.wystawca == Wystawca.PRACODAWCA and etat.kanal == Kanal.UPLOAD
    assert etat.wartosc == "1.00"                       # jak w źródłach ZUS
    assert etat.strona == 4 and etat.zrodlo_opis == "Z-3, str. 4"   # strona 1 wycinka = strona 4 pliku
    miesiace = next(w for w in matka.pola["miesiace"] if w.dokument_id == z3.id)
    assert miesiace.strona == 6 and miesiace.wartosc[1]["skladniki_zmienne"] == "250.50"
    okresy = matka.aktywna("okresy_ubezpieczenia")
    assert okresy.wystawca == Wystawca.ZUS and okresy.zrodlo_opis == "Zrzut z systemu ZUS, str. 21"
    assert matka.aktywna("ezla").wystawca == Wystawca.UZYTKOWNIK   # ZAS-53 to wniosek ubezpieczonej


def test_kod_b_niewidoczny_zostaje_pusty(po_odczycie):
    s, _, _ = po_odczycie
    assert s.osoby[0].wartosc("ezla") == [{"od": "2026-03-02", "do": "2026-03-31", "kod": None}]


def test_pole_na_tytul_z_domyslnym_tytulem_dokumentu_i_niska_pewnosc(po_odczycie):
    s, wynik, _ = po_odczycie
    w = s.osoby[0].aktywna("platnik_ponad_20")
    assert w.wartosc == {"umowa_o_prace": "do_20"}      # Z-3 dotyczy umowy o pracę
    assert wynik.dokumenty[2].do_sprawdzenia == 1 and wynik.dokumenty[2].liczba_pol == 5


def test_pismo_zus_bez_pol_tylko_informacja(po_odczycie):
    s, wynik, _ = po_odczycie
    pismo = wynik.dokumenty[1]
    assert pismo.rola == "pismo_zus" and pismo.informacja == ["zaświadczenie płatnika składek Z-3"]
    assert pismo.liczba_pol == 0 and pismo.osoba_id is None
    assert not any(w.dokument_id == pismo.id for o in s.osoby for lista in o.pola.values() for w in lista)


def test_decyzja_zus_tylko_w_oczekiwanym_wyniku(po_odczycie):
    s, wynik, _ = po_odczycie
    decyzja = wynik.dokumenty[-1]
    assert s.oczekiwany_wynik == "Wypłacono zasiłek chorobowy za okres zwolnienia."
    assert decyzja.rola == "decyzja_zus" and decyzja.liczba_pol == 0
    assert not any(w.dokument_id == decyzja.id for o in s.osoby for lista in o.pola.values() for w in lista)


def test_cztery_z3_to_cztery_zrodla_jednego_pola(po_odczycie):
    s, _, _ = po_odczycie
    assert len(s.osoby[0].pola["etat"]) == 4 and not merge.konflikt(s.osoby[0], "etat")


def test_usuniecie_dokumentu_usuwa_jego_wartosci(po_odczycie):
    s, wynik, _ = po_odczycie
    zrzut, decyzja = wynik.dokumenty[6], wynik.dokumenty[7]
    assert mapowanie.usun_dokument(s, zrzut.id)
    assert "okresy_ubezpieczenia" not in s.osoby[0].pola and zrzut not in s.dokumenty
    assert mapowanie.usun_dokument(s, decyzja.id) and s.oczekiwany_wynik is None
    assert not mapowanie.usun_dokument(s, "d999")


def test_pole_dziecka_trafia_do_dziecka_a_plan_jest_pomijany():
    s = _sprawa()
    frag = Fragment(typ="ZAM", strony=[3, 4], osoby=["matka"])
    mapowanie.zapisz_dokument(s, "x.pdf", frag, {
        "za_zyciem": [{"wartosc": True, "osoba": "dziecko", "strona": 2, "pewnosc": 0.8}],
        "data_urodzenia": [{"wartosc": "2026-07-01", "osoba": "dziecko", "strona": 1, "pewnosc": 0.9},
                           {"wartosc": "1994-01-01", "osoba": "matka", "strona": 1, "pewnosc": 0.9}],
        "data_porodu": [{"wartosc": "nieczytelne", "osoba": "matka", "strona": 1, "pewnosc": 0.3}],
    })
    matka, dziecko = s.osoby
    assert dziecko.rola == Rola.DZIECKO and dziecko.aktywna("za_zyciem").zrodlo_opis == "ZAM, str. 4"
    assert dziecko.wartosc("data_urodzenia") == "2026-07-01" and matka.wartosc("data_urodzenia") == "1994-01-01"
    assert "data_porodu" not in matka.pola             # nieprawidłowa data – odrzucona


def test_dwa_dokumenty_rozne_wartosci_to_konflikt():
    s = _sprawa()
    mapowanie.zapisz_dokument(s, "x.pdf", Fragment(typ="ZAM", strony=[1]),
                              {"data_porodu": [{"wartosc": "2026-12-20", "osoba": None, "strona": 1, "pewnosc": 0.9}]})
    mapowanie.zapisz_dokument(s, "x.pdf", Fragment(typ="akt_urodzenia", strony=[2]),
                              {"data_porodu": [{"wartosc": "2026-12-22", "osoba": None, "strona": 1, "pewnosc": 0.9}]})
    matka = s.osoby[0]
    assert matka.wartosc("data_porodu") == "2026-12-22" and merge.konflikt(matka, "data_porodu")  # urząd > wniosek


def test_schematy_scisle_dla_structured_outputs():
    from app.extraction.schema import TYPY, schemat_klasyfikacji, schemat_odczytu

    def sprawdz(s):
        if isinstance(s, dict):
            if s.get("type") == "object":
                assert s["additionalProperties"] is False and set(s["required"]) == set(s["properties"])
            for v in s.values():
                sprawdz(v)
        elif isinstance(s, list):
            for v in s:
                sprawdz(v)

    sprawdz(schemat_klasyfikacji())
    for typ in TYPY:
        sprawdz(schemat_odczytu(typ))
    z3 = schemat_odczytu("Z-3")["properties"]
    assert {"etat", "miesiace", "zatrudnienie_od", "platnik_ponad_20"} <= set(z3)
    assert "ezla" in schemat_odczytu("ZAS-53")["properties"]
    assert schemat_odczytu("inne") is None
