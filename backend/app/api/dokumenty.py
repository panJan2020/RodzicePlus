"""Upload dokumentów i lista rozpoznanych dokumentów (docs/api.md 2.6, 3.4).

POST zwraca od razu `202 {zadanie_id}`; odczyt (kilkadziesiąt sekund na plik) idzie w tle,
Flutter odpytuje `GET /zadania/{id}` co 3 s. Logika odczytu – `app.extraction.pipeline`.
"""
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile

from app.api.wspolne import Obserwator, ZmianaDanych, login_opcjonalny, sprawa_lub_404
from app.config import MAX_UPLOAD_MB
from app.api.swiadczenia import policz_swiadczenia
from app.domain.model import Dokument
from app.domain.results import Porownanie
from app import porownanie as porownaj_z_decyzja
from app.extraction import mapowanie, pdf, pipeline
from app.storage import memory

router = APIRouter(prefix="/sprawy", tags=["dokumenty"])
log = logging.getLogger("odczyt")


def uruchom_zadanie(zid: str, sprawa_id: str, pliki: list[tuple[str, bytes]]) -> None:
    """Zadanie w tle: pliki po kolei przez pipeline; stan zadania widoczny w GET /zadania/{id}."""
    s = memory.pobierz(sprawa_id)
    obs = Obserwator(s)
    przed = {d.id for d in s.dokumenty}
    ile = len(pliki)
    wywolania: list[dict] = []

    def nowe_dokumenty() -> list[str]:
        return [d.id for d in s.dokumenty if d.id not in przed]

    try:
        for i, (nazwa, dane) in enumerate(pliki):
            def postep(etap: str, p: float, komunikat: str, i: int = i, nazwa: str = nazwa) -> None:
                memory.aktualizuj_zadanie(zid, etap=etap, postep=round((i + p) / ile, 2),
                                          komunikat=f"{nazwa}: {komunikat}" if ile > 1 else komunikat,
                                          dokumenty=nowe_dokumenty())

            wywolania += pipeline.przetworz_plik(s, nazwa, dane, postep=postep).wywolania
        memory.zapisz(s)
        memory.aktualizuj_zadanie(zid, status="gotowe", etap="scalanie", postep=1.0,
                                  komunikat="Gotowe. Sprawdź odczytane dane.", dokumenty=nowe_dokumenty(),
                                  wywolania=wywolania, zmiana_danych=obs.zmiana().model_dump())
    except Exception as e:  # noqa: BLE001 – błąd pokazujemy użytkownikowi, bez treści dokumentu
        log.warning("odczyt zadania %s nieudany: %s", zid, type(e).__name__)
        komunikat = str(e) if isinstance(e, pipeline.claude_client.BladOdczytu) else \
            "Nie udało się odczytać dokumentów. Spróbuj ponownie za chwilę."
        memory.zapisz(s)
        memory.aktualizuj_zadanie(zid, status="blad", blad=komunikat, dokumenty=nowe_dokumenty(),
                                  wywolania=wywolania, zmiana_danych=obs.zmiana().model_dump())


@router.post("/{sprawa_id}/dokumenty", status_code=202)
async def wgraj_dokumenty(sprawa_id: str, tlo: BackgroundTasks, pliki: list[UploadFile] = File(...),
                          login: str | None = Depends(login_opcjonalny)) -> dict:
    """Wiele plików PDF (pole `pliki`, max 30 MB każdy) → jedno zadanie w tle."""
    sprawa_lub_404(sprawa_id, login)
    odebrane: list[tuple[str, bytes]] = []
    for plik in pliki:
        nazwa = plik.filename or "dokument.pdf"
        dane = await plik.read()
        if len(dane) > MAX_UPLOAD_MB * 1024 * 1024:
            raise HTTPException(413, f"Plik „{nazwa}” jest większy niż {MAX_UPLOAD_MB} MB.")
        if not pdf.to_pdf(dane):
            raise HTTPException(415, f"Plik „{nazwa}” nie jest plikiem PDF. Na razie przyjmujemy tylko pliki PDF.")
        odebrane.append((nazwa, dane))
    if not odebrane:
        raise HTTPException(422, "Nie wybrano żadnego pliku.")
    zid = memory.nowe_zadanie(sprawa_id, ", ".join(n for n, _ in odebrane))
    tlo.add_task(uruchom_zadanie, zid, sprawa_id, odebrane)
    return {"zadanie_id": zid}


@router.get("/{sprawa_id}/dokumenty")
def lista_dokumentow(sprawa_id: str, login: str | None = Depends(login_opcjonalny)) -> list[Dokument]:
    return sprawa_lub_404(sprawa_id, login).dokumenty


@router.delete("/{sprawa_id}/dokumenty/{dokument_id}")
def usun_dokument(sprawa_id: str, dokument_id: str, login: str | None = Depends(login_opcjonalny)) -> ZmianaDanych:
    """Usuwa dokument i wszystkie wartości z niego odczytane."""
    s = sprawa_lub_404(sprawa_id, login)
    obs = Obserwator(s)
    if not mapowanie.usun_dokument(s, dokument_id):
        raise HTTPException(404, "W tej sprawie nie ma takiego dokumentu.")
    memory.zapisz(s)
    return obs.zmiana()


@router.get("/{sprawa_id}/porownanie")
def porownanie(sprawa_id: str, login: str | None = Depends(login_opcjonalny)) -> Porownanie:
    """Wynik aplikacji vs decyzja ZUS ze sprawy testowej (tylko status: przysługuje / nie przysługuje)."""
    s = sprawa_lub_404(sprawa_id, login)
    wynik = porownaj_z_decyzja.porownaj(s, policz_swiadczenia(s))
    if wynik is None:
        raise HTTPException(404, "Ta sprawa nie ma decyzji ZUS do porównania.")
    return wynik
