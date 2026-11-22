"""Reguła zasiłku chorobowego w ciąży: 4 statusy, wyczekiwanie, 33 dni wynagrodzenia, 270 dni, stawka (kod B), kto wypłaca.

Dane są FIKCYJNE (rok 2026), ułożone jak sprawa testowa Anny: umowa o pracę od 01.10.2025, płatnik do 20 osób,
wynagrodzenie chorobowe od pracodawcy 18.02–22.03 (33 dni), zwolnienia do 27.05, zasiłek od 23.03.
„Dzisiaj” jest wstrzykiwane (`Kontekst.dzis`), więc testy są deterministyczne.
"""
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

import pytest
from fastapi.testclient import TestClient

from app.domain.model import Kanal, WartoscPola, Wystawca
from app.domain.results import Status
from app.extraction import mapowanie
from app.formaty import kwota_tekst
from app.extraction.podzial import Fragment
from app.main import app
from app.params.store import get_params
from app.rules.wspolne import Kontekst
from app.rules.zasilek_chorobowy_ciaza import zasilek_chorobowy_ciaza
from app.storage import memory

P = get_params(date(2026, 3, 1))
DZIS = date(2026, 11, 22)
c = TestClient(app)

def _miesiac(m, stale):
    return {"miesiac": m, "skladniki_stale": stale, "skladniki_zmienne": "0.00", "dni_przepracowane": 20,
            "dni_obowiazujace": 20, "stale_pelna_kwota": None}


# Fikcyjne wynagrodzenia (etat 0,25): średnia 1325 zł → po odjęciu 13,71% powyżej najniższej podstawy 2026 × 0,25.
MIESIACE_WYSOKIE = [_miesiac("2025-10", "1300.00"), _miesiac("2025-11", "1300.00"), _miesiac("2025-12", "1300.00"),
                    _miesiac("2026-01", "1400.00")]


UOP_OD = "2025-10-01"
OKRES_UOP = {"tytul": "umowa_o_prace", "platnik": "", "od": UOP_OD, "do": None, "chorobowe": None}  # jak w zrzucie ZUS
ANNA = {
    "sytuacja": ["ciaza"], "tytuly": ["umowa_o_prace"], "okresy_ubezpieczenia": [OKRES_UOP],
    "zatrudnienie_od": UOP_OD, "etat": "0.25", "platnik_ponad_20": {"umowa_o_prace": "do_20"},
    "data_urodzenia": "1994-05-12", "miesiace": MIESIACE_WYSOKIE,
    "ezla": [{"od": "2026-03-08", "do": "2026-05-27", "kod": None}],
    "wynagrodzenie_chorobowe_okres": [{"od": "2026-02-18", "do": "2026-03-22", "kod": None}],
}


def niezaleznie(stale, etat, min_wyn, stawka, dni, z_minimum):
    """Wyliczenie kontrolne bez kodu aplikacji: (podstawa, stawka dzienna, kwota za dni)."""
    zl = lambda x: x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    netto = sum(map(Decimal, stale)) / len(stale) * (1 - Decimal("0.1371"))
    if z_minimum:
        netto = max(netto, Decimal(min_wyn) * (1 - Decimal("0.1371")) * Decimal(etat))
    podstawa = zl(netto)
    dzienna = zl(podstawa * Decimal(stawka) / 30)
    return podstawa, dzienna, dzienna * dni


def _licz(fakty, dzis=DZIS, pochodzenie=None, p=P):
    k = Kontekst(fakty=fakty, pochodzenie=pochodzenie or {}, dzis=dzis)
    wyniki = zasilek_chorobowy_ciaza(k, p)
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
    assert w.kto_wyplaca == "zus" and "ZUS" in w.podsumowanie and w.kwota is not None
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
            odczyt["miesiace"] = [{**m, "strona": 3, "pewnosc": 0.9, "stale_pelna_kwota": 0} for m in MIESIACE_WYSOKIE]
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
    assert wynik["status"] == "przysluguje" and wynik["kto_wyplaca"] == "zus"
    podstawa, dzienna, razem = niezaleznie(["1300", "1300", "1300", "1400"], "0.25", "4806", "0.8", 66, z_minimum=True)
    assert wynik["kwota"] == {"miesieczna": str((podstawa * Decimal("0.8")).quantize(Decimal("0.01"), ROUND_HALF_UP)),
                              "za_okres": str(razem), "stawka": "0.80", "stawka_dzienna": str(dzienna),
                              "podstawa_wymiaru": str(podstawa), "brutto": True}
    assert wynik["orientacyjny"] is True
    assert wynik["okres"] == {"od": "2026-03-23", "do": "2026-05-27", "tygodnie": None, "dni": 66}
    assert wynik["okres_wynagrodzenia"]["od"] == "2026-02-18" and wynik["stawka"] == "0.80"
    assert [b["pytanie_id"] for b in wynik["brakujace_pola"]] == ["D1a"]       # pytanie o kod B
    assert "D1" in [p["pytanie_id"] for p in wynik["pola_do_potwierdzenia"]]    # nakładanie okresów → do sprawdzenia
    assert wynik["wersja_parametrow"] == "2026-01-01"


# ---------- poprawki po 2b: wiek tylko jako zapas, parametry po dacie prawa ----------

def test_nie_pytamy_o_date_urodzenia_gdy_jest_okres_wynagrodzenia_z_z3_art92():
    f = {k: v for k, v in ANNA.items() if k != "data_urodzenia"}
    w = _licz(f)
    assert "data_urodzenia" not in w.brakujace
    assert w.okres.od == date(2026, 3, 23)


def test_pytamy_o_date_urodzenia_tylko_gdy_brak_okresu_wynagrodzenia_art92():
    f = {k: v for k, v in _bez_wynagrodzenia().items() if k != "data_urodzenia"}
    w = _licz(f)
    assert "data_urodzenia" in w.brakujace and w.orientacyjny is True


def test_jedynym_powodem_orientacyjnego_u_anny_jest_brak_kodu_b_art11():
    pochodzenie = {"ezla": WartoscPola(wartosc=ANNA["ezla"], wystawca=Wystawca.PRACODAWCA, kanal=Kanal.UPLOAD,
                                       zrodlo_opis="Z-3", pewnosc=0.9)}
    f = {k: v for k, v in ANNA.items() if k != "data_urodzenia"}
    bez_kodu = _licz(f, pochodzenie=pochodzenie)
    assert bez_kodu.orientacyjny is True and bez_kodu.brakujace == ["ezla_kod_b"]   # podstawa wyższa od minimum
    z_kodem = _licz({**f, "ezla": _dni(date(2026, 3, 8), 81, "B")}, pochodzenie=pochodzenie)
    assert z_kodem.orientacyjny is False and z_kodem.brakujace == [] and z_kodem.stawka == "1.00"


def test_brak_parametrow_na_rok_daje_widoczne_ostrzezenie_w_uwagach_api():
    sid = c.post("/sprawy").json()["id"]
    s = memory.pobierz(sid)
    mapowanie.zapisz_dokument(s, "x.pdf", Fragment(typ="Z-3", strony=[1], osoby=["matka"]), {
        "ezla": [_wiersze("2027-03-08", "2027-05-27")], "wynagrodzenie_chorobowe_okres": [
            _wiersze("2027-02-18", "2027-03-22")],
        "pola": [{"pole": "zatrudnienie_od", "wartosc": "2026-10-01", "strona": 1, "pewnosc": 0.9},
                 {"pole": "platnik_ponad_20", "wartosc": "do_20", "strona": 1, "pewnosc": 0.9}]})
    mapowanie.zapisz_dokument(s, "x.pdf", Fragment(typ="zrzut_systemu_ZUS", strony=[2], osoby=["matka"]), {
        "pola": [{"pole": "tytuly", "wartosc": "umowa_o_prace", "tytul": "umowa_o_prace", "strona": 1, "pewnosc": 0.9}],
        "okresy_ubezpieczenia": [{"kod_tytulu": "0110", "tytul": "umowa_o_prace", "platnik": None,
                                  "od": "2026-10-01", "do": None, "chorobowe": None, "chorobowe_dobrowolne": None,
                                  "strona": 1, "pewnosc": 0.9}]})
    memory.zapisz(s)
    c.post(f"/sprawy/{sid}/odpowiedzi", json=[{"pole": "sytuacja", "wartosc": ["ciaza"]}])
    wynik = next(w for w in c.get(f"/sprawy/{sid}/swiadczenia").json() if w["swiadczenie"] == "zasilek_chorobowy_ciaza")
    assert wynik["status"] == "warunkowo" and wynik["okres"]["od"] == "2027-03-23"   # zwolnienie po dzisiejszej dacie
    assert wynik["uwagi"][0].startswith("Brak parametrów prawnych na rok 2027")      # nie cichy fallback
    assert wynik["wersja_parametrow"] == "2026-01-01"


# ---------- podstawa wymiaru i kwota (etap 2c); dane fikcyjne, rok 2025 (płaca minimalna 4666 zł) ----------

P25 = get_params(date(2025, 3, 1))
STALE_25 = ["1000", "1000", "1000", "1100"]
ANNA_25 = {
    "sytuacja": ["ciaza"], "tytuly": ["umowa_o_prace"], "etat": "0.25", "zatrudnienie_od": "2024-11-01",
    "okresy_ubezpieczenia": [{**OKRES_UOP, "od": "2024-11-01"}], "platnik_ponad_20": {"umowa_o_prace": "do_20"},
    "data_urodzenia": "1994-05-12",
    "miesiace": [_miesiac("2024-11", "1000.00"), _miesiac("2024-12", "1000.00"), _miesiac("2025-01", "1000.00"),
                 _miesiac("2025-02", "1100.00")],
    "ezla": [{"od": "2025-03-01", "do": "2025-06-06", "kod": None}],
    "wynagrodzenie_chorobowe_okres": [{"od": "2025-03-01", "do": "2025-04-02", "kod": None}],     # 33 dni
}
DNI_25 = (date(2025, 6, 6) - date(2025, 4, 3)).days + 1                                            # 65 dni zasiłku
DZIS_25 = date(2025, 12, 31)


def test_kwota_z_minimum_art45_wynik_orientacyjny_z_wariantem_bez_minimum_art36_art45():
    w = _licz(ANNA_25, dzis=DZIS_25, p=P25)
    assert w.status == Status.PRZYSLUGUJE and w.okres.dni == DNI_25 == 65
    podstawa, dzienna, razem = niezaleznie(STALE_25, "0.25", "4666", "0.8", DNI_25, z_minimum=True)
    assert (w.kwota.podstawa_wymiaru, w.kwota.stawka, w.kwota.stawka_dzienna, w.kwota.za_okres) == \
        (str(podstawa), "0.80", str(dzienna), str(razem))
    assert w.orientacyjny is True and "etat" in w.pola_do_potwierdzenia and "ezla_kod_b" in w.brakujace
    bez_p, bez_dz, bez_razem = niezaleznie(STALE_25, "0.25", "4666", "0.8", DNI_25, z_minimum=False)
    _, _, bez_razem_b = niezaleznie(STALE_25, "0.25", "4666", "1.0", DNI_25, z_minimum=False)
    wariant = next(u for u in w.uwagi if u.startswith("Wariant niepotwierdzony"))
    assert kwota_tekst(bez_p) in wariant and kwota_tekst(bez_razem) in wariant and kwota_tekst(bez_razem_b) in wariant
    assert any("art. 45" in u and "komentarzy" in u for u in w.uwagi)                              # skąd proporcja
    _, _, z_kodem_b = niezaleznie(STALE_25, "0.25", "4666", "1.0", DNI_25, z_minimum=True)
    assert any(u.startswith("Przy kodzie „B” zasiłek wyniósłby " + kwota_tekst(z_kodem_b)) for u in w.uwagi)
    assert "orientacyjnie" in w.podsumowanie and kwota_tekst(razem) in w.podsumowanie
    assert any("art. 45" in x for x in w.co_zrobic)


def test_kwota_przy_kodzie_b_stawka_100_art11():
    f = {**ANNA_25, "ezla": [{"od": "2025-03-01", "do": "2025-06-06", "kod": "B"}]}
    w = _licz(f, dzis=DZIS_25, p=P25)
    podstawa, dzienna, razem = niezaleznie(STALE_25, "0.25", "4666", "1.0", DNI_25, z_minimum=True)
    assert (w.kwota.stawka, w.kwota.stawka_dzienna, w.kwota.za_okres) == ("1.00", str(dzienna), str(razem))
    assert "ezla_kod_b" not in w.brakujace and not any(u.startswith("Przy kodzie") for u in w.uwagi)
    assert w.orientacyjny is True                       # nadal: minimum przy niepełnym etacie zmienia podstawę


def test_kwota_stawki_mieszane_kod_b_tylko_w_czesci_art11():
    ezla = [{"od": "2025-03-01", "do": "2025-04-30", "kod": "B"}, {"od": "2025-05-01", "do": "2025-06-06", "kod": "A"}]
    w = _licz({**ANNA_25, "ezla": ezla}, dzis=DZIS_25, p=P25)
    d_b = (date(2025, 4, 30) - date(2025, 4, 3)).days + 1                       # dni zasiłku z kodem B
    d_a = DNI_25 - d_b
    _, dz_b, _ = niezaleznie(STALE_25, "0.25", "4666", "1.0", 1, z_minimum=True)
    _, dz_a, _ = niezaleznie(STALE_25, "0.25", "4666", "0.8", 1, z_minimum=True)
    assert w.kwota.stawka is None and w.kwota.stawka_dzienna is None
    assert Decimal(w.kwota.za_okres) == dz_b * d_b + dz_a * d_a


def test_art45_parametr_brak_nie_podnosi_podstawy_i_pokazuje_wariant_proporcjonalny_art45():
    p = {**P25, "art45_niepelny_etat": "brak"}
    w = _licz(ANNA_25, dzis=DZIS_25, p=p)
    podstawa, _, razem = niezaleznie(STALE_25, "0.25", "4666", "0.8", DNI_25, z_minimum=False)
    assert w.kwota.podstawa_wymiaru == str(podstawa) and w.kwota.za_okres == str(razem)
    assert w.orientacyjny is True
    assert any("Nie podnosiliśmy podstawy" in u for u in w.uwagi)
    assert any(u.startswith("Wariant niepotwierdzony (z najniższą podstawą proporcjonalną do etatu)") for u in w.uwagi)


def test_pelny_etat_minimum_jest_pewne_nie_robi_wyniku_orientacyjnego_art45():
    f = {**ANNA_25, "etat": "1.00", "ezla_kod_b": False}
    w = _licz(f, dzis=DZIS_25, p=P25)
    podstawa, _, _ = niezaleznie(STALE_25, "1", "4666", "0.8", DNI_25, z_minimum=True)
    assert w.kwota.podstawa_wymiaru == str(podstawa) == "4026.29"                  # 4666 − 13,71%
    assert w.orientacyjny is False                      # pełny etat: minimum pewne; kod podany (D1a = nie)
    assert not any("Wariant niepotwierdzony" in u for u in w.uwagi)


def test_brak_miesiecy_brak_kwoty_ale_status_i_okres_bez_zmian_art36():
    f = {k: v for k, v in ANNA_25.items() if k != "miesiace"}
    w = _licz(f, dzis=DZIS_25, p=P25)
    assert w.status == Status.PRZYSLUGUJE and w.okres.dni == 65 and w.kwota is None
    assert "srednie_wynagrodzenie_brutto" in w.brakujace


def test_dzialalnosc_12_miesiecy_i_prog_60_proc_prosta_srednia_art48():
    f = _dzialalnosc_facts()
    w = _licz(f, p=P)
    podstawa, dzienna, razem = niezaleznie(["4000"] * 12, "1", "4806", "0.8", w.okres.dni, z_minimum=False)
    assert w.kto_wyplaca == "zus" and w.kwota.podstawa_wymiaru == str(podstawa) == "3451.60"
    assert w.kwota.za_okres == str(razem) and w.kwota.stawka_dzienna == str(dzienna)


def test_dzialalnosc_prog_60_proc_niespelniony_bez_kwoty_art48a():
    w = _licz({**_dzialalnosc_facts(), "podstawa_60_proc": False}, p=P)
    assert w.status == Status.PRZYSLUGUJE and w.kwota is None and w.okres is not None
    assert any("art. 48a" in u and "Kwoty nie liczymy" in u for u in w.uwagi)


def test_dzialalnosc_ubezpieczenie_krotsze_niz_12_miesiecy_bez_kwoty_art48a():
    f = {**_dzialalnosc_facts(), "chorobowe_od": "2025-09-01",
         "okresy_ubezpieczenia": [{**OKRES_UOP, "tytul": "dzialalnosc", "od": "2025-09-01"}]}
    w = _licz(f, p=P)
    assert w.kwota is None and any("art. 48a" in u for u in w.uwagi) and w.brakujace == ["ezla_kod_b"]


def test_dzialalnosc_nieznany_prog_60_proc_pytamy_nie_liczymy_art48a():
    f = {k: v for k, v in _dzialalnosc_facts().items() if k != "podstawa_60_proc"}
    w = _licz(f, p=P)
    assert w.kwota is None and "podstawa_60_proc" in w.brakujace


def _dzialalnosc_facts():
    miesiace = [{"miesiac": f"{r}-{m:02d}", "podstawa": "4000.00", "wakacje_skladkowe": False}
                for r, m in [(2025, i) for i in range(3, 13)] + [(2026, 1), (2026, 2)]]
    return {"sytuacja": ["ciaza"], "tytuly": ["dzialalnosc"], "chorobowe": {"dzialalnosc": True},
            "chorobowe_od": "2024-06-01", "okresy_ubezpieczenia": [{**OKRES_UOP, "tytul": "dzialalnosc", "od": "2024-06-01"}],
            "ezla": [{"od": "2026-03-08", "do": "2026-04-26", "kod": None}], "podstawa_deklarowana": miesiace,
            "podstawa_60_proc": True}
