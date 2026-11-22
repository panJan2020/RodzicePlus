"""Treści informacyjne: dokumenty i terminy, ryzyka, wsparcie, linki (docs/opis_aplikacji.md, rozdz. 8).

Treści trzymajcie w plikach JSON/Markdown w app/content (TODO), żeby nie-programiści mogli je edytować.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/info", tags=["informacje"])

LINKI = [
    {"nazwa": "ZUS – zasiłki", "url": "https://www.zus.pl"},
    {"nazwa": "MRPiPS – urlop rodzicielski", "url": "https://www.gov.pl/web/rodzina/urlop-rodzicielski"},
    {"nazwa": "PIP – rodzicielstwo", "url": "https://www.pip.gov.pl/dla-pracodawcow/porady-prawne/rodzicielstwo"},
    {"nazwa": "Rejestr stanu cywilnego (odpis aktu)", "url": "https://www.gov.pl/web/cyfryzacja/rejestr-stanu-cywilnego"},
]


@router.get("/linki")
def linki() -> list[dict]:
    return LINKI


@router.get("/wsparcie")
def wsparcie() -> list[dict]:
    # TODO: lista organizacji wyłącznie charytatywnych (zweryfikujcie ręcznie każdą pozycję!)
    return []
