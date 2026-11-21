"""Test przepływu: logowanie → sprawa → dane z ZUS → pytania → uprawnienia → kalkulator."""
from fastapi.testclient import TestClient

from app.main import app

c = TestClient(app)


def test_pelny_przeplyw_symulacji():
    token = c.post("/auth/mobywatel", json={"uzytkownik": "anna"}).json()["token"]
    sid = c.post("/sprawy").json()["id"]
    assert c.post(f"/zus/pobierz-do-sprawy/{sid}", headers={"Authorization": token}).status_code == 200

    c.post(f"/sprawy/{sid}/odpowiedzi", json=[{"pole": "sytuacja", "wartosc": ["urodzenie"]}])
    pytania = [p["pole"] for p in c.get(f"/sprawy/{sid}/pytania").json()]
    assert "data_porodu" in pytania and "tytuly" not in pytania  # tytuly przyszły z ZUS

    c.post(f"/sprawy/{sid}/odpowiedzi", json=[
        {"pole": "data_porodu", "wartosc": "2026-07-10"},
        {"pole": "liczba_dzieci", "wartosc": 1},
        {"pole": "ubezpieczony_w_dniu_zdarzenia", "wartosc": True},
        {"pole": "wariant", "wartosc": "100_70"},
    ])
    upr = c.get(f"/sprawy/{sid}/uprawnienia").json()
    assert upr[0]["status"] == "przysluguje" and upr[0]["kto_wyplaca"].startswith("pracodawca")

    wynik = c.get(f"/sprawy/{sid}/kalkulator").json()
    assert wynik["okresy"][0]["stawka"] == 1.0 and wynik["suma"] > 0


def test_zadluzenie_dzialalnosc_art2a():
    token = c.post("/auth/mobywatel", json={"uzytkownik": "marta"}).json()["token"]
    sid = c.post("/sprawy").json()["id"]
    c.post(f"/zus/pobierz-do-sprawy/{sid}", headers={"Authorization": token})
    c.post(f"/sprawy/{sid}/odpowiedzi", json=[{"pole": "ubezpieczony_w_dniu_zdarzenia", "wartosc": True}])
    assert c.get(f"/sprawy/{sid}/uprawnienia").json()[0]["status"] == "nie_przysluguje"
