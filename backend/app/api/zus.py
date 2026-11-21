"""Symulacja systemów ZUS (FR-02, FR-04, FR-05, FR-06): ubezpieczenie, zadłużenie, e-ZLA, PUE.

Wszystkie endpointy wymagają nagłówka `Authorization: sim-<login>` z symulowanego logowania (FR-01).
"""
from datetime import date
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.api.auth import login_z_tokenu
from app.domain.profile import FieldValue, Zrodlo
from app.mocks import zus as zus_mock
from app.mocks.zus import DaneUbezpieczenia
from app.storage import memory

router = APIRouter(prefix="/zus", tags=["ZUS (symulacja)"])


class WynikPobrania(BaseModel):
    uzupelniono: list[str]   # pola zapisane w sprawie ze źródłem "zus"
    pominieto: list[str]     # pola, które użytkownik już podał (jego odpowiedź ma pierwszeństwo)
    ubezpieczenie: DaneUbezpieczenia


def _dane(token: str | None) -> dict[str, Any]:
    return zus_mock.konto(login_z_tokenu(token))


@router.get("/ubezpieczenie", response_model=DaneUbezpieczenia)
def ubezpieczenie(authorization: str | None = Header(default=None), na_dzien: date | None = None) -> DaneUbezpieczenia:
    """Tytuły i okresy ubezpieczenia oraz informacja, czy osoba podlega ubezpieczeniu chorobowemu (FR-02)."""
    return zus_mock.dane_ubezpieczenia(_dane(authorization), na_dzien)


@router.get("/zadluzenie")
def zadluzenie(authorization: str | None = Header(default=None)) -> dict:
    d = _dane(authorization)
    return {"kwota": d.get("zadluzenie_kwota", 0), "zaswiadczenie": "SYMULACJA – dokument nie jest wiążący"}


@router.get("/ezla")
def ezla(authorization: str | None = Header(default=None)) -> list[dict]:
    return _dane(authorization).get("ezla", [])


@router.post("/pobierz-do-sprawy/{sprawa_id}", response_model=WynikPobrania)
def pobierz_do_sprawy(sprawa_id: str, authorization: str | None = Header(default=None)) -> WynikPobrania:
    """Wypełnia profil sprawy danymi z 'ZUS' (zrodlo=zus). Nie nadpisuje odpowiedzi użytkownika."""
    d = _dane(authorization)
    s = memory.pobierz(sprawa_id)
    if not s:
        raise HTTPException(404, "Nie ma takiej sprawy.")
    osoba = s.osoby[0]
    uzupelniono, pominieto = [], []
    for pole, wartosc in zus_mock.pola_profilu(d).items():
        obecne = osoba.pola.get(pole)
        if obecne is not None and obecne.zrodlo != Zrodlo.ZUS:
            pominieto.append(pole)
            continue
        osoba.pola[pole] = FieldValue(wartosc=wartosc, zrodlo=Zrodlo.ZUS)
        uzupelniono.append(pole)
    memory.zapisz(s)
    return WynikPobrania(uzupelniono=uzupelniono, pominieto=pominieto, ubezpieczenie=zus_mock.dane_ubezpieczenia(d))
