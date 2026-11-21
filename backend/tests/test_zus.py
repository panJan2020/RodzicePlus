"""FR-02 – symulowane pobranie z ZUS danych o ubezpieczeniu albo o jego braku."""
from fastapi.testclient import TestClient

from app.main import app

c = TestClient(app)
DZIEN = "2026-11-21"


def _ubezp(login: str, dzien: str = DZIEN) -> dict:
    return c.get("/zus/ubezpieczenie", params={"na_dzien": dzien}, headers={"Authorization": f"sim-{login}"}).json()


def test_pracownica_ubezpieczona_obowiazkowo_fr02():
    u = _ubezp("anna")
    assert u["ubezpieczony_chorobowo"] is True
    assert u["tytuly"] == ["umowa_o_prace"]
    assert u["chorobowe_od"] == "2021-03-01" and u["chorobowe_dobrowolne"] is False
    assert u["platnik_ponad_20"] == "ponad_20"
    assert u["okresy"][0]["aktywny"] is True and u["okresy"][0]["tytul_opis"] == "Umowa o pracę"


def test_dzialalnosc_chorobowe_dobrowolne_fr02():
    u = _ubezp("marta")
    assert u["ubezpieczony_chorobowo"] is True and u["chorobowe_dobrowolne"] is True
    assert u["platnik_ponad_20"] is None  # przy działalności zawsze wypłaca ZUS


def test_zbieg_umowy_o_prace_i_zlecenia_fr02():
    u = _ubezp("piotr")
    assert u["tytuly"] == ["umowa_o_prace", "zlecenie"]
    assert u["chorobowe_dobrowolne"] is False  # obowiązkowe z umowy o pracę
    assert any("umowa zlecenia" in w for w in u["wyjasnienia"])


def test_brak_ubezpieczenia_po_ustaniu_umowy_art29_fr02():
    u = _ubezp("kasia")
    assert u["ubezpieczony_chorobowo"] is False
    assert u["tytuly"] == ["dzielo"] and u["chorobowe_od"] is None
    assert any("31.08.2026" in w for w in u["wyjasnienia"])
    assert any("art. 29" in w for w in u["wyjasnienia"])


def test_stan_na_dzien_w_trakcie_dawnej_umowy_fr02():
    u = _ubezp("kasia", "2026-05-01")
    assert u["ubezpieczony_chorobowo"] is True and u["tytuly"] == ["umowa_o_prace"]


def test_brak_tokenu_fr02():
    assert c.get("/zus/ubezpieczenie").status_code == 401


def test_pobranie_do_sprawy_zrodlo_zus_i_pierwszenstwo_uzytkownika_fr02():
    sid = c.post("/sprawy").json()["id"]
    c.post(f"/sprawy/{sid}/odpowiedzi", json=[{"pole": "etat", "wartosc": 0.5}])
    r = c.post(f"/zus/pobierz-do-sprawy/{sid}", headers={"Authorization": "sim-anna"}).json()
    assert "tytuly" in r["uzupelniono"] and r["pominieto"] == ["etat"]
    pola = c.get(f"/sprawy/{sid}").json()["osoby"][0]["pola"]
    assert pola["tytuly"]["zrodlo"] == "zus" and pola["tytuly"]["wartosc"] == ["umowa_o_prace"]
    assert pola["etat"] == {**pola["etat"], "wartosc": 0.5, "zrodlo": "uzytkownik"}


def test_pobranie_do_sprawy_osoba_bez_ubezpieczenia_fr02():
    sid = c.post("/sprawy").json()["id"]
    r = c.post(f"/zus/pobierz-do-sprawy/{sid}", headers={"Authorization": "sim-kasia"}).json()
    assert r["ubezpieczenie"]["ubezpieczony_chorobowo"] is False
    assert "chorobowe_od" not in r["uzupelniono"]
