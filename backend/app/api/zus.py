"""PRZEJŚCIOWE: stare endpointy /zus/* na nowych adapterach `sources/`.

Kształt odpowiedzi bez zmian, żeby frontend działał w trakcie migracji. Usuwane w kroku 4 migracji
(zastępują je GET /zrodla, POST /sprawy/{id}/zrodla/{kod}/pobierz, GET /sprawy/{id}/ubezpieczenie – docs/api.md).
"""
from datetime import date

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.api.auth import login_z_tokenu
from app.domain.model import Osoba, Rola, Sprawa
from app.domain.profile import FieldValue, Zrodlo
from app.sources import ZRODLA
from app.sources.zus_konto import DaneUbezpieczenia, OkresUbezpieczenia, dane_ubezpieczenia, okresy_z_pola
from app.storage import memory

router = APIRouter(prefix="/zus", tags=["ZUS (symulacja) – przejściowe"])


class OkresStary(OkresUbezpieczenia):
    platnik_ponad_20: str | None = None  # "ponad_20" / "do_20"


class DaneUbezpieczeniaStare(DaneUbezpieczenia):
    okresy: list[OkresStary]
    tytuly: list[str]
    chorobowe_od: date | None = None
    chorobowe_dobrowolne: bool | None = None
    platnik_ponad_20: str | None = None


class WynikPobrania(BaseModel):
    uzupelniono: list[str]
    pominieto: list[str]
    ubezpieczenie: DaneUbezpieczeniaStare


def _pola(login: str, dzien: date) -> dict:
    """Wartości z adapterów zus_konto, zus_platnik, ezla i mobywatel jako zwykły słownik."""
    s, o = Sprawa(id="tmp"), Osoba(id="o1", rola=Rola.MATKA, login=login)
    pola = {}
    for kod in ("mobywatel", "zus_konto", "zus_platnik", "ezla"):
        pola.update({k: w.wartosc for k, w in ZRODLA[kod].pobierz(s, o, dzien).items()})
    return pola


def _ubezpieczenie(login: str, dzien: date | None = None) -> DaneUbezpieczeniaStare:
    dzien = dzien or date.today()
    p = _pola(login, dzien)
    nowe = dane_ubezpieczenia(okresy_z_pola(p["okresy_ubezpieczenia"], dzien), dzien)
    platnik = next(iter((p.get("platnik_ponad_20") or {}).values()), None)
    okresy = [OkresStary(**{**ok.model_dump(), "platnik_ponad_20":
                            None if ok.platnik_ponad_20 is None else ("ponad_20" if ok.platnik_ponad_20 else "do_20")})
              for ok in nowe.okresy]
    return DaneUbezpieczeniaStare(**{**nowe.model_dump(), "okresy": okresy}, tytuly=p["tytuly"],
                                  chorobowe_od=p.get("chorobowe_od"),
                                  chorobowe_dobrowolne=p.get("chorobowe_dobrowolne"), platnik_ponad_20=platnik)


@router.get("/ubezpieczenie", response_model=DaneUbezpieczeniaStare)
def ubezpieczenie(authorization: str | None = Header(default=None), na_dzien: date | None = None):
    return _ubezpieczenie(login_z_tokenu(authorization), na_dzien)


@router.post("/pobierz-do-sprawy/{sprawa_id}", response_model=WynikPobrania)
def pobierz_do_sprawy(sprawa_id: str, authorization: str | None = Header(default=None)) -> WynikPobrania:
    login = login_z_tokenu(authorization)
    s = memory.pobierz(sprawa_id)
    if not s:
        raise HTTPException(404, "Nie ma takiej sprawy.")
    p = _pola(login, date.today())
    p["platnik_ponad_20"] = next(iter((p.get("platnik_ponad_20") or {}).values()), None)
    for k in ("etat", "srednie_wynagrodzenie_brutto", "podstawa_deklarowana_srednia", "zadluzenie_kwota"):
        if p.get(k) is not None:
            p[k] = float(p[k])
    osoba = s.osoby[0]
    uzupelniono, pominieto = [], []
    for pole, wartosc in p.items():
        if wartosc is None or pole in ("okresy_ubezpieczenia", "chorobowe"):
            continue
        obecne = osoba.pola.get(pole)
        if obecne is not None and obecne.zrodlo != Zrodlo.ZUS:
            pominieto.append(pole)
            continue
        osoba.pola[pole] = FieldValue(wartosc=wartosc, zrodlo=Zrodlo.ZUS)
        uzupelniono.append(pole)
    memory.zapisz(s)
    return WynikPobrania(uzupelniono=uzupelniono, pominieto=pominieto, ubezpieczenie=_ubezpieczenie(login))
