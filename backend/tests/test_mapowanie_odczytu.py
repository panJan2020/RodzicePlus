"""Odczyt skanu → WartoscPola: wystawca według typu dokumentu, osoba właściwa dla pola (bez wywołania Claude)."""
from app.domain.model import Kanal, Rola, Sprawa, Wystawca
from app.extraction import mapowanie


def _sprawa():
    s = Sprawa(id="sp")
    s.dodaj_osobe(Rola.MATKA)
    s.dodaj_osobe(Rola.DZIECKO)
    return s


def test_wystawca_wedlug_typu_dokumentu_i_oczekiwany_wynik_osobno():
    s = _sprawa()
    mapowanie.zapisz_odczyt(s, {
        "oczekiwany_wynik": "W sprawie przyznano zasiłek chorobowy.",
        "pola": [{"pole": "etat", "wartosc": "1.00", "dokument": "Z-3", "strona": 5, "pewnosc": 0.9},
                 {"pole": "za_zyciem", "wartosc": True, "dokument": "ZAM", "strona": 2, "pewnosc": 0.8}],
    }, "sprawa.pdf")
    matka, dziecko = s.osoby
    etat = matka.aktywna("etat")
    assert etat.wystawca == Wystawca.PRACODAWCA and etat.kanal == Kanal.UPLOAD and etat.zrodlo_opis == "Z-3, str. 5"
    assert dziecko.aktywna("za_zyciem").wystawca == Wystawca.UZYTKOWNIK  # pole dziecka trafia do dziecka
    assert s.oczekiwany_wynik.startswith("W sprawie") and "oczekiwany_wynik" not in matka.pola


def test_dwa_dokumenty_rozne_wartosci_to_konflikt():
    from app import merge
    s = _sprawa()
    mapowanie.zapisz_odczyt(s, {"pola": [
        {"pole": "pdp", "wartosc": "2026-12-20", "dokument": "ZAM", "strona": 1, "pewnosc": 0.9},
        {"pole": "pdp", "wartosc": "2026-12-30", "dokument": "zaswiadczenie_lekarskie", "strona": 3, "pewnosc": 0.9},
    ]}, "sprawa.pdf")
    matka = s.osoby[0]
    assert matka.wartosc("pdp") == "2026-12-30" and merge.konflikt(matka, "pdp")  # lekarz > wniosek użytkownika


def test_plan_z_dokumentu_pomijany():
    s = _sprawa()
    mapowanie.zapisz_odczyt(s, {"pola": [
        {"pole": "drugi_rodzic_aktywny", "wartosc": "tak", "dokument": "ZAM", "strona": 1, "pewnosc": 0.9}]}, "x.pdf")
    assert "drugi_rodzic_aktywny" not in s.osoby[0].pola


def test_miesiace_z_z3_w_ksztalcie_pola_o4_art38():
    s = _sprawa()
    mapowanie.zapisz_odczyt(s, {"pola": [], "wynagrodzenia_miesieczne": [
        {"miesiac": "2026-05", "skladniki_stale": 6000, "skladniki_zmienne": 512.5, "dni_przepracowane": 20,
         "dni_obowiazujace": 20, "strona": 3}]}, "x.pdf")
    w = s.osoby[0].aktywna("miesiace")
    assert w.wystawca == Wystawca.PRACODAWCA
    assert w.wartosc == [{"miesiac": "2026-05", "skladniki_stale": "6000.00", "skladniki_zmienne": "512.50",
                          "dni_przepracowane": 20, "dni_obowiazujace": 20, "stale_pelna_kwota": None}]
