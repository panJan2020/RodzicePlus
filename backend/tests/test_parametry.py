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
    p, ostrzezenie = parametry_na_dzien(date(2025, 3, 23))
    assert ostrzezenie.startswith("Brak parametrów prawnych na rok 2025") and "01.01.2026" in ostrzezenie
    assert p["obowiazuje_od"] == "2026-01-01"                       # najbliższa wersja, ale z widocznym ostrzeżeniem


def test_parametry_przed_najwczesniejsza_wersja_ostrzezenie_z_data():
    from datetime import date
    from app.params.store import parametry_na_dzien
    assert "na rok 2020" in parametry_na_dzien(date(2020, 3, 23))[1]
