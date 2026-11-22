"""Parametry prawne potrzebne regule zasiłku macierzyńskiego (docs/pytania_kalkulator.md, sekcja Y)."""
from datetime import date

from app.params.store import get_params


def test_parametry_podstawy_i_przedluzenia_umowy_art36_art38_art43_art177kp():
    p = get_params(date(2026, 6, 1))
    assert p["okres_obliczeniowy_mies"] == 12
    assert p["art38_min_czesc_czasu_pracy"] == 0.5
    assert p["art43_przerwa_mies"] == 1
    assert p["ciaza_tyg"] == 40 and p["przedluzenie_umowy_po_miesiacu_ciazy"] == 3
    assert "swiadczenie_rodzicielskie" in p["uwagi"]


# ---------- wersja parametrów po dacie prawa; brak pliku na rok → ostrzeżenie, nie cichy fallback ----------

def test_parametry_na_dzien_w_roku_z_plikiem_bez_ostrzezenia():
    from datetime import date
    from app.params.store import parametry_na_dzien
    p, ostrzezenie = parametry_na_dzien(date(2026, 5, 1))
    assert p["obowiazuje_od"] == "2026-01-01" and ostrzezenie is None


def test_parametry_na_dzien_w_roku_bez_pliku_daje_ostrzezenie():
    from datetime import date
    from app.params.store import parametry_na_dzien
    p, ostrzezenie = parametry_na_dzien(date(2027, 3, 23))
    assert ostrzezenie.startswith("Brak parametrów prawnych na rok 2027") and "01.01.2026" in ostrzezenie
    assert p["obowiazuje_od"] == "2026-01-01"                       # najbliższa wersja, ale z widocznym ostrzeżeniem


def test_parametry_przed_najwczesniejsza_wersja_ostrzezenie_z_data():
    from datetime import date
    from app.params.store import parametry_na_dzien
    assert "na rok 2020" in parametry_na_dzien(date(2020, 3, 23))[1]


# ---------- pliki parametrów 2024–2026: płaca minimalna po dacie, źródła, art. 45 ----------

def test_placa_minimalna_po_dacie_prawa_2024_2025_2026():
    from datetime import date
    from app.params.store import parametry_na_dzien
    oczekiwane = {date(2024, 1, 1): 4242, date(2024, 6, 30): 4242, date(2024, 7, 1): 4300, date(2024, 12, 31): 4300,
                  date(2025, 1, 1): 4666, date(2025, 12, 31): 4666, date(2026, 1, 1): 4806}
    for dzien, kwota in oczekiwane.items():
        p, ostrzezenie = parametry_na_dzien(dzien)
        assert p["minimalne_wynagrodzenie"] == kwota and ostrzezenie is None, dzien


def test_kazdy_plik_ma_zrodla_statusy_i_parametr_art45():
    from app.params.store import _load_all
    for p in _load_all():
        z = p["_zrodla"]
        assert p["art45_niepelny_etat"] in ("proporcjonalnie", "brak"), p["_plik"]
        for klucz in ("minimalne_wynagrodzenie", "max_podstawa_dobrowolne_brutto", "art45_niepelny_etat", "pozostale"):
            assert z[klucz]["status"] in ("zweryfikowane", "do_weryfikacji") and z[klucz]["podstawa_prawna"], (p["_plik"], klucz)
        assert z["minimalne_wynagrodzenie"]["wartosc"] == p["minimalne_wynagrodzenie"], p["_plik"]
        if p["obowiazuje_od"] < "2026":
            assert z["minimalne_wynagrodzenie"]["status"] == "zweryfikowane" and z["minimalne_wynagrodzenie"]["zrodlo"]
            assert z["max_podstawa_dobrowolne_brutto"]["status"] == "do_weryfikacji"
        assert z["art45_niepelny_etat"]["status"] == "do_weryfikacji"                    # pytanie 15 do mentorów


def test_save_params_nie_gubi_kluczy_z_podkreslnikiem(tmp_path, monkeypatch):
    import json
    from app.params import store
    monkeypatch.setattr(store, "PARAMS_DIR", tmp_path)
    nazwa = store.save_params({"obowiazuje_od": "2030-01-01", "x": 1, "_plik": "params_2026.json",
                               "_zrodla": {"x": {"status": "do_weryfikacji"}}})
    zapisane = json.loads((tmp_path / nazwa).read_text(encoding="utf-8"))
    assert zapisane["_zrodla"] == {"x": {"status": "do_weryfikacji"}} and "_plik" not in zapisane


def test_kalkulator_podstawy_importuje_sie_bez_cyklu_importow():
    import subprocess
    import sys
    wynik = subprocess.run([sys.executable, "-c", "import app.calculator.podstawa, app.calculator.kwoty"],
                           capture_output=True, text=True)
    assert wynik.returncode == 0, wynik.stderr[-300:]
