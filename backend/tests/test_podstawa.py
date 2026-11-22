"""Podstawa wymiaru: okres obliczeniowy, miesiące z Z-3, minimum, art. 43, tryb uproszczony."""
from datetime import date
from decimal import Decimal

from app.calculator import podstawa as pw
from app.params.store import get_params

P = get_params(date(2026, 6, 1))


def _m(miesiac, stale="6000.00", przepr=20, obow=20, pelna=None, zmienne="0.00"):
    return {"miesiac": miesiac, "skladniki_stale": stale, "skladniki_zmienne": zmienne, "dni_przepracowane": przepr,
            "dni_obowiazujace": obow, "stale_pelna_kwota": pelna}


def test_okres_obliczeniowy_12_miesiecy_art36():
    okres = pw.okres_obliczeniowy(date(2026, 7, 10), date(2020, 1, 1), P)
    assert okres[0] == "2025-07" and okres[-1] == "2026-06" and len(okres) == 12


def test_podstawa_krotsze_ubezpieczenie_pelne_miesiace_art36():
    # ubezpieczenie od 15.03 – marzec niepełny, liczą się kwiecień–czerwiec
    assert pw.okres_obliczeniowy(date(2026, 7, 10), date(2026, 3, 15), P) == ["2026-04", "2026-05", "2026-06"]
    assert pw.okres_obliczeniowy(date(2026, 7, 10), date(2026, 3, 1), P)[0] == "2026-03"


def test_brak_pelnego_miesiaca_kwota_niepoliczona_art37():
    f = {"tytuly": ["umowa_o_prace"], "chorobowe_od": "2026-06-15", "srednie_wynagrodzenie_brutto": "6000.00"}
    u = pw.ustal_podstawe(f, date(2026, 7, 10), P)
    assert u.kwota is None and u.brakujace == ["miesiace"] and "art. 37" in u.uwagi[0]


def test_podstawa_z_miesiecy_tylko_z_okresu_art36():
    miesiace = [_m("2025-06", stale="20000.00")] + [_m(f"2025-{m:02d}") for m in range(7, 13)] + \
               [_m(f"2026-{m:02d}") for m in range(1, 7)]
    f = {"tytuly": ["umowa_o_prace"], "etat": "1.00", "chorobowe_od": "2020-01-01", "miesiace": miesiace}
    u = pw.ustal_podstawe(f, date(2026, 7, 10), P)
    # 6000 − 13,71% = 5177,40 (czerwiec 2025 spoza okresu pominięty)
    assert u.kwota == Decimal("5177.40") and u.orientacyjny is False and "miesiace" in u.pola


def test_miesiac_ponizej_polowy_pominiety_uzupelniony_art38():
    miesiace = [_m("2026-04"), _m("2026-05", stale="1500.00", przepr=5, obow=20),
                _m("2026-06", stale="3000.00", przepr=10, obow=20, pelna="6000.00", zmienne="500.00")]
    f = {"tytuly": ["umowa_o_prace"], "etat": "1.00", "chorobowe_od": "2026-04-01", "miesiace": miesiace}
    u = pw.ustal_podstawe(f, date(2026, 7, 10), P)
    # maj pominięty (5 z 20 dni); czerwiec: stałe uzupełnione do 6000, zmienne 500 / 10 × 20 = 1000
    # średnia (6000 + 7000) / 2 = 6500 → × 0,8629 = 5608,85
    assert u.kwota == Decimal("5608.85") and any("art. 36 ustawy" in x for x in u.uwagi)


def test_podstawa_minimalna_pelny_etat_art45():
    f = {"tytuly": ["umowa_o_prace"], "etat": "1.00", "miesiace": [_m("2026-06", stale="3000.00")]}
    assert pw.ustal_podstawe(f, date(2026, 7, 10), P).kwota == Decimal("4147.10")


def test_podstawa_niepelny_etat_minimum_proporcjonalne_art45():
    f = {"tytuly": ["umowa_o_prace"], "etat": "0.50", "miesiace": [_m("2026-06", stale="1500.00")]}
    # 4806 × 0,8629 × 0,5 = 2073,55 (1500 × 0,8629 = 1294,35 to mniej)
    assert pw.ustal_podstawe(f, date(2026, 7, 10), P).kwota == Decimal("2073.55")


def test_ta_sama_podstawa_po_przerwie_krotszej_niz_miesiac_art43():
    poprz = {"data_do": "2026-06-30", "podstawa": "7075.78"}
    assert pw.podstawa_z_poprzedniego(poprz, date(2026, 7, 31), P) == Decimal("7075.78")
    assert pw.podstawa_z_poprzedniego(poprz, date(2026, 8, 1), P) is None  # przerwa = pełny miesiąc
    f = {"tytuly": ["umowa_o_prace"], "srednie_wynagrodzenie_brutto": "6000.00", "poprzedni_zasilek": poprz}
    u = pw.ustal_podstawe(f, date(2026, 7, 10), P)
    assert u.kwota == Decimal("7075.78") and u.pola == ["poprzedni_zasilek"] and "art. 43" in u.uwagi[0]


def test_tryb_uproszczony_orientacyjny():
    f = {"tytuly": ["umowa_o_prace"], "etat": "1.00", "srednie_wynagrodzenie_brutto": "8200.00"}
    u = pw.ustal_podstawe(f, date(2026, 7, 10), P)
    assert u.kwota == Decimal("7075.78") and u.orientacyjny is True


def test_brak_wynagrodzenia_brakujace_pole():
    u = pw.ustal_podstawe({"tytuly": ["umowa_o_prace"]}, date(2026, 7, 10), P)
    assert u.kwota is None and u.brakujace == ["srednie_wynagrodzenie_brutto"]
    u = pw.ustal_podstawe({"tytuly": ["dzialalnosc"]}, date(2026, 7, 10), P)
    assert u.brakujace == ["podstawa_deklarowana_srednia"]


# ---------- art. 45 przy niepełnym etacie: parametr art45_niepelny_etat ----------

def test_minimalna_podstawa_pelny_etat_i_dwa_tryby_niepelnego_art45():
    pr, br = P, {**P, "art45_niepelny_etat": "brak"}
    assert pw.minimalna_podstawa(Decimal(1), pr) == pw.minimalna_podstawa(Decimal(1), br)       # pełny etat – pewne
    assert pw.minimalna_podstawa(Decimal("0.5"), pr) == pw.minimalna_podstawa(Decimal(1), pr) / 2
    assert pw.minimalna_podstawa(Decimal("0.5"), br) == 0


def test_niepelny_etat_minimum_zmienia_podstawe_wynik_orientacyjny_z_wariantem_art45():
    f = {"tytuly": ["umowa_o_prace"], "etat": "0.50", "miesiace": [_m("2026-06", stale="1500.00")]}
    u = pw.ustal_podstawe(f, date(2026, 7, 10), P)
    assert u.kwota == Decimal("2073.55") and u.orientacyjny is True and u.minimum_zmienia is True
    assert u.alternatywa == Decimal("1294.35") and any("art. 45" in x and "komentarzy" in x for x in u.uwagi)
    u2 = pw.ustal_podstawe(f, date(2026, 7, 10), {**P, "art45_niepelny_etat": "brak"})
    assert u2.kwota == Decimal("1294.35") and u2.alternatywa == Decimal("2073.55") and u2.orientacyjny is True


def test_niepelny_etat_minimum_nie_zmienia_podstawy_nie_ma_orientacyjnego_art45():
    f = {"tytuly": ["umowa_o_prace"], "etat": "0.50", "miesiace": [_m("2026-06", stale="9000.00")]}
    u = pw.ustal_podstawe(f, date(2026, 7, 10), P)
    assert u.orientacyjny is False and u.alternatywa is None and u.minimum_zmienia is False


def test_pelny_etat_minimum_pewne_bez_orientacyjnego_art45():
    f = {"tytuly": ["umowa_o_prace"], "etat": "1.00", "miesiace": [_m("2026-06", stale="3000.00")]}
    u = pw.ustal_podstawe(f, date(2026, 7, 10), P)
    assert u.kwota == Decimal("4147.10") and u.orientacyjny is False and u.alternatywa is None


def test_stawka_dzienna_zaokraglona_do_groszy_granica_pol_grosza_art36():
    from app.calculator import kwoty
    assert kwoty.dzienny(Decimal("30.15"), 1.0, P) == Decimal("1.01")        # 1,005 → 1,01 (w górę)
    assert kwoty.dzienny(Decimal("30.14"), 1.0, P) == Decimal("1.00")
    suma, grupy = kwoty.kwota_za_dni(Decimal("947.36"), [Decimal("0.8")] * 3 + [Decimal("1.0")] * 2, P)
    assert [(g.stawka, g.dni, g.dzienna) for g in grupy] == [(Decimal("1.0"), 2, Decimal("31.58")),
                                                              (Decimal("0.8"), 3, Decimal("25.26"))]
    assert suma == Decimal("31.58") * 2 + Decimal("25.26") * 3


# ---------- działalność: art. 48a – bez kwoty w sytuacjach, których nie umiemy policzyć ----------

def _dz(**zmiany):
    miesiace = [{"miesiac": f"2025-{m:02d}", "podstawa": "4000.00", "wakacje_skladkowe": False} for m in range(7, 13)] + \
               [{"miesiac": f"2026-{m:02d}", "podstawa": "4000.00", "wakacje_skladkowe": False} for m in range(1, 7)]
    return {"tytuly": ["dzialalnosc"], "chorobowe_od": "2020-01-01", "podstawa_deklarowana": miesiace,
            "podstawa_60_proc": True, **zmiany}


def test_dzialalnosc_prosta_srednia_z_12_miesiecy_art48():
    u = pw.ustal_podstawe(_dz(), date(2026, 7, 10), P)
    assert u.kwota == Decimal("3451.60") and u.orientacyjny is False


def test_dzialalnosc_limit_maksymalnej_podstawy_art48():
    miesiace = [{"miesiac": m["miesiac"], "podstawa": "30000.00", "wakacje_skladkowe": False}
                for m in _dz()["podstawa_deklarowana"]]
    assert pw.ustal_podstawe(_dz(podstawa_deklarowana=miesiace), date(2026, 7, 10), P).kwota == Decimal("20321.30")


def test_dzialalnosc_brak_miesiaca_w_tabeli_brakujace_art48():
    f = _dz()
    f["podstawa_deklarowana"] = f["podstawa_deklarowana"][1:]
    u = pw.ustal_podstawe(f, date(2026, 7, 10), P)
    assert u.kwota is None and u.brakujace == ["podstawa_deklarowana"] and "2025-07" in u.uwagi[0]


def test_dzialalnosc_art48a_tylko_ostrzezenie_bez_kwoty():
    assert pw.ustal_podstawe(_dz(podstawa_60_proc=False), date(2026, 7, 10), P).kwota is None
    assert any("art. 48a" in x for x in pw.ustal_podstawe(_dz(chorobowe_od="2026-02-01"), date(2026, 7, 10), P).uwagi)
    assert pw.ustal_podstawe(_dz(podstawa_60_proc=None), date(2026, 7, 10), P).brakujace == ["podstawa_60_proc"]
