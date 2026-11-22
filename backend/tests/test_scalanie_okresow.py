"""Scalanie okresów (e-ZLA) z kilku dokumentów tego samego wystawcy w jedną wartość pola (merge/okresy.py).

Dane fikcyjne. Nakładanie okresów to ostrzeżenie (`uwagi`), nie konflikt; części zostają widoczne jako osobne
wartości z dokumentem i stroną.
"""
from datetime import date

from app import merge
from app.domain.model import Kanal, Rola, Sprawa, WartoscPola, Wystawca
from app.extraction import mapowanie
from app.extraction.podzial import Fragment
from app.merge import okresy

Z3 = [("2026-03-08", "2026-04-01"), ("2026-04-02", "2026-04-03"), ("2026-04-04", "2026-05-08"),
      ("2026-05-08", "2026-05-27")]


def _sprawa():
    s = Sprawa(id="sp")
    s.dodaj_osobe(Rola.MATKA, zalogowana=True)
    return s


def _wpis(od, do, kod=None):
    return {"ezla": [{"od": od, "do": do, "kod": kod, "strona": 2, "pewnosc": 0.9}]}


def _z3(s, i, od, do, kod=None):
    return mapowanie.zapisz_dokument(s, "x.pdf", Fragment(typ="Z-3", strony=[4 * i + 1, 4 * i + 2]), _wpis(od, do, kod))


def _wszystkie(s):
    for i, (od, do) in enumerate(Z3):
        _z3(s, i, od, do)


def test_cztery_z3_to_jedna_wartosc_scalona_z_czesciami():
    s = _sprawa()
    _wszystkie(s)
    matka = s.osoby[0]
    aktywna = matka.aktywna("ezla")
    assert aktywna.wartosc == [{"od": "2026-03-08", "do": "2026-05-27", "kod": None}]   # sąsiednie i nakładające się
    assert aktywna.wystawca == Wystawca.PRACODAWCA and len(aktywna.czesci) == 4
    czesci = [w for w in matka.pola["ezla"] if w.czesc_z == aktywna.id]
    assert len(czesci) == 4 and not any(w.aktywna for w in czesci)
    assert {w.dokument_id for w in czesci} == {d.id for d in s.dokumenty}      # części pamiętają dokument i stronę
    assert all(w.strona for w in czesci)
    assert "Z-3, str." in aktywna.zrodlo_opis


def test_nakladanie_to_ostrzezenie_a_nie_konflikt():
    s = _sprawa()
    _wszystkie(s)
    matka = s.osoby[0]
    assert matka.aktywna("ezla").uwagi == ["Okresy z różnych dokumentów nakładają się: 08.05.2026. Sprawdź daty zwolnień."]
    assert not merge.konflikt(matka, "ezla") and merge.konflikty(s) == []


def test_sasiadujace_okresy_bez_nakladania_bez_ostrzezenia():
    s = _sprawa()
    _z3(s, 0, "2026-03-08", "2026-04-01")
    _z3(s, 1, "2026-04-02", "2026-04-03")
    w = s.osoby[0].aktywna("ezla")
    assert w.wartosc == [{"od": "2026-03-08", "do": "2026-04-03", "kod": None}] and w.uwagi == []


def test_okresy_z_przerwa_zostaja_osobno():
    s = _sprawa()
    _z3(s, 0, "2026-03-08", "2026-03-10")
    _z3(s, 1, "2026-03-12", "2026-03-14")
    assert [(o["od"], o["do"]) for o in s.osoby[0].aktywna("ezla").wartosc] == \
        [("2026-03-08", "2026-03-10"), ("2026-03-12", "2026-03-14")]


def test_rozne_kody_nie_lacza_sie_art11():
    s = _sprawa()
    _z3(s, 0, "2026-03-08", "2026-03-31", "B")
    _z3(s, 1, "2026-04-01", "2026-04-30", None)
    assert s.osoby[0].aktywna("ezla").wartosc == [{"od": "2026-03-08", "do": "2026-03-31", "kod": "B"},
                                                  {"od": "2026-04-01", "do": "2026-04-30", "kod": None}]


def test_jeden_dokument_nie_tworzy_wartosci_scalonej():
    s = _sprawa()
    _z3(s, 0, "2026-03-08", "2026-04-01")
    w = s.osoby[0].pola["ezla"]
    assert len(w) == 1 and w[0].czesci == [] and w[0].aktywna


def test_scalamy_tylko_tego_samego_wystawcy_zas53_zostaje_osobna_wartoscia():
    s = _sprawa()
    _wszystkie(s)
    mapowanie.zapisz_dokument(s, "x.pdf", Fragment(typ="ZAS-53", strony=[20]), _wpis("2026-02-18", "2026-05-27"))
    matka = s.osoby[0]
    assert matka.aktywna("ezla").wystawca == Wystawca.PRACODAWCA            # pracodawca > użytkownik
    assert len([w for w in matka.pola["ezla"] if w.wystawca == Wystawca.UZYTKOWNIK]) == 1
    # Znana niedoskonałość UI (do etapu 5): różne wartości od różnych wystawców wyglądają jak konflikt,
    # choć ZAS-53 obejmuje całość, a Z-3 tylko część. Konflikt nie blokuje wyniku.
    assert merge.konflikt(matka, "ezla") is True


def test_usuniecie_dokumentu_przelicza_wartosc_scalona():
    s = _sprawa()
    _wszystkie(s)
    ostatni = s.dokumenty[-1]
    assert mapowanie.usun_dokument(s, ostatni.id)
    w = s.osoby[0].aktywna("ezla")
    assert w.wartosc == [{"od": "2026-03-08", "do": "2026-05-08", "kod": None}] and len(w.czesci) == 3
    assert w.uwagi == []                                                    # nakładanie było z usuniętym dokumentem
    for d in s.dokumenty[1:]:
        mapowanie.usun_dokument(s, d.id)
    pojedyncza = s.osoby[0].pola["ezla"]
    assert len(pojedyncza) == 1 and pojedyncza[0].aktywna and pojedyncza[0].czesci == []
    mapowanie.usun_dokument(s, s.dokumenty[0].id)
    assert "ezla" not in s.osoby[0].pola


def test_ponowny_odczyt_tego_samego_dokumentu_nie_dubluje_czesci():
    s = _sprawa()
    d = _z3(s, 0, "2026-03-08", "2026-04-01")
    _z3(s, 1, "2026-04-02", "2026-04-03")
    pola = s.osoby[0].pola["ezla"]
    stare_id = s.osoby[0].aktywna("ezla").id
    merge.dodaj(s, s.osoby[0], "ezla", WartoscPola(wartosc=[{"od": "2026-03-08", "do": "2026-04-05", "kod": None}],
                                                  wystawca=Wystawca.PRACODAWCA, kanal=Kanal.UPLOAD,
                                                  zrodlo_opis="Z-3, str. 2", dokument_id=d.id, strona=2), rodzaj="fakt")
    assert len(pola) == len(s.osoby[0].pola["ezla"]) and s.osoby[0].aktywna("ezla").id == stare_id
    assert s.osoby[0].aktywna("ezla").wartosc == [{"od": "2026-03-08", "do": "2026-04-05", "kod": None}]


def test_funkcje_pomocnicze_scal_odcinki_i_nakladania():
    d = date
    assert okresy.scal_odcinki([(d(2026, 1, 1), d(2026, 1, 5), None), (d(2026, 1, 6), d(2026, 1, 9), None),
                                (d(2026, 1, 20), d(2026, 1, 21), None)]) == \
        [(d(2026, 1, 1), d(2026, 1, 9), None), (d(2026, 1, 20), d(2026, 1, 21), None)]
    assert okresy.nakladania([[(d(2026, 1, 1), d(2026, 1, 10), None)], [(d(2026, 1, 8), d(2026, 1, 12), None)]]) == \
        ["Okresy z różnych dokumentów nakładają się: 08.01.2026–10.01.2026. Sprawdź daty zwolnień."]
