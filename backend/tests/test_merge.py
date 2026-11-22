"""merge/: hierarchia wiarygodności, konflikty, ręczny wybór aktywnej wartości (docs/architektura.md, rozdz. 6)."""
from datetime import datetime, timedelta, timezone

import pytest

from app import merge
from app.domain.model import Kanal, Rola, Sprawa, WartoscPola, Wystawca

PROG = 0.6
T0 = datetime(2026, 11, 22, tzinfo=timezone.utc)


def _sprawa():
    s = Sprawa(id="sp1")
    return s, s.dodaj_osobe(Rola.MATKA, "Anna")


def _w(wartosc, wystawca=Wystawca.UZYTKOWNIK, kanal=Kanal.KREATOR, pewnosc=1.0, dokument_id=None, minuty=0):
    return WartoscPola(wartosc=wartosc, wystawca=wystawca, kanal=kanal, zrodlo_opis="test", pewnosc=pewnosc,
                       dokument_id=dokument_id, utworzono=T0 + timedelta(minutes=minuty))


def _uzytkownik(v, **kw):
    return _w(v, **kw)


def _zus(v, **kw):
    return _w(v, Wystawca.ZUS, Kanal.ZUS_KONTO, **kw)


def _z3(v, pewnosc=0.9, dok="d1", **kw):
    return _w(v, Wystawca.PRACODAWCA, Kanal.UPLOAD, pewnosc=pewnosc, dokument_id=dok, **kw)


# ---------- hierarchia ----------

def test_zus_wygrywa_z_uzytkownikiem_niezaleznie_od_kolejnosci():
    s, o = _sprawa()
    merge.dodaj(s, o, "etat", _zus("1.00"), prog=PROG)
    merge.dodaj(s, o, "etat", _uzytkownik("0.50", minuty=5), prog=PROG)
    assert o.wartosc("etat") == "1.00"
    assert merge.wybor_aktywnej(o, "etat") == "automatyczny"


def test_dokument_pracodawcy_wygrywa_z_uzytkownikiem():
    s, o = _sprawa()
    merge.dodaj(s, o, "etat", _uzytkownik("0.50"), prog=PROG)
    merge.dodaj(s, o, "etat", _z3("0.75"), prog=PROG)
    assert o.wartosc("etat") == "0.75"


def test_niepewny_odczyt_ai_ponizej_dokumentu_ale_powyzej_uzytkownika():
    s, o = _sprawa()
    merge.dodaj(s, o, "etat", _uzytkownik("0.50"), prog=PROG)
    merge.dodaj(s, o, "etat", _z3("0.25", pewnosc=0.4, dok="d1"), prog=PROG)
    assert o.wartosc("etat") == "0.25"  # niepewny AI > użytkownik
    merge.dodaj(s, o, "etat", _w("1.00", Wystawca.LEKARZ, Kanal.UPLOAD, pewnosc=0.7, dokument_id="d2"), prog=PROG)
    assert o.wartosc("etat") == "1.00"  # pewny dokument > niepewny AI


def test_pewny_odczyt_ai_ma_range_wystawcy():
    s, o = _sprawa()
    merge.dodaj(s, o, "tytuly", _z3(["umowa_o_prace"], pewnosc=0.95), prog=PROG)
    merge.dodaj(s, o, "tytuly", _w(["zlecenie"], Wystawca.SAD, Kanal.UPLOAD, pewnosc=0.65, dokument_id="d9"), prog=PROG)
    assert o.wartosc("tytuly") == ["zlecenie"]  # sąd (ranga 4) > pracodawca (ranga 3)


def test_remis_wyzsza_pewnosc_potem_nowsza():
    s, o = _sprawa()
    merge.dodaj(s, o, "pdp", _z3("2026-12-20", pewnosc=0.8, dok="d1"), prog=PROG)
    merge.dodaj(s, o, "pdp", _z3("2026-12-30", pewnosc=0.9, dok="d2"), prog=PROG)
    assert o.wartosc("pdp") == "2026-12-30"
    merge.dodaj(s, o, "pdp", _z3("2027-01-02", pewnosc=0.9, dok="d3", minuty=1), prog=PROG)
    assert o.wartosc("pdp") == "2027-01-02"


def test_wniosek_zam_z_uploadu_wygrywa_z_kreatorem():
    """Ten sam wystawca `uzytkownik`: wartość z dokumentu, który trafił do ZUS, ma pierwszeństwo."""
    s, o = _sprawa()
    zam = _w("2026-12-01", Wystawca.UZYTKOWNIK, Kanal.UPLOAD, pewnosc=0.9, dokument_id="d1")
    merge.dodaj(s, o, "wniosek_81_5_data", zam, prog=PROG)
    merge.dodaj(s, o, "wniosek_81_5_data", _uzytkownik("2026-12-15", minuty=5), prog=PROG)
    assert o.wartosc("wniosek_81_5_data") == "2026-12-01"


# ---------- dodawanie, aktualizacja, usuwanie ----------

def test_wartosci_nie_przepadaja_i_maja_id():
    s, o = _sprawa()
    a = merge.dodaj(s, o, "etat", _uzytkownik("0.50"), prog=PROG)
    b = merge.dodaj(s, o, "etat", _zus("1.00"), prog=PROG)
    assert [w.id for w in o.pola["etat"]] == [a.id, b.id] == ["w1", "w2"]
    assert [w.aktywna for w in o.pola["etat"]] == [False, True]


def test_to_samo_zrodlo_aktualizuje_swoja_wartosc():
    s, o = _sprawa()
    merge.dodaj(s, o, "etat", _uzytkownik("0.50"), prog=PROG)
    merge.dodaj(s, o, "etat", _uzytkownik("0.75"), prog=PROG)
    assert len(o.pola["etat"]) == 1 and o.wartosc("etat") == "0.75" and o.pola["etat"][0].id == "w1"


def test_usuniecie_wartosci_uzytkownika_zostawia_inne_zrodla():
    s, o = _sprawa()
    merge.dodaj(s, o, "etat", _uzytkownik("0.50"), prog=PROG)
    merge.dodaj(s, o, "etat", _zus("1.00"), prog=PROG)
    assert merge.usun(o, "etat", Kanal.KREATOR, prog=PROG)
    assert [w.wartosc for w in o.pola["etat"]] == ["1.00"] and o.wartosc("etat") == "1.00"
    merge.usun(o, "etat", Kanal.ZUS_KONTO, prog=PROG)
    assert "etat" not in o.pola and o.wartosc("etat") is None


def test_plan_tylko_z_kreatora():
    s, o = _sprawa()
    with pytest.raises(merge.NiedozwolonaWartosc):
        merge.dodaj(s, o, "plan_ustania", _z3({"kiedy": "2026-12-01"}), rodzaj="plan", prog=PROG)
    merge.dodaj(s, o, "plan_ustania", _uzytkownik({"kiedy": "2026-12-01"}), rodzaj="plan", prog=PROG)
    assert o.wartosc("plan_ustania") == {"kiedy": "2026-12-01"}


def test_wybor_scenariusza_nie_trafia_do_osoby():
    s, o = _sprawa()
    with pytest.raises(merge.NiedozwolonaWartosc):
        merge.dodaj(s, o, "wariant", _uzytkownik("jednolity_81_5"), rodzaj="wybor", prog=PROG)
    assert "wariant" not in o.pola


# ---------- konflikty ----------

def test_konflikt_gdy_rozne_wartosci():
    s, o = _sprawa()
    merge.dodaj(s, o, "etat", _zus("1.00"), prog=PROG)
    assert not merge.konflikt(o, "etat")
    merge.dodaj(s, o, "etat", _uzytkownik("0.50"), prog=PROG)
    assert merge.konflikt(o, "etat") and merge.konflikty(s) == [("o1", "etat")]


def test_te_same_wartosci_z_dwoch_zrodel_to_nie_konflikt():
    s, o = _sprawa()
    merge.dodaj(s, o, "tytuly", _zus(["umowa_o_prace"]), prog=PROG)
    merge.dodaj(s, o, "tytuly", _z3(["umowa_o_prace"]), prog=PROG)
    assert not merge.konflikt(o, "tytuly")


# ---------- ręczny wybór ----------

def test_reczny_wybor_i_powrot_do_automatycznego():
    s, o = _sprawa()
    u = merge.dodaj(s, o, "etat", _uzytkownik("0.50"), prog=PROG)
    merge.dodaj(s, o, "etat", _zus("1.00"), prog=PROG)
    merge.ustaw_recznie(o, "etat", u.id, prog=PROG)
    assert o.wartosc("etat") == "0.50" and merge.wybor_aktywnej(o, "etat") == "uzytkownik"
    merge.dodaj(s, o, "etat", _z3("0.75"), prog=PROG)  # nowe źródło nie zmienia ręcznego wyboru
    assert o.wartosc("etat") == "0.50"
    merge.ustaw_recznie(o, "etat", None, prog=PROG)
    assert o.wartosc("etat") == "1.00" and merge.wybor_aktywnej(o, "etat") == "automatyczny"


def test_reczny_wybor_nieznanej_wartosci():
    s, o = _sprawa()
    merge.dodaj(s, o, "etat", _zus("1.00"), prog=PROG)
    with pytest.raises(KeyError):
        merge.ustaw_recznie(o, "etat", "w99", prog=PROG)


def test_usuniecie_recznie_wybranej_wartosci_przywraca_automat():
    s, o = _sprawa()
    u = merge.dodaj(s, o, "etat", _uzytkownik("0.50"), prog=PROG)
    merge.dodaj(s, o, "etat", _zus("1.00"), prog=PROG)
    merge.ustaw_recznie(o, "etat", u.id, prog=PROG)
    merge.usun(o, "etat", Kanal.KREATOR, prog=PROG)
    assert o.wartosc("etat") == "1.00" and merge.wybor_aktywnej(o, "etat") == "automatyczny"


def test_aktywne_wartosci_i_migawka():
    s, o = _sprawa()
    merge.dodaj(s, o, "etat", _zus("1.00"), prog=PROG)
    merge.dodaj(s, o, "pdp", _uzytkownik("2026-12-20"), prog=PROG)
    assert merge.aktywne_wartosci(o) == {"etat": "1.00", "pdp": "2026-12-20"}
    przed = merge.migawka(s)
    merge.dodaj(s, o, "pdp", _z3("2026-12-30"), prog=PROG)
    po = merge.migawka(s)
    assert {k for k in po if po[k] != przed.get(k)} == {("o1", "pdp")}


def test_prog_pewnosci_z_parametrow():
    from app.merge.scalanie import prog_pewnosci
    assert prog_pewnosci() == 0.6
