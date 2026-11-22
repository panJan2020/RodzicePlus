"""Źródła danych (symulacje): lista źródeł, pobranie danych do sprawy, stan ubezpieczenia (docs/api.md 2.4, 2.7).

Źródła wymagają zalogowania (mObywatel) i działają tylko dla osoby zalogowanej w tej sprawie.
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app import merge
from app.api.wspolne import Obserwator, ZmianaDanych, login_opcjonalny, osoba_lub_404, sprawa_lub_404
from app.sources import ZRODLA, ZrodloNiedostepne
from app.sources.zus_konto import DaneUbezpieczenia, dane_ubezpieczenia, okresy_z_pola
from app.questions import engine
from app.storage import memory

router = APIRouter(tags=["źródła danych (symulacja)"])


class ZrodloApi(BaseModel):
    kod: str
    nazwa: str
    wystawca: str
    opis: str
    symulacja: bool = True


class Pobranie(BaseModel):
    osoba: str | None = None  # osoba_id; brak = osoba zalogowana


@router.get("/zrodla", response_model=list[ZrodloApi])
def lista_zrodel() -> list[ZrodloApi]:
    return [ZrodloApi(kod=z.kod, nazwa=z.nazwa, wystawca=z.wystawca.value, opis=z.opis) for z in ZRODLA.values()]


@router.post("/sprawy/{sprawa_id}/zrodla/{kod}/pobierz", response_model=ZmianaDanych)
def pobierz(sprawa_id: str, kod: str, dane: Pobranie | None = None,
            login: str | None = Depends(login_opcjonalny)) -> ZmianaDanych:
    """Dodaje wartości ze źródła (nic nie nadpisuje); aktywną wartość wybiera hierarchia wiarygodności."""
    if not login:
        raise HTTPException(401, "Aby pobrać dane z systemów, zaloguj się przez mObywatela.")
    zrodlo = ZRODLA.get(kod)
    if zrodlo is None:
        raise HTTPException(404, "Nie ma takiego źródła danych.")
    s = sprawa_lub_404(sprawa_id, login)
    osoba = osoba_lub_404(s, dane.osoba if dane else None)
    if osoba.login != login:
        raise HTTPException(403, "Dane z systemów możemy pobrać tylko dla osoby zalogowanej.")
    obs = Obserwator(s)
    try:
        wartosci = zrodlo.pobierz(s, osoba)
    except ZrodloNiedostepne as e:
        raise HTTPException(400, str(e)) from None
    for pole, w in wartosci.items():
        q = engine.pytanie_dla_pola(pole)
        merge.dodaj(s, osoba, pole, w, rodzaj=q["rodzaj"] if q else "fakt")
    memory.zapisz(s)
    return obs.zmiana()


@router.get("/sprawy/{sprawa_id}/ubezpieczenie", response_model=DaneUbezpieczenia)
def ubezpieczenie(sprawa_id: str, osoba: str | None = None, na_dzien: date | None = None,
                  login: str | None = Depends(login_opcjonalny)) -> DaneUbezpieczenia:
    """Stan ubezpieczenia na dzień – z AKTYWNEJ wartości pola `okresy_ubezpieczenia`."""
    s = sprawa_lub_404(sprawa_id, login)
    o = osoba_lub_404(s, osoba)
    w = o.aktywna("okresy_ubezpieczenia")
    if w is None:
        raise HTTPException(404, "Nie mamy jeszcze danych o Twoim ubezpieczeniu. Pobierz je z ZUS.")
    dzien = na_dzien or date.today()
    okresy = okresy_z_pola(w.wartosc, dzien)
    for ok in okresy:
        ok.zrodlo_opis = w.zrodlo_opis
    return dane_ubezpieczenia(okresy, dzien)
