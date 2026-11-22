"""Sprawy: profil, odpowiedzi z kwestionariusza, upload dokumentów (FR-03, FR-28)."""
from typing import Any

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.config import MAX_UPLOAD_MB
from app.domain.profile import FieldValue, Sprawa, Zrodlo
from app.extraction import claude_client, merge
from app.questions import engine
from app.storage import memory

router = APIRouter(prefix="/sprawy", tags=["sprawy"])


def _sprawa(sprawa_id: str) -> Sprawa:
    s = memory.pobierz(sprawa_id)
    if not s:
        raise HTTPException(404, "Nie ma takiej sprawy.")
    return s


class Odpowiedz(BaseModel):
    pole: str
    wartosc: Any
    osoba: int = 0  # indeks osoby w sprawie


@router.post("", response_model=Sprawa)
def utworz() -> Sprawa:
    return memory.nowa_sprawa()


@router.get("/{sprawa_id}", response_model=Sprawa)
def pobierz(sprawa_id: str) -> Sprawa:
    return _sprawa(sprawa_id)


@router.post("/{sprawa_id}/odpowiedzi", response_model=Sprawa)
def zapisz_odpowiedzi(sprawa_id: str, odpowiedzi: list[Odpowiedz]) -> Sprawa:
    s = _sprawa(sprawa_id)
    for o in odpowiedzi:
        pola = _osoba(s, o.osoba).pola
        if o.wartosc is None:  # „Wyczyść odpowiedź”
            pola.pop(o.pole, None)
            continue
        pola[o.pole] = FieldValue(wartosc=o.wartosc, zrodlo=Zrodlo.UZYTKOWNIK,
                                                   potwierdzone=True)
    memory.zapisz(s)
    return s


def _osoba(s: Sprawa, osoba: int):
    if not 0 <= osoba < len(s.osoby):
        raise HTTPException(404, "W tej sprawie nie ma takiej osoby.")
    return s.osoby[osoba]


@router.get("/{sprawa_id}/pytania")
def nastepne_pytania(sprawa_id: str, osoba: int = 0) -> list[dict]:
    """Dla kreatora: pytania aktywne (warunki spełnione) i jeszcze bez odpowiedzi."""
    return engine.nastepne_pytania(_osoba(_sprawa(sprawa_id), osoba))


@router.get("/{sprawa_id}/dane", response_model=engine.DaneOsoby)
def dane(sprawa_id: str, osoba: int = 0) -> engine.DaneOsoby:
    """Zakładka „Dane”: całe drzewo pytań ze stanem (aktywne / zablokowane / wykluczone),
    aktualną wartością i jej źródłem. Edycja przez POST /odpowiedzi."""
    return engine.dane_osoby(_osoba(_sprawa(sprawa_id), osoba), osoba)


def _przetworz(zid: str, sprawa_id: str, pdf: bytes) -> None:
    try:
        wynik = claude_client.odczytaj_pdf(pdf)
        s = memory.pobierz(sprawa_id)
        merge.scal(s, wynik["dane"])
        memory.zapisz(s)
        memory.aktualizuj_zadanie(zid, status="gotowe", strony=wynik["dane"].get("strony"),
                                  uwagi=wynik["dane"].get("uwagi"), tokeny=wynik["uzycie_tokenow"])
    except Exception as e:  # noqa: BLE001 – błąd pokazujemy użytkownikowi
        memory.aktualizuj_zadanie(zid, status="blad", blad=str(e))


@router.post("/{sprawa_id}/dokumenty", status_code=202)
async def wgraj_dokument(sprawa_id: str, tlo: BackgroundTasks, plik: UploadFile = File(...)) -> dict:
    """Odczyt skanu trwa kilkadziesiąt sekund → zwracamy id zadania, Flutter odpytuje /zadania/{id}."""
    s = _sprawa(sprawa_id)
    if plik.content_type != "application/pdf":
        raise HTTPException(415, "Obsługujemy tylko PDF")
    dane = await plik.read()
    if len(dane) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"Plik większy niż {MAX_UPLOAD_MB} MB")
    s.dokumenty.append(plik.filename or "dokument.pdf")
    zid = memory.nowe_zadanie(sprawa_id, plik.filename or "")
    tlo.add_task(_przetworz, zid, sprawa_id, dane)
    return {"zadanie_id": zid}


@router.get("/zadania/{zadanie_id}")
def status_zadania(zadanie_id: str) -> dict:
    z = memory.zadanie(zadanie_id)
    if not z:
        raise HTTPException(404, "Nie ma takiego zadania")
    return z
