"""Wyniki świadczeń i kalkulator dla sprawy (docs/api.md 2.8–2.9).

Na razie: jedna reguła (zasiłek macierzyński) i scenariusz domyślny budowany z faktów.
Scenariusze, porównanie i POST /kalkulator – etap 4.
"""
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException

from app.api.wspolne import login_opcjonalny, osoba_lub_404, sprawa_lub_404
from app.calculator import podstawa as pw
from app.calculator import scenariusz, timeline
from app.domain.model import ROLE_RODZICA, Rola, Sprawa
from app.domain.results import (BrakujacePole, OkresKalkulatora, OsobaKalkulatora, WynikKalkulatora,
                                WynikSwiadczenia)
from app.params.store import get_params
from app.questions import engine
from app.rules import eligibility, wyliczone

router = APIRouter(prefix="/sprawy/{sprawa_id}", tags=["świadczenia i kalkulator"])


def _brakujace(s: Sprawa, osoba, pola: list[str]) -> list[BrakujacePole]:
    """Nazwy pól → pytania, na które da się odpowiedzieć teraz (zablokowane → pytanie nadrzędne)."""
    wynik = []
    for id_ in engine.pytania_do_uzupelnienia(s, osoba, pola):
        q = engine.pytanie(id_)
        if q:
            wynik.append(BrakujacePole(pytanie_id=id_, tresc=q["tresc"], gdzie_znalezc=q.get("gdzie_znalezc")))
    return wynik


@router.get("/swiadczenia", response_model=list[WynikSwiadczenia])
def swiadczenia(sprawa_id: str, login: str | None = Depends(login_opcjonalny)) -> list[WynikSwiadczenia]:
    """Wyniki wszystkich reguł dla każdego rodzica w sprawie."""
    s = sprawa_lub_404(sprawa_id, login)
    p = get_params()
    wyniki = []
    for o in (x for x in s.osoby if x.rola in ROLE_RODZICA):
        fakty = engine.fakty(s, o)
        for regula in eligibility.REGULY.values():
            r = regula(fakty, p)
            wyniki.append(WynikSwiadczenia(
                **r.model_dump(exclude={"brakujace"}), osoba_id=o.id,
                brakujace_pola=_brakujace(s, o, r.brakujace), wersja_parametrow=p["obowiazuje_od"]))
    return wyniki


def _podstawa(f: dict, data_prawa, p: dict) -> Decimal:
    u = pw.ustal_podstawe(f, data_prawa, p)
    if u.kwota is None:
        raise HTTPException(422, "Aby policzyć kwotę, podaj średnie wynagrodzenie albo podstawę składek "
                                 "(pytania O4s, Q1s).")
    return u.kwota


@router.get("/kalkulator", response_model=WynikKalkulatora)
def kalkulator(sprawa_id: str, osoba: str | None = None,
               login: str | None = Depends(login_opcjonalny)) -> WynikKalkulatora:
    s = sprawa_lub_404(sprawa_id, login)
    matka = osoba_lub_404(s, osoba)
    f = engine.fakty(s, matka)
    dziecko = next((o for o in s.osoby if o.rola == Rola.DZIECKO), None)
    fd = engine.fakty(s, dziecko) if dziecko else {}

    start = wyliczone.data_prawa(f)
    if start is None:
        raise HTTPException(422, "Aby policzyć zasiłek, podaj datę porodu albo przewidywaną datę porodu "
                                 "(pytania G1, G2).")
    p = get_params(start)
    podstawa = _podstawa(f, start, p)
    wybory = scenariusz.domyslny(f, p)

    plan = timeline.plan_matki(start=start, liczba_dzieci=int(f.get("liczba_dzieci") or 1),
                               za_zyciem=bool(fd.get("za_zyciem", False)), wniosek_81_5=wybory["wniosek_81_5"],
                               podstawa=podstawa, p=p)
    okresy = plan.okresy
    wynik_okresy = [OkresKalkulatora(**o.model_dump(include=set(OkresKalkulatora.model_fields) - {"osoba_id"}),
                                     osoba_id=matka.id) for o in okresy]
    suma = sum((Decimal(o.kwota_za_okres) for o in okresy), Decimal("0"))
    return WynikKalkulatora(scenariusz_id=scenariusz.SCENARIUSZ_DOMYSLNY, wersja_parametrow=p["obowiazuje_od"],
                            osoby=[OsobaKalkulatora(osoba_id=matka.id, podstawa_wymiaru=str(podstawa),
                                                    suma=str(suma))],
                            okresy=wynik_okresy, suma=str(suma))
