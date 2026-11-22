"""Przebieg odczytu jednego pliku PDF (docs/architektura.md, rozdz. 5, kroki 1–5):

  1. klasyfikacja stron – JEDNO wywołanie Claude na cały PDF,
  2. podział na dokumenty – kod (`podzial.py`),
  3. odczyt pól – JEDNO wywołanie na dokument, tylko jego strony, schemat tylko dla jego typu,
  4–5. mapowanie na WartoscPola + merge (`mapowanie.py`).

Wyniki wywołań Claude są w cache po hashu pliku (`cache.py`). Funkcja `zapytaj` jest wstrzykiwana,
więc testy mogą podać zapisane odpowiedzi zamiast wywoływać API.
"""
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app import config
from app.domain.model import Dokument, Sprawa
from app.extraction import cache, claude_client, mapowanie, pdf, prompts
from app.extraction.podzial import Fragment, podziel
from app.extraction.schema import TYPY, WERSJA, WERSJA_KLASYFIKACJI, schemat_klasyfikacji, schemat_odczytu

Postep = Callable[[str, float, str], None]          # (etap, postęp 0–1 w obrębie pliku, komunikat)
Zapytaj = Callable[..., dict[str, Any]]    # (pdf, polecenie, schemat, etap, obrazy=None) → {"dane", "info"}


@dataclass
class WynikPliku:
    strony: list[dict[str, Any]]
    dokumenty: list[Dokument]
    wywolania: list[dict[str, Any]] = field(default_factory=list)  # etap, model, czas, tokeny, cache


def _z_cache(klucz: str, wywolanie: Callable[[], dict[str, Any]], wywolania: list[dict[str, Any]],
             etap: str) -> dict[str, Any]:
    zapisany = cache.wczytaj(klucz)
    if zapisany is not None:
        wywolania.append({**zapisany.get("info", {}), "etap": etap, "cache": True})
        return zapisany["dane"]
    wynik = wywolanie()
    cache.zapisz(klucz, wynik)
    wywolania.append({**wynik["info"], "cache": False})
    return wynik["dane"]


def _uzupelnij_strony(strony: list[dict[str, Any]], n: int) -> list[dict[str, Any]]:
    """Każda strona 1..n dokładnie raz; brakujące (pominięte przez model) → typ `inne`."""
    po_numerze = {s["strona"]: s for s in strony if isinstance(s.get("strona"), int) and 1 <= s["strona"] <= n}
    return [po_numerze.get(i) or {"strona": i, "typ": "inne", "wariant": None, "strona_formularza": None,
                                  "stron_formularza": None, "poczatek_formularza": True, "osoba": None,
                                  "obrocona": False, "obrot": "0"}
            for i in range(1, n + 1)]


def przetworz_plik(s: Sprawa, plik: str, dane: bytes, postep: Postep | None = None,
                   zapytaj: Zapytaj | None = None) -> WynikPliku:
    postep = postep or (lambda *_: None)
    zapytaj = zapytaj or claude_client.zapytaj
    sha = pdf.skrot(dane)
    prefiks = f"{sha}.{WERSJA}.{config.CLAUDE_MODEL}"
    prefiks_klas = f"{sha}.{WERSJA_KLASYFIKACJI}.{config.CLAUDE_MODEL}"  # zmiana odczytu nie powtarza klasyfikacji
    wywolania: list[dict[str, Any]] = []

    # 1. klasyfikacja stron
    postep("klasyfikacja", 0.05, "Rozpoznajemy dokumenty…")
    n = pdf.liczba_stron(dane)
    klas = _z_cache(f"{prefiks_klas}.klasyfikacja",
                    lambda: zapytaj(dane, prompts.KLASYFIKACJA, schemat_klasyfikacji(), "klasyfikacja"),
                    wywolania, "klasyfikacja")
    strony = _uzupelnij_strony(klas.get("strony") or [], n)

    # 2. podział na dokumenty
    postep("podzial", 0.25, "Dzielimy plik na dokumenty…")
    fragmenty = podziel(strony)

    # 3–5. odczyt pól, mapowanie, merge
    licznik_typu: dict[str, int] = {}
    razem_typu = {f.typ: sum(1 for x in fragmenty if x.typ == f.typ) for f in fragmenty}
    dokumenty: list[Dokument] = []
    for i, frag in enumerate(fragmenty):
        licznik_typu[frag.typ] = licznik_typu.get(frag.typ, 0) + 1
        t = TYPY.get(frag.typ, TYPY["inne"])
        postep("odczyt", 0.3 + 0.65 * i / max(len(fragmenty), 1),
               f"Odczytujemy: {t.etykieta} ({licznik_typu[frag.typ]} z {razem_typu[frag.typ]})…")
        odczyt = _odczytaj(dane, frag, prefiks, zapytaj, wywolania)
        dokumenty.append(mapowanie.zapisz_dokument(s, plik, frag, odczyt))

    postep("scalanie", 1.0, "Zapisujemy odczytane dane…")
    return WynikPliku(strony=strony, dokumenty=dokumenty, wywolania=wywolania)


def _odczytaj(dane: bytes, frag: Fragment, prefiks: str, zapytaj: Zapytaj,
              wywolania: list[dict[str, Any]]) -> dict[str, Any] | None:
    schemat = schemat_odczytu(frag.typ) if frag.typ in TYPY else None
    if schemat is None:
        return None  # dokument bez pól do odczytu (np. „inne”, wniosek o urlop)
    klucz = f"{prefiks}.odczyt.{frag.typ}.{'-'.join(map(str, frag.strony))}"
    if frag.obroty:   # obrócone strony: prostujemy i renderujemy w wyższej rozdzielczości (zamiast surowego PDF)
        klucz += f".prosto{pdf.DPI_OBROCONYCH}"
        return _z_cache(klucz, lambda: zapytaj(b"", prompts.odczyt(frag.typ), schemat, f"odczyt:{frag.typ}",
                                               obrazy=pdf.renderuj(dane, frag.strony, frag.obroty)),
                        wywolania, f"odczyt:{frag.typ}")
    return _z_cache(klucz, lambda: zapytaj(pdf.wytnij(dane, frag.strony), prompts.odczyt(frag.typ), schemat,
                                           f"odczyt:{frag.typ}"),
                    wywolania, f"odczyt:{frag.typ}")
