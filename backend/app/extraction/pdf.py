"""Operacje na PDF bez AI: rozpoznanie formatu, liczba stron, wycinanie stron jednego dokumentu."""
import hashlib
import io

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
