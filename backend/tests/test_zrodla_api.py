"""Źródła danych przez API: lista, pobranie do sprawy (merge + konflikty), stan ubezpieczenia (docs/api.md 2.4, 2.7)."""
from fastapi.testclient import TestClient

from app.main import app

c = TestClient(app)


def _h(login: str) -> dict:
    return {"Authorization": f"sim-{login}"}


def _sprawa(login: str) -> str:
    return c.post("/sprawy", headers=_h(login)).json()["id"]


def _pobierz(sid: str, kod: str, login: str, **body):
    return c.post(f"/sprawy/{sid}/zrodla/{kod}/pobierz", headers=_h(login), json=body or None)


def _pytania(sid: str, login: str) -> dict[str, dict]:
    d = c.get(f"/sprawy/{sid}/dane", headers=_h(login)).json()
    return {p["id"]: p for s in d["sekcje"] for p in s["pytania"]}


def _aktywna(p: dict) -> dict | None:
    return next((w for w in p["wartosci"] if w["id"] == p["aktywna_wartosc_id"]), None)


def test_lista_zrodel():
    kody = {z["kod"]: z for z in c.get("/zrodla").json()}
    assert set(kody) == {"mobywatel", "zus_konto", "zus_platnik", "ezla"}
    assert kody["zus_konto"]["wystawca"] == "zus" and all(z["symulacja"] for z in kody.values())


def test_pobranie_zus_konto_wypelnia_dane():
    sid = _sprawa("anna")
    z = _pobierz(sid, "zus_konto", "anna").json()
    assert z["dodano"] >= 5 and "tytuly" in z["zmieniono_aktywne"] and z["nowe_konflikty"] == 0
    b1 = _aktywna(_pytania(sid, "anna")["B1"])
    assert b1["wartosc"] == ["umowa_o_prace"] and b1["wystawca"] == "zus" and b1["kanal"] == "zus_konto"
    assert b1["zrodlo_opis"] == "Konto w ZUS"


def test_ponowne_pobranie_nie_dubluje_wartosci():
    sid = _sprawa("anna")
    _pobierz(sid, "zus_konto", "anna")
    z = _pobierz(sid, "zus_konto", "anna").json()
    assert z["dodano"] == 0 and z["zmieniono_aktywne"] == []
    assert len(_pytania(sid, "anna")["B1"]["wartosci"]) == 1


def test_zus_wygrywa_z_wczesniejsza_odpowiedzia_uzytkownika_konflikt_widoczny():
    sid = _sprawa("anna")
    c.post(f"/sprawy/{sid}/odpowiedzi", headers=_h("anna"), json=[{"pole": "tytuly", "wartosc": ["zlecenie"]}])
    z = _pobierz(sid, "zus_konto", "anna").json()
    assert z["nowe_konflikty"] == 1 and z["liczniki"]["konflikty"] == 1
    b1 = _pytania(sid, "anna")["B1"]
    assert b1["konflikt"] is True and b1["wybor_aktywnej"] == "automatyczny"
    assert _aktywna(b1)["wystawca"] == "zus" and len(b1["wartosci"]) == 2  # odpowiedź użytkownika zostaje


def test_swiadoma_edycja_uzytkownika_to_reczny_wybor():
    sid = _sprawa("anna")
    _pobierz(sid, "zus_konto", "anna")
    c.post(f"/sprawy/{sid}/odpowiedzi", headers=_h("anna"), json=[{"pole": "etat", "wartosc": "0,5"}])
    b2 = _pytania(sid, "anna")["B2"]
    assert _aktywna(b2)["wartosc"] == "0.50" and b2["wybor_aktywnej"] == "uzytkownik" and b2["konflikt"] is True
    # Usunięcie odpowiedzi przywraca wartość z ZUS
    c.post(f"/sprawy/{sid}/odpowiedzi", headers=_h("anna"), json=[{"pole": "etat", "wartosc": None}])
    b2 = _pytania(sid, "anna")["B2"]
    assert _aktywna(b2)["wartosc"] == "1.00" and b2["wybor_aktywnej"] == "automatyczny"


def test_pobranie_wymaga_zalogowania_i_wlasciwej_osoby():
    anonim = c.post("/sprawy").json()["id"]
    assert c.post(f"/sprawy/{anonim}/zrodla/zus_konto/pobierz").status_code == 401
    assert _pobierz(anonim, "zus_konto", "anna").status_code == 403  # o1 nie jest zalogowana
    sid = _sprawa("anna")
    assert _pobierz(sid, "zus_konto", "anna", osoba="o2").status_code == 403  # dziecko
    assert _pobierz(sid, "nieznane", "anna").status_code == 404


def test_platnik_na_tytul_i_ezla():
    sid = _sprawa("piotr")
    _pobierz(sid, "zus_konto", "piotr")
    _pobierz(sid, "zus_platnik", "piotr")
    c1 = _pytania(sid, "piotr")["C1"]
    assert _aktywna(c1)["wartosc"] == {"umowa_o_prace": "do_20", "zlecenie": "do_20"}
    sid = _sprawa("anna")
    _pobierz(sid, "ezla", "anna")
    c.post(f"/sprawy/{sid}/odpowiedzi", headers=_h("anna"), json=[{"pole": "sytuacja", "wartosc": ["ciaza"]}])
    d1 = _pytania(sid, "anna")["D1"]
    assert _aktywna(d1)["wartosc"][0]["kod"] == "B" and d1["edytowalne"] is False


def test_ubezpieczenie_z_aktywnych_wartosci():
    sid = _sprawa("anna")
    assert c.get(f"/sprawy/{sid}/ubezpieczenie", headers=_h("anna")).status_code == 404
    _pobierz(sid, "zus_konto", "anna")
    u = c.get(f"/sprawy/{sid}/ubezpieczenie", params={"na_dzien": "2026-11-21"}, headers=_h("anna")).json()
    assert u["ubezpieczony_chorobowo"] is True and u["stan_na"] == "2026-11-21"
    ok = u["okresy"][0]
    assert ok["tytul_opis"] == "Umowa o pracę" and ok["platnik_ponad_20"] is True and ok["wymiar_etatu"] == "1.00"
    assert ok["aktywny"] is True and ok["zrodlo_opis"] == "Konto w ZUS"


def test_brak_ubezpieczenia_po_ustaniu_umowy_art29():
    sid = _sprawa("kasia")
    _pobierz(sid, "zus_konto", "kasia")
    u = c.get(f"/sprawy/{sid}/ubezpieczenie", params={"na_dzien": "2026-11-21"}, headers=_h("kasia")).json()
    assert u["ubezpieczony_chorobowo"] is False
    assert any("31.08.2026" in w for w in u["wyjasnienia"]) and any("art. 29" in w for w in u["wyjasnienia"])
