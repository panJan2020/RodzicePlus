"""Operacje na PDF bez AI: rozpoznanie formatu, liczba stron, wycinanie stron jednego dokumentu."""
import hashlib
import io

import pymupdf

from pypdf import PdfReader, PdfWriter


def to_pdf(dane: bytes) -> bool:
    return dane[:1024].lstrip().startswith(b"%PDF")


def skrot(dane: bytes) -> str:
    return hashlib.sha256(dane).hexdigest()


def liczba_stron(dane: bytes) -> int:
    return len(PdfReader(io.BytesIO(dane)).pages)


def wytnij(dane: bytes, strony: list[int]) -> bytes:
    """Nowy PDF z wybranych stron (numeracja od 1, w podanej kolejności)."""
    czytnik = PdfReader(io.BytesIO(dane))
    pisarz = PdfWriter()
    for n in strony:
        pisarz.add_page(czytnik.pages[n - 1])
    bufor = io.BytesIO()
    pisarz.write(bufor)
    return bufor.getvalue()


DPI_OBROCONYCH = 200


def renderuj(dane: bytes, strony: list[int], obroty: dict[int, int], dpi: int = DPI_OBROCONYCH) -> list[bytes]:
    """Strony (numeracja od 1) jako PNG w podanej rozdzielczości, każda obrócona do pionu o `obroty[strona]` stopni
    zgodnie z ruchem wskazówek zegara (0, 90, 180, 270). Dla stron obróconych skan często czyta się lepiej po
    wyprostowaniu i renderze w wyższej rozdzielczości."""
    wynik = []
    with pymupdf.open(stream=dane, filetype="pdf") as dok:
        for n in strony:
            strona = dok[n - 1]
            strona.set_rotation((strona.rotation + obroty.get(n, 0)) % 360)
            wynik.append(strona.get_pixmap(dpi=dpi).tobytes("png"))
    return wynik
