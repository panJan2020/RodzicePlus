"""Reguła zasiłku chorobowego w ciąży: 4 statusy, wyczekiwanie, 33 dni wynagrodzenia, 270 dni, stawka (kod B), kto wypłaca.

Dane są FIKCYJNE (rok 2026), ułożone jak sprawa testowa Anny: umowa o pracę od 01.10.2025, płatnik do 20 osób,
wynagrodzenie chorobowe od pracodawcy 18.02–22.03 (33 dni), zwolnienia do 27.05, zasiłek od 23.03.
„Dzisiaj” jest wstrzykiwane (`Kontekst.dzis`), więc testy są deterministyczne.
"""
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.domain.model import Kanal, WartoscPola, Wystawca
from app.domain.results import Status
from app.extraction import mapowanie
from app.extraction.podzial import Fragment
from app.main import app
from app.params.store import get_params
from app.rules.wspolne import Kontekst
from app.rules.zasilek_chorobowy_ciaza import zasilek_chorobowy_ciaza
from app.storage import memory

P = get_params(date(2026, 3, 1))
DZIS = date(2026, 11, 22)
c = TestClient(app)

UOP_OD = "2025-10-01"
OKRES_UOP = {"tytul": "umowa_o_prace", "platnik": "", "od": UOP_OD, "do": None, "chorobowe": None}  # jak w zrzucie ZUS
ANNA = {
    "sytuacja": ["ciaza"], "tytuly": ["umowa_o_prace"], "okresy_ubezpieczenia": [OKRES_UOP],
    "zatrudnienie_od": UOP_OD, "etat": "0.25", "platnik_ponad_20": {"umowa_o_prace": "do_20"},
    "data_urodzenia": "1994-05-12",
    "ezla": [{"od": "2026-03-08", "do": "2026-05-27", "kod": None}],
    "wynagrodzenie_chorobowe_okres": [{"od": "2026-02-18", "do": "2026-03-22", "kod": None}],
}


def _licz(fakty, dzis=DZIS, pochodzenie=None):
    k = Kontekst(fakty=fakty, pochodzenie=pochodzenie or {}, dzis=dzis)
    wyniki = zasilek_chorobowy_ciaza(k, P)
    assert len(wyniki) == 1 and wyniki[0].swiadczenie == "zasilek_chorobowy_ciaza"
    return wyniki[0]


def _dni(od: date, ile: int, kod=None):
    """Zwolnienie na `ile` dni od daty `od` (włącznie)."""
    return [{"od": od.isoformat(), "do": (od + timedelta(days=ile - 1)).isoformat(), "kod": kod}]


def _bez_wynagrodzenia(**zmiany):
    f = {**ANNA, **zmiany}
    f.pop("wynagrodzenie_chorobowe_okres")
    return f


# ---------- Anna: przypadek z zestawu ZUS ----------

def test_anna_przysluguje_od_23_03_zus_art4_art92():
    w = _licz(ANNA)
    assert w.status == Status.PRZYSLUGUJE
    assert (w.okres.od, w.okres.do, w.okres.dni) == (date(2026, 3, 23), date(2026, 5, 27), 66)
    assert (w.okres_wynagrodzenia.od, w.okres_wynagrodzenia.do, w.okres_wynagrodzenia.dni) == \
        (date(2026, 2, 18), date(2026, 3, 22), 33)
    assert w.kto_wyplaca == "zus" and "ZUS" in w.podsumowanie and w.kwota is None
    assert "Z-3" in " ".join(w.co_zrobic)                       # ZUS potrzebuje Z-3 od pracodawcy
    assert w.podsumowanie.startswith("Przysługuje Ci zasiłek chorobowy od 23.03.2026 do 27.05.2026 (66 dni)")


def test_anna_bez_kodu_stawka_orientacyjna_i_pytanie_o_kod_art11():
    w = _licz(ANNA)
    assert w.stawka == "0.80" and w.orientacyjny is True and "ezla_kod_b" in w.brakujace
    assert any("kod" in u for u in w.uwagi)


def test_status_nie_zalezy_od_kodu_b_art11():
    bez = _licz(ANNA)
    z_b = _licz({**ANNA, "ezla": _dni(date(2026, 3, 8), 81, "B")})
    z_deklaracja = _licz({**ANNA, "ezla_kod_b": True})
    assert bez.status == z_b.status == z_deklaracja.status == Status.PRZYSLUGUJE
    assert bez.okres == z_b.okres == z_deklaracja.okres
    assert z_b.stawka == z_deklaracja.stawka == "1.00" and "ezla_kod_b" not in z_b.brakujace
    assert _licz({**ANNA, "ezla_kod_b": False}).stawka == "0.80"
    assert "ezla_kod_b" not in _licz({**ANNA, "ezla_kod_b": False}).brakujace


def test_inny_kod_literowy_to_80_proc_bez_pytania_art11():
    w = _licz({**ANNA, "ezla": _dni(date(2026, 3, 8), 81, "A")})
    assert w.stawka == "0.80" and "ezla_kod_b" not in w.brakujace


def test_zwolnienie_czesciowo_z_kodem_b_ma_stawki_osobno_art11():
    ezla = _dni(date(2026, 3, 8), 30, "B") + _dni(date(2026, 4, 7), 51)       # 08.03–06.04 B, 07.04–27.05 bez kodu
    w = _licz({**ANNA, "ezla": ezla, "ezla_kod_b": False})
    assert w.stawka is None and any("osobno" in u for u in w.uwagi)


# ---------- brak danych ----------

def test_brak_zwolnienia_brak_danych_art4():
    f = {k: v for k, v in ANNA.items() if k not in ("ezla", "wynagrodzenie_chorobowe_okres")}
    w = _licz(f)
    assert w.status == Status.BRAK_DANYCH and w.brakujace[0] == "ezla" and w.okres is None


def test_brak_tytulow_brak_danych_art4():
    w = _licz({k: v for k, v in ANNA.items() if k not in ("tytuly", "okresy_ubezpieczenia")})
    assert w.status == Status.BRAK_DANYCH and "tytuly" in w.brakujace


def test_zlecenie_bez_informacji_o_chorobowym_brak_danych_art4():
    f = {**ANNA, "tytuly": ["zlecenie"], "okresy_ubezpieczenia": [{**OKRES_UOP, "tytul": "zlecenie"}]}
    assert _licz(f).brakujace == ["chorobowe_dobrowolne"]


# ---------- tytuł z chorobowym ----------

def test_umowa_o_prace_z_chorobowe_null_ma_ubezpieczenie_art4():
    assert _licz(ANNA).status == Status.PRZYSLUGUJE


def test_zlecenie_bez_dobrowolnego_chorobowego_nie_przysluguje_art4():
    f = {**ANNA, "tytuly": ["zlecenie"], "chorobowe": {"zlecenie": False},
         "okresy_ubezpieczenia": [{**OKRES_UOP, "tytul": "zlecenie"}]}
    w = _licz(f)
    assert w.status == Status.NIE_PRZYSLUGUJE and w.powody and w.okres is None


def test_niezdolnosc_po_ustaniu_tytulu_nie_przysluguje_z_ostrzezeniem_art7():
    f = {**ANNA, "okresy_ubezpieczenia": [{**OKRES_UOP, "do": "2026-02-10", "chorobowe": True}]}
    w = _licz(f)
    assert w.status == Status.NIE_PRZYSLUGUJE and "10.02.2026" in " ".join(w.uzasadnienie)
    assert any("art. 7" in u for u in w.uwagi) and any("14 dni" in x for x in w.co_zrobic)


def test_niezdolnosc_po_ustaniu_wskazana_przez_uzytkownika_warunkowo_z_ostrzezeniem_art7():
    f = {**ANNA, "po_ustaniu": True, "okresy_ubezpieczenia": [{**OKRES_UOP, "do": "2026-02-10", "chorobowe": True}]}
    w = _licz(f)
    assert w.status == Status.WARUNKOWO and w.kto_wyplaca == "zus" and any("art. 7" in u for u in w.uwagi)


# ---------- okres wyczekiwania: 30 dni (obowiązkowe), 90 (dobrowolne) – art. 4 ----------

@pytest.mark.parametrize("dni_po_poczatku, status", [(29, Status.NIE_PRZYSLUGUJE), (30, Status.PRZYSLUGUJE)])
def test_wyczekiwanie_30_dni_obowiazkowe_granica_art4(dni_po_poczatku, status):
    start = date(2026, 1, 1) + timedelta(days=dni_po_poczatku)
    f = {**_bez_wynagrodzenia(), "chorobowe_od": "2026-01-01", "zatrudnienie_od": "2026-01-01",
         "okresy_ubezpieczenia": [{**OKRES_UOP, "od": "2026-01-01"}], "ezla": _dni(start, 60)}
    w = _licz(f)
    assert w.status == status
    if status == Status.NIE_PRZYSLUGUJE:
        assert "01.01.2026" in w.uzasadnienie[0] and "31.01.2026" in w.uzasadnienie[0]   # najwcześniej 31.01


@pytest.mark.parametrize("dni_po_poczatku, status", [(89, Status.NIE_PRZYSLUGUJE), (90, Status.PRZYSLUGUJE)])
def test_wyczekiwanie_90_dni_dobrowolne_granica_art4(dni_po_poczatku, status):
    start = date(2026, 1, 1) + timedelta(days=dni_po_poczatku)
    f = {"sytuacja": ["ciaza"], "tytuly": ["dzialalnosc"], "chorobowe": {"dzialalnosc": True},
         "chorobowe_od": "2026-01-01", "okresy_ubezpieczenia": [{**OKRES_UOP, "tytul": "dzialalnosc", "od": "2026-01-01"}],
         "ezla": _dni(start, 20)}
    assert _licz(f).status == status


def test_wyczekiwanie_liczone_od_zatrudnienia_gdy_brak_chorobowe_od_art4():
    f = {"sytuacja": ["ciaza"], "tytuly": ["umowa_o_prace"], "umowa_rodzaj": "nieokreslony",
         "zatrudnienie_od": "2026-01-01", "chorobowe_od": "2026-01-01", "platnik_ponad_20": {"umowa_o_prace": "ponad_20"},
         "ezla": _dni(date(2026, 1, 20), 20)}
    assert _licz(f).status == Status.NIE_PRZYSLUGUJE


# ---------- 33 dni wynagrodzenia płaci pracodawca – art. 92 KP ----------

def test_33_dni_granica_zasilek_od_34_dnia_art92():
    start = date(2026, 3, 8)
    w34 = _licz(_bez_wynagrodzenia(ezla=_dni(start, 34)))
    assert (w34.okres.od, w34.okres.do, w34.okres.dni) == (start + timedelta(days=33),) * 2 + (1,)
    assert w34.orientacyjny is True and any("33 dni" in u for u in w34.uwagi)     # bez okresu z Z-3 zakładamy 33
    w33 = _licz(_bez_wynagrodzenia(ezla=_dni(start, 33)))
    assert w33.status == Status.WARUNKOWO and w33.okres is None and "pracodawca" in w33.podsumowanie


def test_okres_wynagrodzenia_z_z3_wyznacza_koniec_platnosci_pracodawcy_art92():
    f = {**ANNA, "wynagrodzenie_chorobowe_okres": [{"od": "2026-02-18", "do": "2026-03-15", "kod": None}]}  # 26 dni
    w = _licz(f)
    assert w.okres.od == date(2026, 3, 16) and w.okres_wynagrodzenia.dni == 26
    assert any("26 dni" in u and "limit" in u for u in w.uwagi)                   # kontrola względem limitu 33


def test_14_dni_wynagrodzenia_po_50_roku_zycia_art92():
    start = date(2026, 3, 8)
    for urodzony, ile in (("1975-01-01", 14), ("1976-12-31", 33)):             # 2026-1975=51 > 50; 2026-1976=50
        w = _licz(_bez_wynagrodzenia(ezla=_dni(start, 60), data_urodzenia=urodzony))
        assert w.okres.od == start + timedelta(days=ile), urodzony


# ---------- 270 dni w ciąży – art. 8 ----------

def test_270_dni_granica_art8():
    start = date(2026, 1, 1)
    f = _bez_wynagrodzenia(ezla=_dni(start, 270), tytuly=["dzialalnosc"], chorobowe={"dzialalnosc": True},
                           okresy_ubezpieczenia=[{**OKRES_UOP, "tytul": "dzialalnosc", "od": "2025-01-01"}],
                           chorobowe_od="2025-01-01")
    w270 = _licz(f, dzis=date(2026, 12, 31))
    assert w270.okres.dni == 270 and w270.okres.do == start + timedelta(days=269)
    assert not any("270" in u for u in w270.uzasadnienie)
    w271 = _licz({**f, "ezla": _dni(start, 271)}, dzis=date(2026, 12, 31))
    assert w271.okres.dni == 270 and w271.okres.do == start + timedelta(days=269)
    assert any("270 dni" in u for u in w271.uzasadnienie)


def test_270_dni_liczy_dni_wynagrodzenia_art8():
    start = date(2026, 3, 8)
    w = _licz(_bez_wynagrodzenia(ezla=_dni(start, 300)), dzis=date(2026, 12, 31))
    assert w.okres.od == start + timedelta(days=33) and w.okres.dni == 270 - 33
    assert w.okres.do == start + timedelta(days=269)


# ---------- kto wypłaca – art. 61 ----------

def test_ponad_20_ubezpieczonych_wyplaca_pracodawca_art61():
    w = _licz({**ANNA, "platnik_ponad_20": {"umowa_o_prace": "ponad_20"}})
    assert w.kto_wyplaca == "platnik" and "pracodawca" in w.podsumowanie and "Z-3" not in " ".join(w.co_zrobic)
    assert w.okres.od == date(2026, 3, 23)                           # okres zasiłku ten sam – zmienia się płatnik


def test_nie_wiadomo_ilu_ubezpieczonych_pytamy_nie_zgadujemy_art61():
    w = _licz({**ANNA, "platnik_ponad_20": {"umowa_o_prace": "nie_wiem"}})
    assert w.kto_wyplaca is None and "platnik_ponad_20" in w.brakujace and w.status == Status.PRZYSLUGUJE


def test_dzialalnosc_zawsze_zus_i_zasilek_od_pierwszego_dnia_art61():
    f = {"sytuacja": ["ciaza"], "tytuly": ["dzialalnosc"], "chorobowe": {"dzialalnosc": True},
         "chorobowe_od": "2025-01-01", "okresy_ubezpieczenia": [{**OKRES_UOP, "tytul": "dzialalnosc", "od": "2025-01-01"}],
         "ezla": _dni(date(2026, 3, 8), 20)}
    w = _licz(f)
    assert w.kto_wyplaca == "zus" and w.okres.od == date(2026, 3, 8) and w.okres_wynagrodzenia is None
    assert "ZAS-53" in w.gdzie_zlozyc


# ---------- „dzisiaj” wstrzykiwane, ostrzeżenia ----------

def test_zwolnienie_trwajace_po_dacie_odniesienia_warunkowo_art8():
    przed, po = date(2026, 5, 1), date(2026, 5, 28)
    assert _licz(ANNA, dzis=przed).status == Status.WARUNKOWO
    assert _licz(ANNA, dzis=przed).warunki and "01.05.2026" in _licz(ANNA, dzis=przed).warunki[0].opis
    assert _licz(ANNA, dzis=po).status == Status.PRZYSLUGUJE


def test_nakladanie_okresow_z_dokumentow_to_ostrzezenie_do_sprawdzenia():
    pochodzenie = {"ezla": WartoscPola(wartosc=ANNA["ezla"], wystawca=Wystawca.PRACODAWCA, kanal=Kanal.UPLOAD,
                                       zrodlo_opis="Z-3", uwagi=["Okresy z różnych dokumentów nakładają się: 08.05.2026."])}
    w = _licz(ANNA, pochodzenie=pochodzenie)
    assert w.status == Status.PRZYSLUGUJE and "08.05.2026" in " ".join(w.uwagi) and "ezla" in w.pola_do_potwierdzenia


def test_praca_na_zwolnieniu_ostrzezenie_art17():
    w = _licz({**ANNA, "praca_na_zwolnieniu": True})
    assert w.status == Status.PRZYSLUGUJE and "praca_na_zwolnieniu" in w.ryzyka and any("art. 17" in u for u in w.uwagi)


def test_przerwa_miedzy_zwolnieniami_ostrzezenie():
    ezla = _dni(date(2026, 3, 8), 20) + _dni(date(2026, 4, 10), 20)
    assert any("przerwy" in u for u in _licz({**ANNA, "ezla": ezla}).uwagi)


# ---------- od dokumentów do wyniku (upload → merge → reguła → API) ----------

def _wiersze(od, do, kod=None):
    return {"od": od, "do": do, "kod": kod, "strona": 2, "pewnosc": 0.9}


def test_od_dokumentow_do_wyniku_przez_merge_i_api_art4_art92():
    sid = c.post("/sprawy").json()["id"]
    s = memory.pobierz(sid)
    z3 = [("2026-03-08", "2026-04-01"), ("2026-04-02", "2026-04-03"), ("2026-04-04", "2026-05-08"),
          ("2026-05-08", "2026-05-27")]
    pierwszy = True
    for i, (od, do) in enumerate(z3):
        odczyt = {"ezla": [_wiersze(od, do)], "pola": [
            {"pole": "etat", "wartosc": "0.25", "strona": 1, "pewnosc": 0.9},
            {"pole": "zatrudnienie_od", "wartosc": UOP_OD, "strona": 1, "pewnosc": 0.9},
            {"pole": "platnik_ponad_20", "wartosc": "do_20", "strona": 1, "pewnosc": 0.9}]}
        if pierwszy:
            odczyt["wynagrodzenie_chorobowe_okres"] = [_wiersze("2026-02-18", "2026-03-22")]
            pierwszy = False
        mapowanie.zapisz_dokument(s, "anna.pdf", Fragment(typ="Z-3", strony=[4 * i + 1], osoby=["matka"]), odczyt)
    mapowanie.zapisz_dokument(s, "anna.pdf", Fragment(typ="ZAS-53", strony=[20], osoby=["matka"]),
                              {"ezla": [_wiersze("2026-02-18", "2026-05-27")]})
    mapowanie.zapisz_dokument(s, "anna.pdf", Fragment(typ="zrzut_systemu_ZUS", strony=[21], osoby=["matka"]), {
        "pola": [{"pole": "tytuly", "wartosc": "umowa_o_prace", "tytul": "umowa_o_prace", "strona": 1, "pewnosc": 0.9}],
        "okresy_ubezpieczenia": [{"kod_tytulu": "0110", "tytul": "umowa_o_prace", "platnik": None, "od": UOP_OD,
                                  "do": None, "chorobowe": None, "chorobowe_dobrowolne": None, "strona": 1,
                                  "pewnosc": 0.9}]})
    matka = s.osoby[0]
    scalona = matka.aktywna("ezla")
    assert scalona.wystawca == Wystawca.PRACODAWCA and scalona.czesci and len(matka.pola["ezla"]) == 4 + 1 + 1
    assert scalona.uwagi and "08.05.2026" in scalona.uwagi[0]       # nakładanie to ostrzeżenie, nie konflikt
    memory.zapisz(s)
    odp = c.post(f"/sprawy/{sid}/odpowiedzi", json=[{"pole": "sytuacja", "wartosc": ["ciaza"]},
                                                    {"pole": "data_urodzenia", "wartosc": "1994-05-12"}])
    assert odp.status_code == 200
    wynik = next(w for w in c.get(f"/sprawy/{sid}/swiadczenia").json() if w["swiadczenie"] == "zasilek_chorobowy_ciaza")
    assert wynik["status"] == "przysluguje" and wynik["kto_wyplaca"] == "zus" and wynik["kwota"] is None
    assert wynik["okres"] == {"od": "2026-03-23", "do": "2026-05-27", "tygodnie": None, "dni": 66}
    assert wynik["okres_wynagrodzenia"]["od"] == "2026-02-18" and wynik["stawka"] == "0.80"
    assert [b["pytanie_id"] for b in wynik["brakujace_pola"]] == ["D1a"]       # pytanie o kod B
    assert "D1" in [p["pytanie_id"] for p in wynik["pola_do_potwierdzenia"]]    # nakładanie okresów → do sprawdzenia
    assert wynik["wersja_parametrow"] == "2026-01-01"
