"""Pola wyliczane: ubezpieczenie chorobowe w dniu porodu (B7), data zdarzenia i data powstania prawa."""
from datetime import date

from fastapi.testclient import TestClient

from app.main import app
from app.params.store import get_params
from app.rules import wyliczone

P = get_params(date(2026, 6, 1))
c = TestClient(app)

OKRES_UOP = {"tytul": "umowa_o_prace", "platnik": "X", "od": "2022-01-01", "do": None, "chorobowe": True}


def test_okres_z_zus_obejmuje_dzien_porodu_art29():
    u = wyliczone.ubezpieczony_w_dniu({"okresy_ubezpieczenia": [OKRES_UOP]}, date(2026, 7, 10), P)
    assert u.wartosc is True and u.brakujace == []


def test_okres_zakonczony_przed_porodem_art29():
    okresy = [{**OKRES_UOP, "do": "2026-08-31"}, {"tytul": "dzielo", "platnik": "Y", "od": "2026-10-01",
                                                  "do": None, "chorobowe": False}]
    u = wyliczone.ubezpieczony_w_dniu({"okresy_ubezpieczenia": okresy}, date(2026, 10, 15), P)
    assert u.wartosc is False and "31.08.2026" in u.uzasadnienie[0]
    assert u.powody[0][0] == "okresy_ubezpieczenia"


def test_umowa_przedluzona_do_porodu_art177kp():
    # pdp 2027-03-10 → początek ciąży ok. 2026-06-03 → koniec 3. miesiąca ok. 2026-09-03
    f = {"tytuly": ["umowa_o_prace"], "umowa_rodzaj": "okreslony", "umowa_do": "2026-12-31", "pdp": "2027-03-10"}
    u = wyliczone.ubezpieczony_w_dniu(f, date(2027, 3, 10), P)
    assert u.wartosc is True and "art. 177" in u.uzasadnienie[0]
    assert any("przybliżeniu" in x for x in u.uwagi)


def test_umowa_konczaca_sie_przed_3_miesiacem_ciazy_nie_przedluzona_art177kp():
    f = {"tytuly": ["umowa_o_prace"], "umowa_rodzaj": "okreslony", "umowa_do": "2026-08-01", "pdp": "2027-03-10"}
    assert wyliczone.ubezpieczony_w_dniu(f, date(2027, 3, 10), P).wartosc is False


def test_umowa_na_zastepstwo_nie_przedluzona_art177kp():
    f = {"tytuly": ["umowa_o_prace"], "umowa_rodzaj": "zastepstwo", "umowa_do": "2026-12-31", "pdp": "2027-03-10"}
    u = wyliczone.ubezpieczony_w_dniu(f, date(2027, 3, 10), P)
    assert u.wartosc is False and "zastępstwo" in u.uzasadnienie[0]


def test_koniec_3_miesiaca_ciazy_przyblizenie_art177kp():
    assert wyliczone.koniec_3_miesiaca_ciazy(date(2027, 3, 10), P) == date(2026, 9, 3)


def test_plan_ustania_przed_porodem_art29():
    f = {"okresy_ubezpieczenia": [OKRES_UOP], "plan_ustania": True, "plan_ustania_data": "2027-01-31"}
    u = wyliczone.ubezpieczony_w_dniu(f, date(2027, 3, 10), P)
    assert u.wartosc is False and u.powody[0][0] == "plan_ustania_data"


def test_zlecenie_bez_dobrowolnego_chorobowego_art29():
    f = {"tytuly": ["zlecenie"], "chorobowe_dobrowolne": False}
    assert wyliczone.ubezpieczony_w_dniu(f, date(2026, 7, 10), P).wartosc is False
    assert wyliczone.ubezpieczony_w_dniu({"tytuly": ["zlecenie"]}, date(2026, 7, 10), P).brakujace == \
        ["chorobowe_dobrowolne"]


def test_brak_danych_umowy_art29():
    u = wyliczone.ubezpieczony_w_dniu({"tytuly": ["umowa_o_prace"]}, None, P)
    assert u.wartosc is None and u.brakujace == ["data_porodu", "pdp", "umowa_rodzaj"]


def test_data_prawa_start_urlopu_przed_porodem_art29():
    f = {"pdp": "2027-03-10", "macierzynski_od": "2027-02-20"}
    assert wyliczone.data_prawa(f) == date(2027, 2, 20)
    assert wyliczone.data_prawa(f, {"start_urlopu_macierzynskiego": "2027-02-01"}) == date(2027, 2, 1)
    assert wyliczone.data_prawa({"pdp": "2027-03-10", "data_porodu": "2027-03-05"}) == date(2027, 3, 5)


def test_moje_dane_pokazuja_b7_wyliczone_art29():
    sid = c.post("/sprawy").json()["id"]
    c.post(f"/sprawy/{sid}/odpowiedzi", json=[
        {"pole": k, "wartosc": v} for k, v in {"sytuacja": ["urodzenie"], "tytuly": ["umowa_o_prace"],
                                                "umowa_rodzaj": "nieokreslony", "data_porodu": "2026-07-10"}.items()])
    d = c.get(f"/sprawy/{sid}/dane").json()
    b7 = next(p for s in d["sekcje"] for p in s["pytania"] if p["id"] == "B7")
    assert b7["rodzaj"] == "wyliczone" and b7["edytowalne"] is False
    assert b7["wartosci"][0]["wartosc"] is True and b7["wartosci"][0]["wystawca"] == "wyliczone"
    assert b7["aktywna_wartosc_id"] == b7["wartosci"][0]["id"]
    # nie da się na nie odpowiedzieć ręcznie
    r = c.post(f"/sprawy/{sid}/odpowiedzi", json=[{"pole": "ubezpieczony_w_dniu_zdarzenia", "wartosc": True}])
    assert r.status_code == 400
