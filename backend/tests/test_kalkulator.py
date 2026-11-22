"""Testy reguł liczbowych. Każda reguła prawna = co najmniej jeden test z przepisem w nazwie."""
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.calculator import kwoty, timeline, wymiary
from app.calculator.podstawa import MiesiacWynagrodzenia, podstawa_dobrowolne, podstawa_pracownik
from app.params.store import get_params

P = get_params(date(2026, 6, 1))


@pytest.mark.parametrize("dzieci,tyg", [(1, 20), (2, 31), (3, 33), (4, 35), (5, 37), (7, 37)])
def test_urlop_macierzynski_art180(dzieci, tyg):
    assert wymiary.urlop_macierzynski_tyg(dzieci, P) == tyg


def test_urlop_rodzicielski_za_zyciem():
    assert wymiary.urlop_rodzicielski_tyg(1, False, P) == 41
    assert wymiary.urlop_rodzicielski_tyg(3, False, P) == 43
    assert wymiary.urlop_rodzicielski_tyg(1, True, P) == 65


def test_laczenie_z_praca_max_polowa_etatu():
    assert wymiary.wydluzenie_przy_laczeniu_tyg(10, 0.5, P) == 5
    with pytest.raises(ValueError):
        wymiary.wydluzenie_przy_laczeniu_tyg(10, 0.6, P)


def test_podstawa_pracownik_minus_skladki():
    m = [MiesiacWynagrodzenia(skladniki_stale=10000)] * 12
    assert podstawa_pracownik(m, etat=1, p=P) == Decimal("8629.00")


def test_podstawa_minimalna_pelny_etat_art45():
    m = [MiesiacWynagrodzenia(skladniki_stale=3000)]
    assert podstawa_pracownik(m, etat=1, p=P) == Decimal("4147.10")


def test_miesiac_ponizej_polowy_wylaczony_art38():
    m = [MiesiacWynagrodzenia(skladniki_stale=6000, dni_przepracowane=20, dni_obowiazujace=20),
         MiesiacWynagrodzenia(skladniki_stale=1000, dni_przepracowane=5, dni_obowiazujace=20)]
    assert podstawa_pracownik(m, etat=1, p=P) == Decimal("5177.40")


def test_limit_podstawy_dobrowolnej():
    assert podstawa_dobrowolne([30000], P) == Decimal("20321.30")


def test_podwyzszenie_do_swiadczenia_rodzicielskiego_art31_3a():
    kwota, podw = kwoty.z_podwyzszeniem(Decimal("800.00"), P)
    assert kwota == Decimal("1000.00") and podw


def test_rodzicielski_matki_bez_9_tyg_drugiego_rodzica_art182_1a():
    plan = timeline.plan_matki(date(2026, 3, 2), 1, False, True, Decimal("6000"), P)
    assert [o.rodzaj for o in plan.okresy] == ["macierzynski", "rodzicielski"]
    assert [o.tygodnie for o in plan.okresy] == [20, 32]
    assert plan.powrot_do_pracy == date(2026, 3, 2) + timedelta(weeks=20 + 32)
    assert "wyłącznie drugiemu rodzicowi" in plan.ostrzezenia[0] and "70%" in plan.ostrzezenia[0]


@pytest.mark.parametrize("dzieci,za_zyciem,tyg", [(1, False, 32), (2, False, 34), (1, True, 56), (2, True, 58)])
def test_rodzicielski_za_zyciem_i_dzieci_art182_1a(dzieci, za_zyciem, tyg):
    assert timeline.plan_matki(date(2026, 3, 2), dzieci, za_zyciem, False, None, P).okresy[1].tygodnie == tyg


def test_stawki_100_70_art31():
    o = timeline.plan_matki(date(2026, 3, 2), 1, False, False, Decimal("6000.00"), P).okresy
    assert [x.stawka for x in o] == ["1.00", "0.70"]
    assert o[0].kwota_miesieczna == "6000.00" and o[1].kwota_miesieczna == "4200.00"


def test_81_5_za_caly_okres_art31_ust3():
    o = timeline.plan_matki(date(2026, 3, 2), 1, False, True, Decimal("6000.00"), P).okresy
    assert {x.stawka for x in o} == {"0.815"} and o[0].kwota_miesieczna == "4890.00"


def test_kwoty_co_do_grosza_art36():
    # Podstawa 7075,78 zł (8200 zł brutto − 13,71%).
    # Macierzyński 100%: stawka dzienna 7075,78 / 30 = 235,859… → 235,86 zł; 20 tyg. = 140 dni × 235,86 = 33 020,40 zł
    # Rodzicielski 70%: 7075,78 × 0,7 = 4953,046 → miesięcznie 4953,05 zł; dziennie 4953,046 / 30 = 165,1015… → 165,10 zł;
    #                   32 tyg. = 224 dni × 165,10 = 36 982,40 zł
    o = timeline.plan_matki(date(2026, 7, 10), 1, False, False, Decimal("7075.78"), P).okresy
    assert (o[0].stawka_dzienna, o[0].kwota_za_okres) == ("235.86", "33020.40")
    assert (o[1].kwota_miesieczna, o[1].stawka_dzienna, o[1].kwota_za_okres) == ("4953.05", "165.10", "36982.40")


def test_podwyzszenie_za_okres_art31_ust3c():
    # 1000 zł za pełny miesiąc, za niepełny proporcjonalnie: 15.01–31.03.2026 → 17/31 × 1000 + 1000 + 1000
    assert kwoty.za_okres_podwyzszony(date(2026, 1, 15), date(2026, 3, 31), P) == Decimal("2548.39")
    o = timeline.plan_matki(date(2026, 1, 15), 1, False, False, Decimal("1000.00"), P).okresy[1]  # 70% = 700 zł
    assert o.podwyzszone and o.kwota_miesieczna == "1000.00" and "do potwierdzenia" in o.uwagi[0]


@pytest.mark.parametrize("stawka,tekst", [(1.0, "1.00"), (0.7, "0.70"), (0.815, "0.815")])
def test_stawka_jako_tekst(stawka, tekst):
    assert timeline.stawka_tekst(stawka) == tekst


@pytest.mark.parametrize("wniosek,wynik", [("2026-07-31", True), ("2026-08-01", False), ("2026-06-20", True), (None, False)])
def test_scenariusz_domyslny_wniosek_81_5_w_terminie_art31(wniosek, wynik):
    from app.calculator import scenariusz
    fakty = {"data_porodu": "2026-07-10", "wniosek_81_5_data": wniosek}
    assert scenariusz.domyslny(fakty, P) == {"wniosek_81_5": wynik}
