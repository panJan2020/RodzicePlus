"""Sprawy i osoby, dane osoby (drzewo pytań), kreator, odpowiedzi użytkownika (docs/api.md 2.2–2.3). Upload dokumentów – api/dokumenty.py.

Sprawa może być anonimowa (bez logowania) – wtedy o1 ma `zalogowana: false`. Sprawa zalogowanej osoby
jest dostępna tylko z jej tokenem.
"""
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app import merge, sources
from app.api.wspolne import (Liczniki, Obserwator, ZmianaDanych, liczniki, login_opcjonalny, osoba_lub_404,
                             sprawa_lub_404)
from app.domain.model import Kanal, Rola, Sprawa, WartoscPola, Wystawca
from app.questions import engine
from app.storage import memory

router = APIRouter(prefix="/sprawy", tags=["sprawy"])

ZDARZENIA = ("urodzenie", "przysposobienie", "rodzina_zastepcza")


class OsobaApi(BaseModel):
    id: str
    rola: Rola
    imie: str | None = None
    zalogowana: bool


class SprawaSkrot(BaseModel):
    id: str
    nazwa: str
    zdarzenie: str
    utworzono: datetime


class SprawaApi(SprawaSkrot):
    osoby: list[OsobaApi]
    liczniki: dict[str, int]
    ma_decyzje_zus: bool


class NowaSprawa(BaseModel):
    zdarzenie: str = "urodzenie"
    nazwa: str = "Moja sprawa"


class NowaOsoba(BaseModel):
    rola: Rola
    imie: str | None = None


class Odpowiedz(BaseModel):
    osoba: str | None = None  # osoba_id; brak = wnioskodawca
    pole: str
    wartosc: Any


def _sprawa_api(s: Sprawa) -> SprawaApi:
    lic: Liczniki = liczniki(s)
    return SprawaApi(id=s.id, nazwa=s.nazwa, zdarzenie=s.zdarzenie, utworzono=s.utworzono,
                     osoby=[OsobaApi(id=o.id, rola=o.rola, imie=o.imie, zalogowana=o.zalogowana) for o in s.osoby],
                     liczniki={**lic.model_dump(), "dokumenty": len(s.dokumenty)},
                     ma_decyzje_zus=s.oczekiwany_wynik is not None)


@router.get("", response_model=list[SprawaSkrot])
def lista(login: str | None = Depends(login_opcjonalny)) -> list[SprawaSkrot]:
    if not login:
        raise HTTPException(401, "Zaloguj się, aby zobaczyć swoje sprawy.")
    return [SprawaSkrot(id=s.id, nazwa=s.nazwa, zdarzenie=s.zdarzenie, utworzono=s.utworzono)
            for s in memory.lista(login)]


@router.post("", response_model=SprawaApi)
def utworz(dane: NowaSprawa | None = None, login: str | None = Depends(login_opcjonalny)) -> SprawaApi:
    """Nowa sprawa. Zalogowana osoba (albo anonimowa o1) jest dodawana automatycznie;
    przy zdarzeniu „urodzenie” od razu dodajemy osobę `dziecko` (o2)."""
    dane = dane or NowaSprawa()
    if dane.zdarzenie not in ZDARZENIA:
        raise HTTPException(422, "Nieznany rodzaj sprawy.")
    s = memory.nowa_sprawa(dane.zdarzenie, dane.nazwa, wlasciciel=login)
    konto = sources.konto(login) if login else None
    s.dodaj_osobe(Rola.MATKA, konto["imie"] if konto else None, zalogowana=bool(login), login=login)
    if dane.zdarzenie == "urodzenie":
        s.dodaj_osobe(Rola.DZIECKO, "Dziecko")
    memory.zapisz(s)
    return _sprawa_api(s)


@router.get("/{sprawa_id}", response_model=SprawaApi)
def pobierz(sprawa_id: str, login: str | None = Depends(login_opcjonalny)) -> SprawaApi:
    return _sprawa_api(sprawa_lub_404(sprawa_id, login))


@router.post("/{sprawa_id}/osoby", response_model=OsobaApi)
def dodaj_osobe(sprawa_id: str, dane: NowaOsoba, login: str | None = Depends(login_opcjonalny)) -> OsobaApi:
    s = sprawa_lub_404(sprawa_id, login)
    if dane.rola == Rola.MATKA:
        raise HTTPException(422, "Można dodać ojca, drugiego rodzica albo dziecko.")
    o = s.dodaj_osobe(dane.rola, dane.imie)
    memory.zapisz(s)
    return OsobaApi(id=o.id, rola=o.rola, imie=o.imie, zalogowana=o.zalogowana)


@router.delete("/{sprawa_id}/osoby/{osoba_id}", status_code=204)
def usun_osobe(sprawa_id: str, osoba_id: str, login: str | None = Depends(login_opcjonalny)) -> None:
    s = sprawa_lub_404(sprawa_id, login)
    o = osoba_lub_404(s, osoba_id)
    if o is s.wnioskodawca():
        raise HTTPException(400, "Nie można usunąć osoby, która prowadzi sprawę.")
    s.osoby.remove(o)
    memory.zapisz(s)


@router.get("/{sprawa_id}/dane", response_model=engine.DaneOsoby)
def dane(sprawa_id: str, osoba: str | None = None, login: str | None = Depends(login_opcjonalny)) -> engine.DaneOsoby:
    """„Moje dane”: wszystkie pytania osoby w sekcjach, ze stanem i wartościami ze wszystkich źródeł."""
    s = sprawa_lub_404(sprawa_id, login)
    return engine.dane_osoby(s, osoba_lub_404(s, osoba))


@router.get("/{sprawa_id}/pytania", response_model=list[engine.Pytanie])
def nastepne_pytania(sprawa_id: str, osoba: str | None = None,
                     login: str | None = Depends(login_opcjonalny)) -> list[engine.Pytanie]:
    """Kreator: pytania aktywne, bez aktywnej wartości, na które użytkownik może odpowiedzieć."""
    s = sprawa_lub_404(sprawa_id, login)
    return engine.nastepne_pytania(s, osoba_lub_404(s, osoba))


@router.post("/{sprawa_id}/odpowiedzi", response_model=ZmianaDanych)
def zapisz_odpowiedzi(sprawa_id: str, odpowiedzi: list[Odpowiedz],
                      login: str | None = Depends(login_opcjonalny)) -> ZmianaDanych:
    """Dodaje albo zmienia wartość UŻYTKOWNIKA. `wartosc: null` usuwa tylko wartość użytkownika.

    Gdy pole ma już wartość z innego źródła, odpowiedź użytkownika staje się aktywna z wyboru ręcznego
    (`wybor_aktywnej: uzytkownik`) – wartość z innego źródła zostaje, a konflikt jest widoczny.
    """
    s = sprawa_lub_404(sprawa_id, login)
    obs = Obserwator(s)
    for o in odpowiedzi:
        osoba = osoba_lub_404(s, o.osoba)
        q = engine.pytanie_dla_pola(o.pole)
        if q is None:
            raise HTTPException(400, f"Nie znamy pola „{o.pole}”.")
        if not engine.dotyczy(q, s, osoba):
            raise HTTPException(400, f"Pytanie „{q['tresc']}” nie dotyczy tej osoby.")
        if not engine.edytowalne(q):
            raise HTTPException(400, f"Na pytanie „{q['tresc']}” nie można odpowiedzieć ręcznie.")
        if o.wartosc is None:
            merge.usun(osoba, o.pole, Kanal.KREATOR)
            continue
        try:
            wartosc = engine.normalizuj(q, o.wartosc)
        except engine.BlednaOdpowiedz as e:
            raise HTTPException(422, f"{q['tresc']}: {e}") from None
        inne_zrodla = any(w.kanal != Kanal.KREATOR for w in osoba.pola.get(o.pole, []))
        nowa = merge.dodaj(s, osoba, o.pole, WartoscPola(wartosc=wartosc, wystawca=Wystawca.UZYTKOWNIK,
                                                         kanal=Kanal.KREATOR, zrodlo_opis="Twoja odpowiedź"),
                           rodzaj=q["rodzaj"])
        if inne_zrodla:
            merge.ustaw_recznie(osoba, o.pole, nowa.id)
        if o.pole == "rola":
            osoba.rola = engine.rola_z_odpowiedzi(osoba.wartosc("rola"))
    memory.zapisz(s)
    return obs.zmiana()
