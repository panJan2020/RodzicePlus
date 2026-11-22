"""Drzewo pytań (zakładka „Dane”, FR-03): stany pytań, zachowanie danych, brakujące pytania jako ID."""
from fastapi.testclient import TestClient

from app.domain.profile import FieldValue, Osoba, Zrodlo
from app.main import app
from app.questions import engine
from app.questions.engine import StatusPytania as S

c = TestClient(app)


def _osoba(**pola) -> Osoba:
    return Osoba(pola={k: FieldValue(wartosc=v, zrodlo=Zrodlo.UZYTKOWNIK) for k, v in pola.items()})


def _stany(osoba: Osoba) -> dict[str, engine.PytanieWDrzewie]:
    return {p.id: p for p in engine.drzewo(osoba)}


def _odpowiedz(sid: str, **pola) -> None:
    c.post(f"/sprawy/{sid}/odpowiedzi", json=[{"pole": k, "wartosc": v} for k, v in pola.items()])


def _pytania_api(sid: str) -> dict[str, dict]:
    d = c.get(f"/sprawy/{sid}/dane").json()
    return {p["id"]: p for s in d["sekcje"] for p in s["pytania"]}


# ---------- katalog ----------

def test_katalog_spojny():
    ids = [p["id"] for p in engine.katalog()]
    pola = [p["pole"] for p in engine.katalog()]
    assert len(ids) == len(set(ids)) and len(pola) == len(set(pola))
    for p in engine.katalog():
        assert p["sekcja"] in engine.sekcje(), p["id"]
        for w in p.get("pokaz_gdy", []):
            assert engine.pytanie_dla_pola(w["pole"]), f"{p['id']}: warunek na nieznanym polu {w['pole']}"
        if p["typ"] in ("wybor", "wielokrotny"):
            assert all(o["etykieta"] for o in p["opcje"]), p["id"]


# ---------- stany ----------

def test_pytania_bez_warunkow_aktywne():
    st = _stany(Osoba())
    assert st["A1"].status == S.AKTYWNE and st["B1"].status == S.AKTYWNE


def test_zablokowane_czekaja_na_pytanie_nadrzedne():
    st = _stany(Osoba())
    assert st["G2"].status == S.ZABLOKOWANE and st["G2"].czeka_na == ["A1"]
    assert st["B2"].status == S.ZABLOKOWANE and st["B2"].czeka_na == ["B1"]
    # Łańcuch: B3a zależy od B3, a B3 od B1 → wskazujemy B1 (na nie da się odpowiedzieć teraz).
    assert st["B3a"].status == S.ZABLOKOWANE and st["B3a"].czeka_na == ["B1"]


def test_wykluczone_po_odpowiedzi():
    st = _stany(_osoba(tytuly=["umowa_o_prace"], sytuacja=["urodzenie"]))
    assert st["Q1s"].status == S.WYKLUCZONE  # działalność nie dotyczy pracownicy
    assert st["B4"].status == S.WYKLUCZONE   # dobrowolne chorobowe – tylko zlecenie/działalność
    assert st["G1"].status == S.WYKLUCZONE   # przewidywana data porodu – tylko w ciąży
    assert st["O4s"].status == S.AKTYWNE and st["G2"].status == S.AKTYWNE


def test_wykluczenie_przechodzi_na_pytania_zalezne():
    st = _stany(_osoba(tytuly=["dzialalnosc"]))
    assert st["B3"].status == S.WYKLUCZONE and st["B3a"].status == S.WYKLUCZONE


def test_operator_rowne_true():
    assert _stany(_osoba(sytuacja=["ciaza"], po_ustaniu=True))["D5"].status == S.AKTYWNE
    assert _stany(_osoba(sytuacja=["ciaza"], po_ustaniu=False))["D5"].status == S.WYKLUCZONE


def test_pusta_lista_to_brak_odpowiedzi():
    st = _stany(_osoba(sytuacja=[]))
    assert st["A1"].odpowiedziane is False and st["G2"].status == S.ZABLOKOWANE


def test_niepewny_odczyt_do_sprawdzenia():
    o = Osoba(pola={"tytuly": FieldValue(wartosc=["umowa_o_prace"], zrodlo=Zrodlo.DOKUMENT,
                                          dokument="Z-3", strona=2, pewnosc=0.4)})
    assert _stany(o)["B1"].do_sprawdzenia is True
    o.pola["tytuly"].pewnosc = 0.9
    assert _stany(o)["B1"].do_sprawdzenia is False


# ---------- zachowanie danych po zmianie odpowiedzi ----------

def test_zmiana_odpowiedzi_nie_kasuje_danych_zaleznych():
    sid = c.post("/sprawy").json()["id"]
    _odpowiedz(sid, tytuly=["dzialalnosc"], podstawa_deklarowana_srednia=5000)
    assert _pytania_api(sid)["Q1s"]["status"] == "aktywne"

    _odpowiedz(sid, tytuly=["umowa_o_prace"])
    q = _pytania_api(sid)["Q1s"]
    assert q["status"] == "wykluczone" and q["wartosc"]["wartosc"] == 5000  # dalej w profilu

    _odpowiedz(sid, tytuly=["dzialalnosc"])
    q = _pytania_api(sid)["Q1s"]
    assert q["status"] == "aktywne" and q["wartosc"]["wartosc"] == 5000  # wraca z wartością


def test_aktywne_pola_pomijaja_wykluczone():
    o = _osoba(tytuly=["umowa_o_prace"], podstawa_deklarowana_srednia=5000, srednie_wynagrodzenie_brutto=8000)
    a = engine.aktywne_pola(o)
    assert a.get("podstawa_deklarowana_srednia") is None and a.get("srednie_wynagrodzenie_brutto") == 8000
    assert o.get("podstawa_deklarowana_srednia") == 5000  # oryginał nietknięty


def test_kalkulator_nie_uzywa_wartosci_wykluczonych():
    sid = c.post("/sprawy").json()["id"]
    # Najpierw działalność z podstawą, potem zmiana na umowę o pracę bez wynagrodzenia.
    _odpowiedz(sid, sytuacja=["urodzenie"], tytuly=["dzialalnosc"], podstawa_deklarowana_srednia=5000,
               data_porodu="2026-07-10", liczba_dzieci=1)
    assert c.get(f"/sprawy/{sid}/kalkulator").status_code == 200
    _odpowiedz(sid, tytuly=["umowa_o_prace"])
    r = c.get(f"/sprawy/{sid}/kalkulator")
    assert r.status_code == 422 and "O4s" in r.json()["detail"]


def test_wyczyszczenie_odpowiedzi():
    sid = c.post("/sprawy").json()["id"]
    _odpowiedz(sid, tytuly=["umowa_o_prace"])
    _odpowiedz(sid, tytuly=None)
    assert _pytania_api(sid)["B1"]["odpowiedziane"] is False


# ---------- endpoint /dane ----------

def test_dane_sekcje_i_postep():
    sid = c.post("/sprawy").json()["id"]
    _odpowiedz(sid, sytuacja=["ciaza"], rola="matka")
    d = c.get(f"/sprawy/{sid}/dane").json()
    a = next(s for s in d["sekcje"] if s["id"] == "A")
    assert a["tytul"] == "Sytuacja i rola"
    assert a["postep"]["odpowiedziane"] == 2 and a["postep"]["aktywne"] == 4  # A1, A2 z 4 aktywnych
    assert d["postep"]["aktywne"] >= a["postep"]["aktywne"]
    assert a["pytania"][0]["wartosc"]["zrodlo"] == "uzytkownik"


def test_dane_zrodlo_zus():
    sid = c.post("/sprawy").json()["id"]
    c.post(f"/zus/pobierz-do-sprawy/{sid}", headers={"Authorization": "sim-anna"})
    b1 = _pytania_api(sid)["B1"]
    assert b1["wartosc"]["zrodlo"] == "zus" and b1["odpowiedziane"] is True


def test_dane_nieznana_osoba_lub_sprawa():
    sid = c.post("/sprawy").json()["id"]
    assert c.get(f"/sprawy/{sid}/dane?osoba=5").status_code == 404
    assert c.get("/sprawy/nieistnieje/dane").status_code == 404


def test_kreator_pyta_tylko_o_aktywne_bez_odpowiedzi():
    sid = c.post("/sprawy").json()["id"]
    ids = [p["id"] for p in c.get(f"/sprawy/{sid}/pytania").json()]
    assert "A1" in ids and "G2" not in ids  # G2 zablokowane
    _odpowiedz(sid, sytuacja=["urodzenie"])
    ids = [p["id"] for p in c.get(f"/sprawy/{sid}/pytania").json()]
    assert "A1" not in ids and "G2" in ids


# ---------- brakujące pola jako ID pytań (art. 29 – zasiłek macierzyński) ----------

def test_brakujace_pytania_jako_id_art29():
    sid = c.post("/sprawy").json()["id"]
    w = c.get(f"/sprawy/{sid}/uprawnienia").json()[0]
    assert w["status"] == "brak_danych"
    # B1 aktywne → "B1"; B7 zablokowane przez A1 → wskazujemy "A1".
    assert w["brakujace_pola"] == ["B1", "A1"]
    assert w["brakujace_pytania"][0] == {"id": "B1", "tresc": "Na jakiej podstawie pracujesz?",
                                         "gdzie_znalezc": None}


def test_brakujace_pytania_po_odpowiedzi_na_a1_art29():
    sid = c.post("/sprawy").json()["id"]
    _odpowiedz(sid, sytuacja=["urodzenie"], tytuly=["zlecenie"])
    w = c.get(f"/sprawy/{sid}/uprawnienia").json()[0]
    assert w["brakujace_pola"] == ["B7", "B4"]
    assert all(p["tresc"] for p in w["brakujace_pytania"])
