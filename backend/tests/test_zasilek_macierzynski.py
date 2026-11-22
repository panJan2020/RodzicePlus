"""Reguła zasiłku macierzyńskiego matki: 4 statusy, okresy, stawki, kwoty, kto wypłaca, wynik orientacyjny."""
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.calculator import scenariusz
from app.domain.model import Kanal, WartoscPola, Wystawca
from app.domain.results import Status
from app.main import app
from app.params.store import get_params
from app.rules.wspolne import Kontekst, kwota_tekst, tygodnie_tekst
from app.rules.zasilek_macierzynski import URLOP_MACIERZYNSKI, URLOP_RODZICIELSKI, zasilek_macierzynski

P = get_params(date(2026, 6, 1))
DZIS = date(2026, 11, 22)
c = TestClient(app)

OKRES_UOP = {"tytul": "umowa_o_prace", "platnik": "X", "od": "2021-03-01", "do": None, "chorobowe": True}
PRACOWNICA = {"sytuacja": ["urodzenie"], "tytuly": ["umowa_o_prace"], "etat": "1.00",
              "okresy_ubezpieczenia": [OKRES_UOP], "platnik_ponad_20": {"umowa_o_prace": "ponad_20"},
              "data_porodu": "2026-07-10", "liczba_dzieci": 1, "srednie_wynagrodzenie_brutto": "8200.00"}


def _zus(v):
    return WartoscPola(wartosc=v, wystawca=Wystawca.ZUS, kanal=Kanal.ZUS_KONTO, zrodlo_opis="ZUS")


def _licz(fakty, dziecko=None, pochodzenie=None, dzis=DZIS):
    wybory = scenariusz.domyslny(fakty, P)
    k = Kontekst(fakty=fakty, fakty_dziecka={"za_zyciem": False} if dziecko is None else dziecko, wybory=wybory,
                 pochodzenie=pochodzenie if pochodzenie is not None else {k: _zus(v) for k, v in fakty.items()},
                 dzis=dzis)
    mac, rodz = zasilek_macierzynski(k, P)
    assert (mac.swiadczenie, rodz.swiadczenie) == (URLOP_MACIERZYNSKI, URLOP_RODZICIELSKI)
    assert mac.status == rodz.status  # wspólne ustalenie prawa
    return mac, rodz


# ---------- status ----------

def test_ubezpieczona_w_dniu_porodu_przysluguje_art29():
    mac, rodz = _licz(PRACOWNICA)
    assert mac.status == Status.PRZYSLUGUJE and mac.brakujace == []
    assert mac.podsumowanie.startswith("Przysługuje Ci zasiłek za 20 tygodni urlopu macierzyńskiego (od 10.07.2026")
    assert "miesięcznie brutto" in mac.podsumowanie
    assert rodz.okres.tygodnie == 32


def test_brak_ubezpieczenia_w_dniu_porodu_nie_przysluguje_art29():
    f = {**PRACOWNICA, "tytuly": ["dzielo"], "data_porodu": "2026-10-15",
         "okresy_ubezpieczenia": [{**OKRES_UOP, "do": "2026-08-31"}]}
    mac, _ = _licz(f)
    assert mac.status == Status.NIE_PRZYSLUGUJE and mac.okres is None and mac.kwota is None
    assert mac.powody[0].pole == "okresy_ubezpieczenia" and "31.08.2026" in " ".join(mac.uzasadnienie)
    assert any("art. 30" in x for x in mac.co_zrobic) and "art. 29 ustawy zasiłkowej" in mac.podstawa_prawna
    assert mac.kto_wyplaca is None


def test_porod_w_przyszlosci_warunkowo_art29():
    f = {**PRACOWNICA, "sytuacja": ["ciaza"], "pdp": "2027-03-10"}
    del f["data_porodu"]
    mac, rodz = _licz(f)
    assert mac.status == Status.WARUNKOWO
    assert mac.warunki[0].opis == "Ubezpieczenie chorobowe w dniu porodu"
    assert mac.ryzyka == ["brak_ubezpieczenia_w_dniu_porodu"]
    assert ", o ile w dniu porodu nadal będziesz ubezpieczona" in mac.podsumowanie
    assert mac.okres.od == date(2027, 3, 10) and mac.kwota is not None


def test_porod_w_przyszlosci_bez_ubezpieczenia_nadal_warunkowo_art29():
    f = {"sytuacja": ["ciaza"], "tytuly": ["umowa_o_prace"], "umowa_rodzaj": "zastepstwo",
         "umowa_do": "2026-12-31", "pdp": "2027-03-10"}
    mac, _ = _licz(f)
    assert mac.status == Status.WARUNKOWO
    assert mac.podsumowanie.startswith("Jeśli nic się nie zmieni, zasiłek nie przysługuje")
    assert "Jeśli nic się nie zmieni, zasiłek nie przysługuje." in mac.uzasadnienie and mac.co_zrobic


def test_umowa_przedluzona_do_porodu_art177kp():
    f = {"sytuacja": ["urodzenie"], "tytuly": ["umowa_o_prace"], "umowa_rodzaj": "okreslony",
         "umowa_do": "2026-06-30", "pdp": "2026-07-12", "data_porodu": "2026-07-10", "liczba_dzieci": 1}
    mac, _ = _licz(f)
    assert mac.status == Status.PRZYSLUGUJE and any("art. 177" in x for x in mac.uzasadnienie)
    assert any("przybliżeniu" in x for x in mac.uwagi)


def test_umowa_na_zastepstwo_nie_przedluzona_art177kp():
    f = {"sytuacja": ["urodzenie"], "tytuly": ["umowa_o_prace"], "umowa_rodzaj": "zastepstwo",
         "umowa_do": "2026-06-30", "pdp": "2026-07-12", "data_porodu": "2026-07-10"}
    assert _licz(f)[0].status == Status.NIE_PRZYSLUGUJE


def test_plan_ustania_przed_porodem_ryzyko_art29():
    f = {**PRACOWNICA, "sytuacja": ["ciaza"], "pdp": "2027-03-10", "plan_ustania": True,
         "plan_ustania_data": "2027-01-31"}
    del f["data_porodu"]
    mac, _ = _licz(f)
    assert mac.status == Status.WARUNKOWO and mac.powody[0].pole == "plan_ustania_data"
    assert "brak_ubezpieczenia_w_dniu_porodu" in mac.ryzyka and mac.kwota is None


def test_brak_pol_brak_danych_art29():
    mac, rodz = _licz({"sytuacja": ["urodzenie"], "tytuly": ["umowa_o_prace"]}, pochodzenie={})
    assert mac.status == Status.BRAK_DANYCH
    assert mac.brakujace == ["data_porodu", "pdp", "umowa_rodzaj"]
    assert mac.podsumowanie == "Brakuje danych, żeby ustalić, czy przysługuje Ci zasiłek."


def test_zadluzenie_dzialalnosc_nie_przysluguje_art2a():
    f = {"sytuacja": ["urodzenie"], "tytuly": ["dzialalnosc"], "chorobowe": {"dzialalnosc": True},
         "data_porodu": "2026-07-10", "liczba_dzieci": 1, "zadluzenie_kwota": "120.00"}
    mac, _ = _licz(f)
    assert mac.status == Status.NIE_PRZYSLUGUJE and mac.powody[0].pole == "zadluzenie_kwota"
    assert "art. 2a ustawy zasiłkowej" in mac.podstawa_prawna


def test_brak_kwoty_nie_zmienia_statusu_art29():
    f = {**PRACOWNICA}
    del f["srednie_wynagrodzenie_brutto"]
    mac, _ = _licz(f)
    assert mac.status == Status.PRZYSLUGUJE and mac.kwota is None and mac.okres is not None
    assert mac.brakujace == ["srednie_wynagrodzenie_brutto"]


# ---------- okres i stawki ----------

@pytest.mark.parametrize("dzieci,mac_tyg,rodz_tyg", [(1, 20, 32), (2, 31, 34), (3, 33, 34), (5, 37, 34)])
def test_wymiar_wg_liczby_dzieci_art180kp(dzieci, mac_tyg, rodz_tyg):
    mac, rodz = _licz({**PRACOWNICA, "liczba_dzieci": dzieci})
    assert (mac.okres.tygodnie, rodz.okres.tygodnie) == (mac_tyg, rodz_tyg)


def test_rodzicielski_za_zyciem_art182_1a():
    _, rodz = _licz(PRACOWNICA, dziecko={"za_zyciem": True})
    assert rodz.okres.tygodnie == 65 - 9 and any("wyłącznie drugiemu rodzicowi" in x for x in rodz.uwagi)


def test_brak_liczby_dzieci_i_za_zyciem_zalozenia_art180kp():
    f = {**PRACOWNICA}
    del f["liczba_dzieci"]
    mac, rodz = _licz(f, dziecko={})
    assert mac.okres.tygodnie == 20 and "liczba_dzieci" in mac.brakujace
    assert "za_zyciem" in rodz.brakujace and "za_zyciem" not in mac.brakujace


def test_stawki_100_70_art31():
    mac, rodz = _licz(PRACOWNICA)
    assert (mac.kwota.stawka, rodz.kwota.stawka) == ("1.00", "0.70")
    assert mac.kwota.podstawa_wymiaru == "7075.78" and mac.kwota.brutto is True


def test_81_5_w_terminie_art31_ust3():
    mac, rodz = _licz({**PRACOWNICA, "wniosek_81_5_data": "2026-07-31"})
    assert mac.kwota.stawka == rodz.kwota.stawka == "0.815"


def test_81_5_po_terminie_art31_ust3():
    mac, _ = _licz({**PRACOWNICA, "wniosek_81_5_data": "2026-08-01"})
    assert mac.kwota.stawka == "1.00"


def test_kwoty_co_do_grosza_art36():
    # 8200 zł × (1 − 0,1371) = 7075,78; 100%: 7075,78 / 30 = 235,86 zł × 140 dni = 33 020,40 zł
    mac, rodz = _licz(PRACOWNICA)
    assert (mac.kwota.miesieczna, mac.kwota.stawka_dzienna, mac.kwota.za_okres) == ("7075.78", "235.86", "33020.40")
    assert (rodz.kwota.stawka_dzienna, rodz.kwota.za_okres) == ("165.10", "36982.40")


def test_start_urlopu_przed_porodem_art180kp():
    mac, rodz = _licz({**PRACOWNICA, "macierzynski_od": "2026-06-26"})
    assert mac.okres.od == date(2026, 6, 26) and any("przed porodem" in x for x in mac.uzasadnienie)


# ---------- kto wypłaca ----------

def test_kto_wyplaca_platnik_ponad_20_art61():
    mac, _ = _licz(PRACOWNICA)
    assert mac.kto_wyplaca == "platnik" and "kadrach" in mac.gdzie_zlozyc


def test_kto_wyplaca_zus_art61():
    mac, _ = _licz({**PRACOWNICA, "platnik_ponad_20": {"umowa_o_prace": "do_20"}})
    assert mac.kto_wyplaca == "zus" and "Z-3" in mac.gdzie_zlozyc


def test_kto_wyplaca_nie_wiem_nie_blokuje_art61():
    mac, _ = _licz({**PRACOWNICA, "platnik_ponad_20": {"umowa_o_prace": "nie_wiem"}})
    assert mac.status == Status.PRZYSLUGUJE and mac.kto_wyplaca is None
    assert mac.kto_wyplaca_opis.startswith("Zapytaj w kadrach") and "platnik_ponad_20" in mac.brakujace


# ---------- wynik orientacyjny ----------

def test_tryb_uproszczony_orientacyjny():
    mac, _ = _licz(PRACOWNICA)
    assert mac.orientacyjny is True and "miesiace" in mac.pola_do_potwierdzenia
    assert any("orientacyjna" in x for x in mac.uwagi)


def test_deklaracje_uzytkownika_do_potwierdzenia():
    poch = {k: _zus(v) for k, v in PRACOWNICA.items()}
    poch["data_porodu"] = WartoscPola(wartosc="2026-07-10", wystawca=Wystawca.UZYTKOWNIK, kanal=Kanal.KREATOR,
                                      zrodlo_opis="Twoja odpowiedź")
    mac, _ = _licz(PRACOWNICA, pochodzenie=poch)
    assert "data_porodu" in mac.pola_do_potwierdzenia


def test_teksty_kwot_i_tygodni():
    assert kwota_tekst("1234.5") == "1 234,50 zł" and kwota_tekst("999.00") == "999,00 zł"
    assert [tygodnie_tekst(n) for n in (1, 2, 20, 22, 32, 12)] == \
        ["1 tydzień", "2 tygodnie", "20 tygodni", "22 tygodnie", "32 tygodnie", "12 tygodni"]


# ---------- API ----------

def _odp(sid, h, **pola):
    return c.post(f"/sprawy/{sid}/odpowiedzi", headers=h, json=[{"pole": k, "wartosc": v} for k, v in pola.items()])


def _konto(login):
    h = {"Authorization": f"sim-{login}"}
    sid = c.post("/sprawy", headers=h).json()["id"]
    for kod in ("zus_konto", "zus_platnik"):
        assert c.post(f"/sprawy/{sid}/zrodla/{kod}/pobierz", headers=h).status_code == 200
    return sid, h


def test_api_anna_ciaza_warunkowo_z_kwota_orientacyjna_art29():
    sid, h = _konto("anna")
    assert _odp(sid, h, sytuacja=["ciaza"], pdp="2027-03-10").status_code == 200
    wyniki = c.get(f"/sprawy/{sid}/swiadczenia", headers=h).json()
    # Bez dokumentów i bez zwolnień (ezla) karta „zasiłek chorobowy – brak danych” się nie pokazuje.
    assert [w["swiadczenie"] for w in wyniki] == [URLOP_MACIERZYNSKI, URLOP_RODZICIELSKI]
    w = wyniki[0]
    assert w["status"] == "warunkowo" and w["scenariusz_id"] == "domyslny" and w["orientacyjny"] is True
    assert w["kwota"] == {"miesieczna": "7075.78", "za_okres": "33020.40", "stawka": "1.00",
                          "stawka_dzienna": "235.86", "podstawa_wymiaru": "7075.78", "brutto": True}
    assert w["okres"] == {"od": "2027-03-10", "do": "2027-07-27", "tygodnie": 20, "dni": None}
    assert w["warunki"] == [{"opis": "Ubezpieczenie chorobowe w dniu porodu",
                             "ryzyko": "brak_ubezpieczenia_w_dniu_porodu"}]
    potw = {x["pytanie_id"] for x in w["pola_do_potwierdzenia"]}
    assert {"O4", "G1"} <= potw  # miesiące z Z-3 i przewidywana data porodu wpisana przez użytkownika
    assert w["kto_wyplaca"] == "platnik" and w["wersja_parametrow"] == "2026-01-01"


def test_api_zrodla_danych_i_karta_chorobowego_z_ezla():
    """„Skąd te dane?”: pola użyte w wyniku z opisem źródła; z ezla karta chorobowego wraca (nawet z brakami)."""
    sid, h = _konto("anna")
    _odp(sid, h, sytuacja=["ciaza"], pdp="2027-03-10")
    w = c.get(f"/sprawy/{sid}/swiadczenia", headers=h).json()[0]
    zrodla = {z["pole"]: z for z in w["zrodla_danych"]}
    assert zrodla["pdp"]["zrodlo_opis"] == "Twoja odpowiedź" and zrodla["pdp"]["do_sprawdzenia"] is True
    assert zrodla["okresy_ubezpieczenia"]["kanal"] == "zus_konto" and zrodla["okresy_ubezpieczenia"]["tresc"]
    assert "data_porodu" not in zrodla                       # pole bez wartości nie jest „źródłem”

    c.post(f"/sprawy/{sid}/zrodla/ezla/pobierz", headers=h)  # zwolnienia z e-ZLA
    pola = [x["swiadczenie"] for x in c.get(f"/sprawy/{sid}/swiadczenia", headers=h).json()]
    assert "zasilek_chorobowy_ciaza" in pola


def test_api_kasia_po_porodzie_nie_przysluguje_art29():
    sid, h = _konto("kasia")
    _odp(sid, h, sytuacja=["urodzenie"], data_porodu="2026-10-15")
    w = c.get(f"/sprawy/{sid}/swiadczenia", headers=h).json()[0]
    assert w["status"] == "nie_przysluguje" and w["kwota"] is None and w["okres"] is None
    assert w["powody"] and w["co_zrobic"] and "31.08.2026" in " ".join(w["uzasadnienie"])


def test_api_ojciec_bez_wyniku_zasilku_matki():
    sid = c.post("/sprawy").json()["id"]
    c.post(f"/sprawy/{sid}/osoby", json={"rola": "ojciec", "imie": "Piotr"})
    assert {w["osoba_id"] for w in c.get(f"/sprawy/{sid}/swiadczenia").json()} == {"o1"}


def test_api_kalkulator_powrot_do_pracy_i_ostrzezenia():
    sid, h = _konto("anna")
    _odp(sid, h, sytuacja=["urodzenie"], data_porodu="2026-07-10", liczba_dzieci=1)
    k = c.get(f"/sprawy/{sid}/kalkulator", headers=h).json()
    assert k["osoby"][0]["powrot_do_pracy"] == "2027-07-09"  # 10.07.2026 + 52 tygodnie (364 dni)
    assert k["okresy"][0]["stawka_dzienna"] == "235.86" and k["orientacyjny"] is True
    assert any("wyłącznie drugiemu rodzicowi" in x for x in k["ostrzezenia"])


def test_zasilek_macierzynski_z_okresem_zus_bez_informacji_o_chorobowym_art29():
    """Regresja: `chorobowe: null` w okresie (np. ze zrzutu ZUS) nie może odbierać prawa umowie o pracę."""
    f = {**PRACOWNICA, "okresy_ubezpieczenia": [{**OKRES_UOP, "chorobowe": None}]}
    mac, rodz = _licz(f)
    assert mac.status == rodz.status == Status.PRZYSLUGUJE and mac.brakujace == []
    zlecenie = {**PRACOWNICA, "tytuly": ["zlecenie"], "okresy_ubezpieczenia": [{**OKRES_UOP, "tytul": "zlecenie",
                                                                               "chorobowe": None}]}
    mac, _ = _licz(zlecenie)
    assert mac.status == Status.BRAK_DANYCH and "chorobowe_dobrowolne" in mac.brakujace
