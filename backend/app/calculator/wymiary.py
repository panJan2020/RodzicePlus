"""Wymiary urlopów (w tygodniach) – czyste funkcje, wartości z parametrów."""
from typing import Any


def _klucz(liczba_dzieci: int, max_klucz: int) -> str:
    return str(min(max(liczba_dzieci, 1), max_klucz))


def urlop_macierzynski_tyg(liczba_dzieci: int, p: dict[str, Any]) -> int:
    tabela = p["urlop_macierzynski_tyg"]
    return tabela[_klucz(liczba_dzieci, max(map(int, tabela)))]


def urlop_rodzicielski_tyg(liczba_dzieci: int, za_zyciem: bool, p: dict[str, Any]) -> int:
    tabela = p["urlop_rodzicielski_za_zyciem_tyg" if za_zyciem else "urlop_rodzicielski_tyg"]
    return tabela[_klucz(liczba_dzieci, 2)]


def limit_przy_laczeniu_tyg(liczba_dzieci: int, za_zyciem: bool, p: dict[str, Any]) -> int:
    tabela = p["laczenie_limit_za_zyciem_tyg" if za_zyciem else "laczenie_limit_tyg"]
    return tabela[_klucz(liczba_dzieci, 2)]


def wydluzenie_przy_laczeniu_tyg(tygodnie_laczenia: float, wymiar_pracy: float, p: dict[str, Any]) -> float:
    """Art. 182^1f §2 KP: wydłużenie = liczba tygodni łączenia × wymiar pracy."""
    if wymiar_pracy > p["laczenie_max_wymiar"]:
        raise ValueError("Wymiar pracy w czasie urlopu rodzicielskiego nie może przekraczać 1/2 etatu")
    return tygodnie_laczenia * wymiar_pracy


def uzupelniajacy_tyg(tydzien_ciazy: int, masa_g: int, dni_w_szpitalu: int, p: dict[str, Any]) -> int:
    """Uproszczony wymiar uzupełniającego urlopu macierzyńskiego (art. 180^2 KP).

    dni_w_szpitalu = suma dni pobytu liczona w oknie właściwym dla przypadku
    (dla donoszonych: od 5. dnia do końca 8. tyg.). Niepełny tydzień w górę.
    TODO: liczenie okna z listy hospitalizacji (pole hospitalizacje[]) + warunek 2 kolejnych dni.
    """
    u = p["uzupelniajacy"]
    if tydzien_ciazy < u["prog_tydzien_wczesny"] or masa_g <= u["prog_masa_g"]:
        limit = u["limit_tyg_wczesny"]
    else:
        limit = u["limit_tyg_pozostale"]
    tygodnie = -(-dni_w_szpitalu // 7)  # zaokrąglenie w górę
    return min(tygodnie, limit)
