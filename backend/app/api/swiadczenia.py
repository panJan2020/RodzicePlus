"""Wyniki świadczeń i kalkulator dla sprawy (docs/api.md 2.8–2.9).

Na razie: reguła zasiłku macierzyńskiego matki i scenariusz domyślny budowany z faktów.
Scenariusze, porównanie i POST /kalkulator – etap 4. Parametry: wersja obowiązująca w dniu powstania prawa.
"""
from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.api.wspolne import login_opcjonalny, osoba_lub_404, sprawa_lub_404
from app.calculator import podstawa as pw
from app.calculator import scenariusz, timeline
from app.domain.model import ROLE_RODZICA, Osoba, Rola, Sprawa
from app.domain.results import (BrakujacePole, OkresKalkulatora, OsobaKalkulatora, WynikKalkulatora,
                                WynikSwiadczenia)
from app.merge.scalanie import prog_pewnosci
from app.params.store import get_params
from app.questions import engine
from app.rules import DLA_ROL, REGULY, wyliczone
from app.rules.wspolne import Kontekst

router = APIRouter(prefix="/sprawy/{sprawa_id}", tags=["świadczenia i kalkulator"])


def _brakujace(s: Sprawa, osoba: Osoba, pola: list[str]) -> list[BrakujacePole]:
    """Nazwy pól → pytania, na które da się odpowiedzieć teraz (zablokowane → pytanie nadrzędne)."""
    wynik = []
    for id_ in engine.pytania_do_uzupelnienia(s, osoba, pola):
        q = engine.pytanie(id_)
        if q:
            wynik.append(BrakujacePole(pytanie_id=id_, tresc=q["tresc"], gdzie_znalezc=q.get("gdzie_znalezc")))
    return wynik


def _do_potwierdzenia(pola: list[str]) -> list[BrakujacePole]:
    """Nazwy pól → pytania z katalogu (bez względu na stan – wartość już jest, trzeba ją tylko potwierdzić)."""
    wynik = []
    for pole in pola:
        q = engine.pytanie_dla_pola(pole)
        if q:
            wynik.append(BrakujacePole(pytanie_id=q["id"], tresc=q["tresc"], gdzie_znalezc=q.get("gdzie_znalezc")))
    return wynik


def _kontekst(s: Sprawa, o: Osoba) -> tuple[Kontekst, dict[str, Any]]:
    """Kontekst reguły (fakty, dziecko, scenariusz domyślny) i parametry z dnia powstania prawa."""
    f, pochodzenie = engine.fakty_z_pochodzeniem(s, o)
    dziecko = next((x for x in s.osoby if x.rola == Rola.DZIECKO), None)
    fd = engine.fakty(s, dziecko) if dziecko else {}
    wybory = scenariusz.domyslny(f, get_params(wyliczone.data_prawa(f)))
    p = get_params(wyliczone.data_prawa(f, wybory))
    return Kontekst(fakty=f, fakty_dziecka=fd, wybory=wybory, pochodzenie=pochodzenie, dzis=date.today(),
                    prog_pewnosci=prog_pewnosci()), p


@router.get("/swiadczenia", response_model=list[WynikSwiadczenia])
def swiadczenia(sprawa_id: str, login: str | None = Depends(login_opcjonalny)) -> list[WynikSwiadczenia]:
    """Wyniki reguł dla każdego rodzica w sprawie (reguła tylko dla ról, których dotyczy)."""
    s = sprawa_lub_404(sprawa_id, login)
    wyniki = []
    for o in (x for x in s.osoby if x.rola in ROLE_RODZICA):
        k, p = _kontekst(s, o)
        for kod, regula in REGULY.items():
            if o.rola.value not in DLA_ROL[kod]:
                continue
            for r in regula(k, p):
                wyniki.append(WynikSwiadczenia(
                    **r.model_dump(exclude={"brakujace", "pola_do_potwierdzenia"}), osoba_id=o.id,
                    scenariusz_id=scenariusz.SCENARIUSZ_DOMYSLNY, brakujace_pola=_brakujace(s, o, r.brakujace),
                    pola_do_potwierdzenia=_do_potwierdzenia(r.pola_do_potwierdzenia),
                    wersja_parametrow=p["obowiazuje_od"]))
    return wyniki


@router.get("/kalkulator", response_model=WynikKalkulatora)
def kalkulator(sprawa_id: str, osoba: str | None = None,
               login: str | None = Depends(login_opcjonalny)) -> WynikKalkulatora:
    """Okresy i kwoty matki w scenariuszu domyślnym. Bez daty porodu albo podstawy wymiaru – 422."""
    s = sprawa_lub_404(sprawa_id, login)
    matka = osoba_lub_404(s, osoba)
    k, p = _kontekst(s, matka)
    f = k.fakty
    start = wyliczone.data_prawa(f, k.wybory)
    if start is None:
        raise HTTPException(422, "Aby policzyć zasiłek, podaj datę porodu albo przewidywaną datę porodu "
                                 "(pytania G1, G2).")
    ustalenie = pw.ustal_podstawe(f, start, p)
    if ustalenie.kwota is None:
        powod = " ".join(ustalenie.uwagi)
        raise HTTPException(422, (powod + " " if powod else "") + "Aby policzyć kwotę, podaj średnie "
                                 "wynagrodzenie albo podstawę składek (pytania O4s, Q1s).")

    plan = timeline.plan_matki(start=start, liczba_dzieci=int(f.get("liczba_dzieci") or 1),
                               za_zyciem=bool(k.fakty_dziecka.get("za_zyciem", False)),
                               wniosek_81_5=bool(k.wybory.get("wniosek_81_5")), podstawa=ustalenie.kwota, p=p)
    okresy = [OkresKalkulatora(**o.model_dump(include=set(OkresKalkulatora.model_fields) - {"osoba_id"}),
                               osoba_id=matka.id) for o in plan.okresy]
    suma = sum((Decimal(o.kwota_za_okres) for o in okresy), Decimal("0"))
    return WynikKalkulatora(
        scenariusz_id=scenariusz.SCENARIUSZ_DOMYSLNY, wersja_parametrow=p["obowiazuje_od"],
        osoby=[OsobaKalkulatora(osoba_id=matka.id, podstawa_wymiaru=str(ustalenie.kwota), suma=str(suma),
                                powrot_do_pracy=plan.powrot_do_pracy)],
        okresy=okresy, suma=str(suma), orientacyjny=ustalenie.orientacyjny,
        ostrzezenia=ustalenie.uwagi + plan.ostrzezenia)
