"""Uprawnienia i kalkulator (FR-07..FR-18)."""
from datetime import date

from fastapi import APIRouter, HTTPException

from app.calculator import podstawa as pw
from app.calculator import timeline
from app.domain.results import WynikKalkulatora, WynikUprawnienia
from app.params.store import get_params
from app.questions import engine
from app.rules import eligibility
from app.storage import memory

router = APIRouter(prefix="/sprawy/{sprawa_id}", tags=["kalkulator"])


@router.get("/uprawnienia", response_model=list[WynikUprawnienia])
def uprawnienia(sprawa_id: str, osoba: int = 0) -> list[WynikUprawnienia]:
    s = memory.pobierz(sprawa_id)
    if not s:
        raise HTTPException(404, "Nie ma takiej sprawy")
    return eligibility.ocen_wszystko(s.osoby[osoba], get_params())


@router.get("/kalkulator", response_model=WynikKalkulatora)
def kalkulator(sprawa_id: str, osoba: int = 0) -> WynikKalkulatora:
    s = memory.pobierz(sprawa_id)
    if not s:
        raise HTTPException(404, "Nie ma takiej sprawy")
    o = engine.aktywne_pola(s.osoby[osoba])  # bez odpowiedzi na pytania wykluczone

    data_str = o.get("data_porodu") or o.get("pdp")
    if not data_str:
        raise HTTPException(422, "Aby policzyć zasiłek, podaj datę porodu albo przewidywaną datę porodu (pytania G1, G2).")
    data_porodu = date.fromisoformat(data_str)
    p = get_params(data_porodu)

    tytuly = o.get("tytuly", [])
    if "umowa_o_prace" in tytuly and o.get("srednie_wynagrodzenie_brutto"):
        # Tryb uproszczony. TODO: pełny tryb z wynagrodzenia_miesieczne (Z-3) → pw.podstawa_pracownik
        m = pw.MiesiacWynagrodzenia(skladniki_stale=float(o.get("srednie_wynagrodzenie_brutto")))
        podstawa = pw.podstawa_pracownik([m], pelny_etat=(o.get("etat", 1) >= 1), p=p)
    elif o.get("podstawa_deklarowana_srednia"):
        podstawa = pw.podstawa_dobrowolne([float(o.get("podstawa_deklarowana_srednia"))], p)
    else:
        raise HTTPException(422, "Aby policzyć kwotę, podaj średnie wynagrodzenie albo podstawę składek (pytania O4s, Q1s).")

    okresy = timeline.plan_matki(
        data_porodu=data_porodu, liczba_dzieci=int(o.get("liczba_dzieci", 1)),
        za_zyciem=bool(o.get("za_zyciem", False)), wariant=o.get("wariant", "100_70"),
        podstawa=podstawa, p=p, drugi_rodzic_bierze_9_tyg=o.get("drugi_rodzic_aktywny") == "tak")
    return WynikKalkulatora(podstawa_wymiaru=float(podstawa), okresy=okresy,
                            suma=round(sum(x.kwota_za_okres for x in okresy), 2),
                            wersja_parametrow=p["_plik"])
