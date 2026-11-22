"""Oś czasu okresów zasiłku.

Wersja startowa: matka, urlop macierzyński + jej część urlopu rodzicielskiego (bez 9 tygodni drugiego rodzica),
wariant 81,5% albo 100% / 70%. Okres zaczyna się w dniu powstania prawa (start urlopu albo poród).
TODO (etap 4): drugi rodzic, łączenie z pracą (L3), części, ojcowski, przyjęcie dziecka, sytuacje szczególne.
"""
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.calculator import kwoty, wymiary

UWAGA_PODWYZSZENIE = ("Podwyższono do kwoty świadczenia rodzicielskiego (art. 31 ust. 3a ustawy zasiłkowej). "
                      "Sposób liczenia za niepełny miesiąc – do potwierdzenia w ZUS.")


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
    stawka_dzienna: str | None = None    # None – nie znamy podstawy wymiaru
    kwota_miesieczna: str | None = None
    kwota_za_okres: str | None = None
    podwyzszone: bool = False
    uwagi: list[str] = Field(default_factory=list)


class PlanMatki(BaseModel):
    okresy: list[Okres]
    powrot_do_pracy: date           # pierwszy dzień po ostatnim okresie
    ostrzezenia: list[str] = Field(default_factory=list)


def _okres(rodzaj: str, osoba: str, od: date, tygodnie: int, stawka: float,
           podstawa: Decimal | None, p: dict[str, Any]) -> Okres:
    dni = tygodnie * 7
    do = od + timedelta(days=dni - 1)
    okres = Okres(rodzaj=rodzaj, osoba=osoba, od=od, do=do, tygodnie=tygodnie, stawka=stawka_tekst(stawka))
    if podstawa is None:
        return okres
    mies, podwyzszone = kwoty.z_podwyzszeniem(kwoty.miesieczny(podstawa, stawka), p)
    if podwyzszone:
        okres.podwyzszone = True
        okres.uwagi.append(UWAGA_PODWYZSZENIE)
        okres.kwota_za_okres = str(kwoty.za_okres_podwyzszony(od, do, p))
        okres.stawka_dzienna = str(kwoty.zl(mies / p["dzielnik_dzienny"]))
    else:
        okres.kwota_za_okres = str(kwoty.za_okres(podstawa, stawka, dni, p))
        okres.stawka_dzienna = str(kwoty.dzienny(podstawa, stawka, p))
    okres.kwota_miesieczna = str(mies)
    return okres


def plan_matki(start: date, liczba_dzieci: int, za_zyciem: bool, wniosek_81_5: bool,
               podstawa: Decimal | None, p: dict[str, Any]) -> PlanMatki:
    """Urlop macierzyński od `start` (dzień powstania prawa), zaraz po nim część rodzicielskiego matki."""
    s = p["stawki"]
    tyg_mac = wymiary.urlop_macierzynski_tyg(liczba_dzieci, p)
    tyg_rodz = wymiary.urlop_rodzicielski_tyg(liczba_dzieci, za_zyciem, p)
    tyg_drugi = p["rodzicielski_nieprzenoszalne_tyg"]

    mac = _okres("macierzynski", "matka", start, tyg_mac,
                 s["jednolita"] if wniosek_81_5 else s["macierzynski"], podstawa, p)
    # 9 tygodni urlopu rodzicielskiego drugiego rodzica nie przechodzi na matkę (art. 182^1a § 1 KP)
    rodz = _okres("rodzicielski", "matka", mac.do + timedelta(days=1), tyg_rodz - tyg_drugi,
                  s["jednolita"] if wniosek_81_5 else s["rodzicielski"], podstawa, p)
    ostrzezenia = [f"{tyg_drugi} tygodni urlopu rodzicielskiego przysługuje wyłącznie drugiemu rodzicowi – "
                   f"zasiłek za nie zawsze wynosi {int(Decimal(str(s['nieprzenoszalna_drugi_rodzic'])) * 100)}%."]
    return PlanMatki(okresy=[mac, rodz], powrot_do_pracy=rodz.do + timedelta(days=1), ostrzezenia=ostrzezenia)
