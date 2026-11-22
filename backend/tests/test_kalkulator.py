"""Testy reguł liczbowych. Każda reguła prawna = co najmniej jeden test z przepisem w nazwie."""
from datetime import date
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
    assert podstawa_pracownik(m, pelny_etat=True, p=P) == Decimal("8629.00")


def test_podstawa_minimalna_pelny_etat_art45():
    m = [MiesiacWynagrodzenia(skladniki_stale=3000)]
    assert podstawa_pracownik(m, pelny_etat=True, p=P) == Decimal("4147.10")


def test_miesiac_ponizej_polowy_wylaczony_art38():
    m = [MiesiacWynagrodzenia(skladniki_stale=6000, dni_przepracowane=20, dni_obowiazujace=20),
         MiesiacWynagrodzenia(skladniki_stale=1000, dni_przepracowane=5, dni_obowiazujace=20)]
    assert podstawa_pracownik(m, pelny_etat=False, p=P) == Decimal("5177.40")


def test_limit_podstawy_dobrowolnej():
    assert podstawa_dobrowolne([30000], P) == Decimal("20321.30")


def test_podwyzszenie_do_swiadczenia_rodzicielskiego_art31_3a():
    kwota, podw = kwoty.z_podwyzszeniem(Decimal("800.00"), P)
    assert kwota == Decimal("1000.00") and podw


def test_plan_matki_81_5_pomija_9_tyg_drugiego_rodzica():
    okresy = timeline.plan_matki(date(2026, 3, 2), 1, False, True, Decimal("6000"), P)
    assert [o.rodzaj for o in okresy] == ["macierzynski", "rodzicielski"]
    assert (okresy[1].do - okresy[0].od).days + 1 == (20 + 32) * 7
    assert all(o.stawka == "0.815" for o in okresy)


@pytest.mark.parametrize("stawka,tekst", [(1.0, "1.00"), (0.7, "0.70"), (0.815, "0.815")])
def test_stawka_jako_tekst(stawka, tekst):
    assert timeline.stawka_tekst(stawka) == tekst


@pytest.mark.parametrize("wniosek,wynik", [("2026-07-31", True), ("2026-08-01", False), ("2026-06-20", True), (None, False)])
def test_scenariusz_domyslny_wniosek_81_5_w_terminie_art31(wniosek, wynik):
    from app.calculator import scenariusz
    fakty = {"data_porodu": "2026-07-10", "wniosek_81_5_data": wniosek}
    assert scenariusz.domyslny(fakty, P) == {"wniosek_81_5": wynik}
