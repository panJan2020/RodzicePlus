"""Test przepływu: logowanie → sprawa → dane z ZUS → odpowiedzi → świadczenia → kalkulator."""
from fastapi.testclient import TestClient

from app.main import app

c = TestClient(app)


def _odp(sid, h, **pola):
    return c.post(f"/sprawy/{sid}/odpowiedzi", headers=h, json=[{"pole": k, "wartosc": v} for k, v in pola.items()])


def test_pelny_przeplyw_symulacji_art29():
    h = {"Authorization": c.post("/auth/mobywatel", json={"login": "anna"}).json()["token"]}
    sid = c.post("/sprawy", headers=h).json()["id"]
    for kod in ("zus_konto", "zus_platnik"):
        assert c.post(f"/sprawy/{sid}/zrodla/{kod}/pobierz", headers=h).status_code == 200

    _odp(sid, h, sytuacja=["urodzenie"])
    pytania = [p["pole"] for p in c.get(f"/sprawy/{sid}/pytania", headers=h).json()]
    assert "data_porodu" in pytania and "tytuly" not in pytania  # tytuly przyszły z ZUS

    _odp(sid, h, data_porodu="2026-07-10", liczba_dzieci=1, ubezpieczony_w_dniu_zdarzenia=True)
    w = c.get(f"/sprawy/{sid}/swiadczenia", headers=h).json()[0]
    assert w["status"] == "przysluguje" and w["osoba_id"] == "o1" and w["kto_wyplaca"] == "platnik"
    assert "pracodawca" in w["kto_wyplaca_opis"] and w["wersja_parametrow"] == "2026-01-01"

    k = c.get(f"/sprawy/{sid}/kalkulator", headers=h).json()
    assert k["scenariusz_id"] == "domyslny" and k["okresy"][0]["stawka"] == "1.00"
    assert k["okresy"][1]["stawka"] == "0.70" and k["okresy"][0]["osoba_id"] == "o1"
    assert isinstance(k["suma"], str) and float(k["suma"]) > 0  # kwoty jako tekst
    assert k["osoby"][0]["podstawa_wymiaru"] == "7075.78"  # 8200 zł − 13,71%


def test_wniosek_81_5_w_terminie_z_faktow_art31():
    sid = c.post("/sprawy").json()["id"]
    _odp(sid, None, sytuacja=["urodzenie"], tytuly=["umowa_o_prace"], srednie_wynagrodzenie_brutto="6000",
         data_porodu="2026-07-10", wniosek_81_5_data="2026-07-31")
    assert {o["stawka"] for o in c.get(f"/sprawy/{sid}/kalkulator").json()["okresy"]} == {"0.815"}
    _odp(sid, None, wniosek_81_5_data="2026-08-01")  # 22 dni po porodzie – po terminie
    assert c.get(f"/sprawy/{sid}/kalkulator").json()["okresy"][0]["stawka"] == "1.00"


def test_za_zyciem_z_pola_dziecka():
    sid = c.post("/sprawy").json()["id"]
    _odp(sid, None, sytuacja=["urodzenie"], tytuly=["umowa_o_prace"], srednie_wynagrodzenie_brutto="6000",
         data_porodu="2026-07-10")
    c.post(f"/sprawy/{sid}/odpowiedzi", json=[{"osoba": "o2", "pole": "za_zyciem", "wartosc": True}])
    k = c.get(f"/sprawy/{sid}/kalkulator").json()
    assert k["okresy"][1]["tygodnie"] == 65 - 9


def test_zadluzenie_dzialalnosc_art2a():
    h = {"Authorization": "sim-marta"}
    sid = c.post("/sprawy", headers=h).json()["id"]
    for kod in ("zus_konto", "zus_platnik"):
        c.post(f"/sprawy/{sid}/zrodla/{kod}/pobierz", headers=h)
    # B7 zależy od A1 (sytuacja) – bez A1 byłoby zablokowane i reguła by go nie widziała.
    _odp(sid, h, sytuacja=["urodzenie"], ubezpieczony_w_dniu_zdarzenia=True)
    w = c.get(f"/sprawy/{sid}/swiadczenia", headers=h).json()[0]
    assert w["status"] == "nie_przysluguje" and w["powody"][0]["pole"] == "zadluzenie_kwota"


def test_brakujace_pola_jako_pytania_art29():
    sid = c.post("/sprawy").json()["id"]
    w = c.get(f"/sprawy/{sid}/swiadczenia").json()[0]
    assert w["status"] == "brak_danych"
    # B1 aktywne → "B1"; B7 zablokowane przez A1 → wskazujemy "A1".
    assert [b["pytanie_id"] for b in w["brakujace_pola"]] == ["B1", "A1"]
    assert w["brakujace_pola"][0] == {"pytanie_id": "B1", "tresc": "Na jakiej podstawie pracujesz?",
                                      "gdzie_znalezc": None}


def test_brakujace_pola_po_odpowiedzi_na_a1_art29():
    sid = c.post("/sprawy").json()["id"]
    _odp(sid, None, sytuacja=["urodzenie"], tytuly=["zlecenie"])
    w = c.get(f"/sprawy/{sid}/swiadczenia").json()[0]
    assert [b["pytanie_id"] for b in w["brakujace_pola"]] == ["B7", "B4a"]


def test_zadania_nowa_sciezka():
    assert c.get("/zadania/nieistnieje").status_code == 404
