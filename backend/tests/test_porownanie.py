"""Porównanie wyniku aplikacji z decyzją ZUS (tylko status), zabezpieczenie niskiej pewności odczytu
i prostowanie obróconych stron. Dane fikcyjne (rok 2026), jak w test_zasilek_chorobowy_ciaza.py."""
import copy
from datetime import date

import pymupdf
import pytest
from fastapi.testclient import TestClient

from app import config, porownanie
from app.domain.model import Kanal, Rola, Sprawa, WartoscPola, Wystawca
from app.domain.results import Status
from app.extraction import mapowanie, pdf, pipeline
from app.extraction.podzial import Fragment, podziel
from app.main import app
from app.params.store import get_params
from app.rules.wspolne import Kontekst
from app.rules.zasilek_chorobowy_ciaza import zasilek_chorobowy_ciaza
from app.storage import memory
from tests.test_mapowanie_odczytu import FIKSTURA, _pusty_pdf
from tests.test_zasilek_chorobowy_ciaza import ANNA, MIESIACE_WYSOKIE, OKRES_UOP, UOP_OD, _wiersze

c = TestClient(app)
P = get_params(date(2026, 3, 1))


# ---------- decyzja ZUS: proste rozpoznanie słowami kluczowymi ----------

@pytest.mark.parametrize("tekst, wynik", [
    ("W sprawie przyznano zasiłek chorobowy.", "przyznano"),
    ("Zasiłek chorobowy w okresie ciąży dla prowadzącej działalność gospodarczą. Zasiłek przyznano.", "przyznano"),
    ("Wypłacono zasiłek macierzyński.", "przyznano"),
    ("Nie przyznano zasiłku chorobowego.", "odmowa"),
    ("Odmówiono prawa do zasiłku macierzyńskiego.", "odmowa"),
    ("Zasiłek nie przysługuje.", "odmowa"),
    ("Pismo w sprawie uzupełnienia dokumentów.", None),
])
def test_rozpoznanie_rozstrzygniecia_decyzji_zus(tekst, wynik):
    assert porownanie.rozstrzygniecie(tekst) == wynik


def test_rozpoznanie_swiadczenia_z_decyzji_zus():
    assert porownanie.swiadczenie_z_tekstu("W sprawie przyznano zasiłek chorobowy.") == "zasilek_chorobowy_ciaza"
    assert porownanie.swiadczenie_z_tekstu("Wypłacono zasiłek macierzyński.") == "zasilek_macierzynski_urlop_macierzynski"
    assert porownanie.swiadczenie_z_tekstu("Przyznano świadczenie rehabilitacyjne.") is None


# ---------- od dokumentów do porównania (merge → reguła → porównanie) ----------

def _sprawa_anny(decyzja: str | None, z_ezla: bool = True) -> str:
    sid = c.post("/sprawy").json()["id"]
    s = memory.pobierz(sid)
    odczyt = {"pola": [{"pole": "zatrudnienie_od", "wartosc": UOP_OD, "strona": 1, "pewnosc": 0.9},
                       {"pole": "etat", "wartosc": "0.25", "strona": 1, "pewnosc": 0.9},
                       {"pole": "platnik_ponad_20", "wartosc": "do_20", "strona": 1, "pewnosc": 0.9}],
              "miesiace": [{**m, "strona": 3, "pewnosc": 0.9, "stale_pelna_kwota": 0} for m in MIESIACE_WYSOKIE]}
    if z_ezla:
        odczyt["ezla"] = [_wiersze("2026-03-08", "2026-05-27")]
        odczyt["wynagrodzenie_chorobowe_okres"] = [_wiersze("2026-02-18", "2026-03-22")]
    mapowanie.zapisz_dokument(s, "x.pdf", Fragment(typ="Z-3", strony=[1], osoby=["matka"]), odczyt)
    mapowanie.zapisz_dokument(s, "x.pdf", Fragment(typ="zrzut_systemu_ZUS", strony=[2], osoby=["matka"]), {
        "pola": [{"pole": "tytuly", "wartosc": "umowa_o_prace", "tytul": "umowa_o_prace", "strona": 1, "pewnosc": 0.9}],
        "okresy_ubezpieczenia": [{"kod_tytulu": "0110", "tytul": "umowa_o_prace", "platnik": None, "od": UOP_OD,
                                  "do": None, "chorobowe": None, "chorobowe_dobrowolne": None, "strona": 1,
                                  "pewnosc": 0.9}]})
    if decyzja:
        mapowanie.zapisz_dokument(s, "x.pdf", Fragment(typ="decyzja_ZUS", strony=[3]), {"tekst": decyzja, "strona": 1})
    memory.zapisz(s)
    assert c.post(f"/sprawy/{sid}/odpowiedzi", json=[{"pole": "sytuacja", "wartosc": ["ciaza"]},
                                                     {"pole": "data_urodzenia", "wartosc": "1994-05-12"}]).status_code == 200
    return sid


def test_porownanie_przyznano_i_przysluguje_zgodne():
    sid = _sprawa_anny("W sprawie przyznano zasiłek chorobowy.")
    p = c.get(f"/sprawy/{sid}/porownanie").json()
    assert p["zgodnosc"] == "zgodne" and p["decyzja_zus"]["rozstrzygniecie"] == "przyznano"
    assert p["wynik_aplikacji"] == {"swiadczenie": "zasilek_chorobowy_ciaza", "status": "przysluguje", "kwota": None}
    assert p["decyzja_zus"]["dokument_id"] and p["decyzja_zus"]["swiadczenie"] == "zasilek_chorobowy_ciaza"


def test_porownanie_odmowa_przy_wyniku_przysluguje_rozne():
    sid = _sprawa_anny("Odmówiono prawa do zasiłku chorobowego.")
    assert c.get(f"/sprawy/{sid}/porownanie").json()["zgodnosc"] == "rozne"


def test_porownanie_brak_danych_nie_do_porownania_i_brak_decyzji_404():
    sid = _sprawa_anny("W sprawie przyznano zasiłek chorobowy.", z_ezla=False)    # brak zwolnień → brak_danych
    p = c.get(f"/sprawy/{sid}/porownanie").json()
    assert p["zgodnosc"] == "nie_do_porownania" and p["wynik_aplikacji"]["status"] == "brak_danych"
    brak = c.get(f"/sprawy/{_sprawa_anny(None)}/porownanie")
    assert brak.status_code == 404 and "decyzji ZUS" in brak.json()["detail"]


# ---------- odmowa nigdy tylko z odczytu o pewności ≤ 0,6 ----------

def _ezla_przed_ubezpieczeniem():
    """Zwolnienie zaczyna się przed początkiem ubezpieczenia – bez zabezpieczenia byłoby „nie przysługuje”."""
    return {**ANNA, "okresy_ubezpieczenia": [{**OKRES_UOP, "od": "2026-04-01"}],
            "ezla": [{"od": "2026-03-08", "do": "2026-03-30", "kod": None}],
            "wynagrodzenie_chorobowe_okres": [{"od": "2026-03-01", "do": "2026-03-07", "kod": None}]}


def _wynik(pewnosc, kanal=Kanal.UPLOAD, zrodlo="ezla"):
    pochodzenie = {zrodlo: WartoscPola(wartosc=[], wystawca=Wystawca.PRACODAWCA, kanal=kanal, zrodlo_opis="x",
                                       pewnosc=pewnosc)}
    return zasilek_chorobowy_ciaza(Kontekst(fakty=_ezla_przed_ubezpieczeniem(), pochodzenie=pochodzenie,
                                            dzis=date(2026, 11, 22)), P)[0]


def test_odmowa_z_odczytu_o_pewnosci_rowno_prog_to_warunkowo_z_polem_do_potwierdzenia():
    w = _wynik(0.6)
    assert w.status == Status.WARUNKOWO and "ezla" in w.pola_do_potwierdzenia and w.orientacyjny
    assert w.warunki and w.podsumowanie.startswith("Do sprawdzenia") and w.powody      # powód odmowy zostaje


def test_odmowa_przy_pewnosci_powyzej_progu_albo_nie_z_odczytu_zostaje():
    assert _wynik(0.61).status == Status.NIE_PRZYSLUGUJE
    assert _wynik(0.3, kanal=Kanal.KREATOR).status == Status.NIE_PRZYSLUGUJE         # odpowiedź użytkownika ≠ odczyt AI
    assert _wynik(0.6, zrodlo="platnik_ponad_20").status == Status.NIE_PRZYSLUGUJE   # pole, od którego odmowa nie zależy


def test_odmowa_zasilku_macierzynskiego_z_niepewnego_odczytu_tez_warunkowo_art29():
    from tests.test_zasilek_macierzynski import OKRES_UOP as OKRES, PRACOWNICA, _licz
    f = {**PRACOWNICA, "tytuly": ["dzielo"], "data_porodu": "2026-10-15", "okresy_ubezpieczenia": [{**OKRES, "do": "2026-08-31"}]}
    niepewny = {"okresy_ubezpieczenia": WartoscPola(wartosc=[], wystawca=Wystawca.ZUS, kanal=Kanal.UPLOAD,
                                                    zrodlo_opis="x", pewnosc=0.5)}
    mac, rodz = _licz(f, pochodzenie=niepewny)
    assert mac.status == rodz.status == Status.WARUNKOWO and "okresy_ubezpieczenia" in mac.pola_do_potwierdzenia
    assert _licz(f)[0].status == Status.NIE_PRZYSLUGUJE                              # z rejestru ZUS – odmowa zostaje


# ---------- zrzut ZUS nie jest źródłem zwolnień (ezla), także ze starego cache ----------

def test_zrzut_zus_nie_zapisuje_ezla_nawet_gdy_jest_w_odczycie():
    s = Sprawa(id="sp")
    s.dodaj_osobe(Rola.MATKA, zalogowana=True)
    mapowanie.zapisz_dokument(s, "x.pdf", Fragment(typ="zrzut_systemu_ZUS", strony=[1]), {
        "ezla": [_wiersze("2024-04-04", "2024-04-24")],
        "okresy_ubezpieczenia": [{"kod_tytulu": "0110", "tytul": "umowa_o_prace", "platnik": None, "od": UOP_OD,
                                  "do": None, "chorobowe": None, "chorobowe_dobrowolne": None, "strona": 1,
                                  "pewnosc": 0.9}]})
    assert "ezla" not in s.osoby[0].pola and "okresy_ubezpieczenia" in s.osoby[0].pola


def test_brak_zwolnienia_prosi_o_wgranie_zwolnienia():
    f = {k: v for k, v in ANNA.items() if k not in ("ezla", "wynagrodzenie_chorobowe_okres")}
    w = zasilek_chorobowy_ciaza(Kontekst(fakty=f, dzis=date(2026, 11, 22)), P)[0]
    assert w.status == Status.BRAK_DANYCH and any("Wgraj zwolnienie" in x for x in w.co_zrobic)


# ---------- obrócone strony: prostowanie i render 200 DPI ----------

def test_renderuj_prostuje_strone_i_daje_png_200_dpi():
    dane = _pusty_pdf(2)                                         # A4: 595 × 842 pt
    pionowa, pozioma = pdf.renderuj(dane, [1, 2], {2: 90})
    assert pionowa[:4] == b"\x89PNG"
    p1, p2 = pymupdf.Pixmap(pionowa), pymupdf.Pixmap(pozioma)
    assert (p1.width, p1.height) == (1653, 2339)                 # 595 / 72 × 200, 842 / 72 × 200
    assert (p2.width, p2.height) == (2339, 1653)                 # obrót o 90°


def test_obrot_z_klasyfikacji_trafia_do_fragmentu_i_odczyt_idzie_z_obrazow(monkeypatch):
    monkeypatch.setattr(config, "CACHE_ODCZYTU", False)
    klas = copy.deepcopy(FIKSTURA["klasyfikacja"])
    for s in klas["strony"]:
        s["obrot"] = "270" if s["typ"] == "zrzut_systemu_ZUS" else "0"
    zrzut = next(f for f in podziel(klas["strony"]) if f.typ == "zrzut_systemu_ZUS")
    assert zrzut.obroty == {20: 270, 21: 270}
    wywolania = []

    def zapytaj(pdf_bytes, polecenie, schemat, etap, obrazy=None):
        wywolania.append((etap, len(obrazy or [])))
        dane = klas if etap == "klasyfikacja" else FIKSTURA["odczyt"][etap.split(":", 1)[1]]
        return {"dane": dane, "info": {"etap": etap, "model": "test", "czas_s": 0, "tokeny_wejscie": 0,
                                       "tokeny_wyjscie": 0}}

    s = Sprawa(id="sp")
    s.dodaj_osobe(Rola.MATKA, zalogowana=True)
    pipeline.przetworz_plik(s, "x.pdf", _pusty_pdf(FIKSTURA["liczba_stron"]), zapytaj=zapytaj)
    assert ("odczyt:zrzut_systemu_ZUS", 2) in wywolania              # dwa wyprostowane obrazy zamiast PDF
    assert all(n == 0 for etap, n in wywolania if etap != "odczyt:zrzut_systemu_ZUS")
