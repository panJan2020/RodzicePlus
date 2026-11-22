"""Symulowane logowanie przez mObywatela (docs/api.md 2.1)."""
from fastapi.testclient import TestClient

from app.main import app

c = TestClient(app)


def test_lista_kont_testowych():
    konta = c.get("/auth/mobywatel/konta").json()
    loginy = {k["login"] for k in konta}
    assert {"anna", "marta", "piotr"} <= loginy
    assert all(k["imie"] and k["nazwisko"] and k["opis"] for k in konta)


def test_logowanie_i_dane_zalogowanego():
    sesja = c.post("/auth/mobywatel", json={"login": "anna"}).json()
    assert sesja == {"token": "sim-anna", "login": "anna", "imie": "Anna", "nazwisko": "Testowa", "admin": False}
    ja = c.get("/auth/ja", headers={"Authorization": sesja["token"]})
    assert ja.status_code == 200 and ja.json()["login"] == "anna"


def test_nieznane_konto():
    r = c.post("/auth/mobywatel", json={"login": "nieistnieje"})
    assert r.status_code == 404 and "konta" in r.json()["detail"]


def test_bledny_lub_brak_tokenu():
    assert c.get("/auth/ja").status_code == 401
    assert c.get("/auth/ja", headers={"Authorization": "anna"}).status_code == 401
    assert c.get("/auth/ja", headers={"Authorization": "sim-nieistnieje"}).status_code == 401
