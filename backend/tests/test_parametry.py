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
