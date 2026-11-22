"""Drzewo pytań („Moje dane”, kreator): stany pytań, osoby w sprawie, zachowanie danych, odpowiedzi użytkownika."""
from fastapi.testclient import TestClient

from app import merge
from app.domain.model import Kanal, Rola, Sprawa, WartoscPola, Wystawca
from app.main import app
from app.questions import engine
from app.questions.engine import StatusPytania as S

c = TestClient(app)


def _sprawa(**pola):
    """Sprawa z matką (o1, wnioskodawca) i dzieckiem (o2); pola matki jako odpowiedzi użytkownika."""
    s = Sprawa(id="sp")
    o = s.dodaj_osobe(Rola.MATKA)
    s.dodaj_osobe(Rola.DZIECKO)
    for k, v in pola.items():
        merge.dodaj(s, o, k, WartoscPola(wartosc=v, wystawca=Wystawca.UZYTKOWNIK, kanal=Kanal.KREATOR,
                                         zrodlo_opis="Twoja odpowiedź"), prog=0.6)
    return s, o


def _stany(s, osoba=None) -> dict[str, engine.Pytanie]:
    return {p.id: p for p in engine.drzewo(s, osoba or s.osoby[0])}


def _nowa() -> str:
    return c.post("/sprawy").json()["id"]


def _odpowiedz(sid: str, osoba: str | None = None, **pola):
    return c.post(f"/sprawy/{sid}/odpowiedzi",
                  json=[{"osoba": osoba, "pole": k, "wartosc": v} for k, v in pola.items()])


def _pytania_api(sid: str, osoba: str = "o1") -> dict[str, dict]:
    d = c.get(f"/sprawy/{sid}/dane", params={"osoba": osoba}).json()
    return {p["id"]: p for s in d["sekcje"] for p in s["pytania"]}


def _aktywna(p: dict):
    return next((w["wartosc"] for w in p["wartosci"] if w["id"] == p["aktywna_wartosc_id"]), None)


# ---------- katalog ----------

def test_katalog_spojny():
    ids = [p["id"] for p in engine.katalog()]
    pola = [p["pole"] for p in engine.katalog()]
    assert len(ids) == len(set(ids)) and len(pola) == len(set(pola))
    for p in engine.katalog():
        assert p["sekcja"] in engine.sekcje(), p["id"]
        assert p["rodzaj"] in ("fakt", "plan", "wyliczone"), f"{p['id']}: pola „wybór” należą do scenariusza"
        assert p["osoba"] and set(p["osoba"]) <= {"rodzic", "matka", "ojciec", "dziecko", "wnioskodawca"}, p["id"]
        assert p["zrodla"], p["id"]
        if p["rodzaj"] == "plan":
            assert p["zrodla"] == ["kreator"], f"{p['id']}: plan tylko od użytkownika"
        for w in p.get("pokaz_gdy", []):
            assert engine.pytanie_dla_pola(w["pole"]), f"{p['id']}: warunek na nieznanym polu {w['pole']}"
        if p["typ"] in ("wybor", "wielokrotny"):
            assert all(o["etykieta"] for o in p["opcje"]), p["id"]


def test_pola_wyboru_nie_sa_w_katalogu():
    pola = {p["pole"] for p in engine.katalog()}
    assert not pola & {"wariant", "rezygnacja_od", "rodz_w_1_roku"}


# ---------- stany ----------

def test_pytania_bez_warunkow_aktywne():
    st = _stany(*_sprawa()[:1])
    assert st["A1"].status == S.AKTYWNE and st["B1"].status == S.AKTYWNE


def test_zablokowane_czekaja_na_pytanie_nadrzedne():
    st = _stany(_sprawa()[0])
    assert st["G2"].status == S.ZABLOKOWANE and st["G2"].czeka_na == ["A1"]
    assert st["B2"].status == S.ZABLOKOWANE and st["B2"].czeka_na == ["B1"]
    # Łańcuch: B3a zależy od B3, a B3 od B1 → wskazujemy B1 (na nie da się odpowiedzieć teraz).
    assert st["B3a"].status == S.ZABLOKOWANE and st["B3a"].czeka_na == ["B1"]


def test_wykluczone_po_odpowiedzi():
    st = _stany(_sprawa(tytuly=["umowa_o_prace"], sytuacja=["urodzenie"])[0])
    assert st["Q1s"].status == S.WYKLUCZONE  # działalność nie dotyczy pracownicy
    assert st["B4a"].status == S.WYKLUCZONE  # dobrowolne chorobowe – tylko zlecenie/działalność
    assert st["G1"].status == S.WYKLUCZONE   # przewidywana data porodu – tylko w ciąży
    assert st["O4s"].status == S.AKTYWNE and st["G2"].status == S.AKTYWNE


def test_wykluczenie_przechodzi_na_pytania_zalezne():
    st = _stany(_sprawa(tytuly=["dzialalnosc"])[0])
    assert st["B3"].status == S.WYKLUCZONE and st["B3a"].status == S.WYKLUCZONE


def test_operator_rowne_true():
    assert _stany(_sprawa(sytuacja=["ciaza"], po_ustaniu=True)[0])["D5"].status == S.AKTYWNE
    assert _stany(_sprawa(sytuacja=["ciaza"], po_ustaniu=False)[0])["D5"].status == S.WYKLUCZONE


def test_pusta_lista_to_brak_odpowiedzi():
    st = _stany(_sprawa(sytuacja=[])[0])
    assert st["A1"].aktywna_wartosc_id is None and st["G2"].status == S.ZABLOKOWANE


def test_niepewny_odczyt_do_sprawdzenia():
    s, o = _sprawa()
    w = merge.dodaj(s, o, "tytuly", WartoscPola(wartosc=["umowa_o_prace"], wystawca=Wystawca.PRACODAWCA,
                                                kanal=Kanal.UPLOAD, zrodlo_opis="Z-3, str. 2", dokument_id="d1",
                                                strona=2, pewnosc=0.4), prog=0.6)
    assert _stany(s)["B1"].wartosci[0].do_sprawdzenia is True
    w.pewnosc = 0.9
    assert _stany(s)["B1"].wartosci[0].do_sprawdzenia is False


# ---------- osoby w sprawie ----------

def test_pytania_dziecka_tylko_u_dziecka_a_warunki_od_wnioskodawcy():
    s, _ = _sprawa(sytuacja=["urodzenie"])
    matka, dziecko = _stany(s), _stany(s, s.osoby[1])
    assert "G4" not in matka and "A1" not in dziecko and "B1" not in dziecko
    assert dziecko["G4"].status == S.AKTYWNE  # warunek A1 czytany od matki (wnioskodawcy)
    assert dziecko["A4"].status == S.AKTYWNE  # data urodzenia – rodzic i dziecko


def test_pytania_tylko_dla_matki():
    s, _ = _sprawa(sytuacja=["ciaza"])
    ojciec = s.dodaj_osobe(Rola.OJCIEC)
    assert "G1" in _stany(s) and "G1" not in _stany(s, ojciec)
    assert "A1" not in _stany(s, ojciec)  # A1 tylko wnioskodawca


def test_pole_na_tytul_ma_klucze_z_tytulow():
    st = _stany(_sprawa(tytuly=["umowa_o_prace", "zlecenie", "dzielo"])[0])
    assert [k.wartosc for k in st["C1"].klucze] == ["umowa_o_prace", "zlecenie"]
    assert [k.wartosc for k in st["B4"].klucze] == ["zlecenie"]


def test_klucze_obejmuja_tytuly_z_aktywnej_wartosci():
    s, o = _sprawa(tytuly=["umowa_o_prace", "zlecenie"])
    merge.dodaj(s, o, "chorobowe", WartoscPola(wartosc={"umowa_o_prace": True, "zlecenie": False},
                                               wystawca=Wystawca.ZUS, kanal=Kanal.ZUS_KONTO,
                                               zrodlo_opis="Konto w ZUS"), prog=0.6)
    assert [k.etykieta for k in _stany(s)["B4"].klucze] == ["Umowa o pracę", "Umowa zlecenia lub agencyjna"]


# ---------- API: sprawa i osoby ----------

def test_nowa_sprawa_anonimowa_z_dzieckiem():
    s = c.post("/sprawy").json()
    assert s["zdarzenie"] == "urodzenie" and s["ma_decyzje_zus"] is False
    assert s["osoby"] == [{"id": "o1", "rola": "matka", "imie": None, "zalogowana": False},
                          {"id": "o2", "rola": "dziecko", "imie": "Dziecko", "zalogowana": False}]
    assert set(s["liczniki"]) == {"konflikty", "niespojnosci", "brakujace_pola", "dokumenty"}


def test_sprawa_zalogowanej_osoby_tylko_z_jej_tokenem():
    s = c.post("/sprawy", headers={"Authorization": "sim-anna"}, json={"nazwa": "Ciąża 2026"}).json()
    assert s["nazwa"] == "Ciąża 2026" and s["osoby"][0] == {"id": "o1", "rola": "matka", "imie": "Anna",
                                                            "zalogowana": True}
    assert c.get(f"/sprawy/{s['id']}").status_code == 403
    assert c.get(f"/sprawy/{s['id']}", headers={"Authorization": "sim-marta"}).status_code == 403
    assert c.get(f"/sprawy/{s['id']}", headers={"Authorization": "sim-anna"}).status_code == 200
    assert s["id"] in [x["id"] for x in c.get("/sprawy", headers={"Authorization": "sim-anna"}).json()]
    assert c.get("/sprawy").status_code == 401


def test_dodanie_i_usuniecie_osoby():
    sid = _nowa()
    o = c.post(f"/sprawy/{sid}/osoby", json={"rola": "ojciec", "imie": "Tomasz"}).json()
    assert o == {"id": "o3", "rola": "ojciec", "imie": "Tomasz", "zalogowana": False}
    assert c.delete(f"/sprawy/{sid}/osoby/o1").status_code == 400  # wnioskodawcy nie usuwamy
    assert c.delete(f"/sprawy/{sid}/osoby/o3").status_code == 204
    assert [x["id"] for x in c.get(f"/sprawy/{sid}").json()["osoby"]] == ["o1", "o2"]


# ---------- API: odpowiedzi ----------

def test_odpowiedz_zwraca_zmiane_danych():
    sid = _nowa()
    z = _odpowiedz(sid, sytuacja=["ciaza"]).json()
    assert z["dodano"] == 1 and z["zmieniono_aktywne"] == ["sytuacja"] and z["wyniki_nieaktualne"] is True
    assert z["nowe_konflikty"] == 0 and z["liczniki"]["brakujace_pola"] > 0


def test_kwoty_i_ulamki_jako_tekst_liczby_calkowite_jako_liczby():
    sid = _nowa()
    _odpowiedz(sid, tytuly=["umowa_o_prace"], etat=0.5, srednie_wynagrodzenie_brutto="8 200,5", sytuacja=["ciaza"],
               liczba_dzieci=2)
    q = _pytania_api(sid)
    assert _aktywna(q["B2"]) == "0.50" and _aktywna(q["O4s"]) == "8200.50" and _aktywna(q["G3"]) == 2


def test_bledne_odpowiedzi():
    sid = _nowa()
    assert _odpowiedz(sid, etat="pół").status_code == 422
    assert _odpowiedz(sid, rola="kosmita").status_code == 422
    assert _odpowiedz(sid, nieznane_pole=1).status_code == 400
    assert _odpowiedz(sid, okresy_ubezpieczenia=[]).status_code == 400   # tylko podgląd
    assert _odpowiedz(sid, "o2", tytuly=["umowa_o_prace"]).status_code == 400  # nie dotyczy dziecka


def test_odpowiedz_dla_dziecka():
    sid = _nowa()
    _odpowiedz(sid, sytuacja=["urodzenie"])
    assert _odpowiedz(sid, "o2", za_zyciem=True).status_code == 200
    assert _aktywna(_pytania_api(sid, "o2")["G4"]) is True


def test_a2_aktualizuje_role_osoby():
    sid = _nowa()
    _odpowiedz(sid, rola="ojciec")
    assert c.get(f"/sprawy/{sid}").json()["osoby"][0]["rola"] == "ojciec"
    assert "G1" not in _pytania_api(sid)  # pytania tylko dla matki znikają


def test_zmiana_odpowiedzi_nie_kasuje_danych_zaleznych():
    sid = _nowa()
    _odpowiedz(sid, tytuly=["dzialalnosc"], podstawa_deklarowana_srednia=5000)
    assert _pytania_api(sid)["Q1s"]["status"] == "aktywne"

    _odpowiedz(sid, tytuly=["umowa_o_prace"])
    q = _pytania_api(sid)["Q1s"]
    assert q["status"] == "wykluczone" and _aktywna(q) == "5000.00"  # dalej w profilu

    _odpowiedz(sid, tytuly=["dzialalnosc"])
    q = _pytania_api(sid)["Q1s"]
    assert q["status"] == "aktywne" and _aktywna(q) == "5000.00"  # wraca z wartością


def test_fakty_pomijaja_wykluczone():
    s, o = _sprawa(tytuly=["umowa_o_prace"], podstawa_deklarowana_srednia="5000.00",
                   srednie_wynagrodzenie_brutto="8000.00")
    f = engine.fakty(s, o)
    assert "podstawa_deklarowana_srednia" not in f and f["srednie_wynagrodzenie_brutto"] == "8000.00"
    assert o.wartosc("podstawa_deklarowana_srednia") == "5000.00"  # oryginał nietknięty


def test_kalkulator_nie_uzywa_wartosci_wykluczonych():
    sid = _nowa()
    # Najpierw działalność z podstawą, potem zmiana na umowę o pracę bez wynagrodzenia.
    _odpowiedz(sid, sytuacja=["urodzenie"], tytuly=["dzialalnosc"], podstawa_deklarowana_srednia=5000,
               data_porodu="2026-07-10", liczba_dzieci=1)
    assert c.get(f"/sprawy/{sid}/kalkulator").status_code == 200
    _odpowiedz(sid, tytuly=["umowa_o_prace"])
    r = c.get(f"/sprawy/{sid}/kalkulator")
    assert r.status_code == 422 and "O4s" in r.json()["detail"]


def test_wyczyszczenie_odpowiedzi():
    sid = _nowa()
    _odpowiedz(sid, tytuly=["umowa_o_prace"])
    _odpowiedz(sid, tytuly=None)
    q = _pytania_api(sid)["B1"]
    assert q["aktywna_wartosc_id"] is None and q["wartosci"] == []


# ---------- API: /dane i kreator ----------

def test_dane_sekcje_i_postep():
    sid = _nowa()
    _odpowiedz(sid, sytuacja=["ciaza"], rola="matka")
    d = c.get(f"/sprawy/{sid}/dane").json()
    assert d["osoba"] == {"id": "o1", "rola": "matka", "imie": None}
    a = next(s for s in d["sekcje"] if s["id"] == "A")
    assert a["tytul"] == "Sytuacja i rola"
    assert a["postep"]["odpowiedziane"] == 2 and a["postep"]["aktywne"] == 4  # A1, A2 z 4 aktywnych
    w = a["pytania"][0]["wartosci"][0]
    assert w["wystawca"] == "uzytkownik" and w["kanal"] == "kreator" and w["zrodlo_opis"] == "Twoja odpowiedź"
    assert a["pytania"][0]["rodzaj"] == "fakt" and a["pytania"][0]["edytowalne"] is True


def test_dane_nieznana_osoba_lub_sprawa():
    sid = _nowa()
    assert c.get(f"/sprawy/{sid}/dane?osoba=o9").status_code == 404
    assert c.get("/sprawy/nieistnieje/dane").status_code == 404


def test_kreator_pyta_tylko_o_aktywne_bez_odpowiedzi():
    sid = _nowa()
    ids = [p["id"] for p in c.get(f"/sprawy/{sid}/pytania").json()]
    assert "A1" in ids and "G2" not in ids and "B5a" not in ids  # G2 zablokowane, B5a tylko podgląd
    _odpowiedz(sid, sytuacja=["urodzenie"])
    ids = [p["id"] for p in c.get(f"/sprawy/{sid}/pytania").json()]
    assert "A1" not in ids and "G2" in ids
    assert "G4" in [p["id"] for p in c.get(f"/sprawy/{sid}/pytania?osoba=o2").json()]


def test_plan_ustania_s3_tylko_w_ciazy_i_data_po_tak_art29():
    sid = _nowa()
    _odpowiedz(sid, sytuacja=["ciaza"], tytuly=["umowa_o_prace"])
    ids = [p["id"] for p in c.get(f"/sprawy/{sid}/pytania").json()]
    assert "S3" in ids and "S3a" not in ids
    _odpowiedz(sid, plan_ustania=True)
    assert "S3a" in [p["id"] for p in c.get(f"/sprawy/{sid}/pytania").json()]
    q = _pytania_api(sid)
    assert q["S3"]["rodzaj"] == "plan"
    assert q["O4"]["typ"] == "miesiace" and q["O4"]["edytowalne"] is False  # O4 tylko podgląd (Z-3)
    assert q["O2"]["typ"] == "zasilek" and q["O2"]["edytowalne"] is False
