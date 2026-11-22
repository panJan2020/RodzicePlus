"""Oś czasu okresów zasiłku.

Wersja startowa: matka, urlop macierzyński + rodzicielski, wariant 81,5% albo 100/70,
opcjonalnie 9 tygodni drugiego rodzica na końcu. TODO: łączenie z pracą (L3), części,
ojcowski, przyjęcie dziecka, sytuacje szczególne (sekcje H, I, K).
"""
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.calculator import kwoty, wymiary


def stawka_tekst(stawka: float | str | Decimal) -> str:
    """Stawka jako tekst z co najmniej dwoma miejscami po przecinku: "1.00", "0.70", "0.815"."""
    d = Decimal(str(stawka))
    return str(d.quantize(Decimal("0.01")) if d.as_tuple().exponent > -2 else d)


class Okres(BaseModel):
    rodzaj: str          # "macierzynski", "rodzicielski", "ojcowski", ...
    osoba: str           # rola: "matka" / "ojciec"
    od: date
    do: date
    tygodnie: int
    stawka: str
    kwota_miesieczna: str
    kwota_za_okres: str
    uwagi: list[str] = Field(default_factory=list)


def _okres(rodzaj: str, osoba: str, od: date, tygodnie: int, stawka: float,
           podstawa: Decimal, p: dict[str, Any]) -> tuple[Okres, date]:
    dni = tygodnie * 7
    do = od + timedelta(days=dni - 1)
    mies = kwoty.miesieczny(podstawa, stawka)
    mies, podwyzszone = kwoty.z_podwyzszeniem(mies, p)
    uwagi = ["Podwyższono do kwoty świadczenia rodzicielskiego (art. 31 ust. 3a ustawy zasiłkowej)"] if podwyzszone else []
    # TODO: przy podwyższeniu kwota za okres liczona proporcjonalnie do miesięcy (art. 31 ust. 3c)
    okres = Okres(rodzaj=rodzaj, osoba=osoba, od=od, do=do, tygodnie=tygodnie, stawka=stawka_tekst(stawka),
                  kwota_miesieczna=str(mies), kwota_za_okres=str(kwoty.za_okres(podstawa, stawka, dni, p)), uwagi=uwagi)
    return okres, do + timedelta(days=1)


def plan_matki(data_porodu: date, liczba_dzieci: int, za_zyciem: bool, wniosek_81_5: bool,
               podstawa: Decimal, p: dict[str, Any], drugi_rodzic_bierze_9_tyg: bool = False) -> list[Okres]:
    s = p["stawki"]
    okresy: list[Okres] = []

    tyg_mac = wymiary.urlop_macierzynski_tyg(liczba_dzieci, p)
    tyg_rodz = wymiary.urlop_rodzicielski_tyg(liczba_dzieci, za_zyciem, p)
    tyg_drugi = p["rodzicielski_nieprzenoszalne_tyg"]
    tyg_rodz_matki = tyg_rodz - tyg_drugi  # 9 tyg. drugiego rodzica nie przechodzi na matkę

    o, nastepny = _okres("macierzynski", "matka", data_porodu, tyg_mac,
                         s["jednolita"] if wniosek_81_5 else s["macierzynski"], podstawa, p)
    okresy.append(o)
    o, nastepny = _okres("rodzicielski", "matka", nastepny, tyg_rodz_matki,
                         s["jednolita"] if wniosek_81_5 else s["rodzicielski"], podstawa, p)
    okresy.append(o)
    if drugi_rodzic_bierze_9_tyg:
        # Podstawa drugiego rodzica jest inna – tu tylko szkic osi czasu.
        o, _ = _okres("rodzicielski", "ojciec", nastepny, tyg_drugi,
                      s["nieprzenoszalna_drugi_rodzic"], podstawa, p)
        o.uwagi.append("Kwota orientacyjna – policz z podstawą wymiaru drugiego rodzica")
        okresy.append(o)
    return okresy
