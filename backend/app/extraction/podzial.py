"""Podział stron PDF na dokumenty (egzemplarze formularzy) – sam kod, bez AI (docs/architektura.md, rozdz. 5, krok 2).

Wejście: wynik klasyfikacji (`strony[]`). Nowy dokument zaczyna się, gdy:
  * zmienia się typ strony,
  * strona ma „Strona 1 z y”,
  * numer strony formularza nie rośnie (np. po „Strona 8 z 8” znowu „Strona 3 z 8”),
  * poprzedni egzemplarz jest kompletny (x == y),
  * zmienia się liczba stron formularza (y) albo wariant (pierwszorazowy / w kontynuacji),
  * strona bez numeracji ma nagłówek nowego egzemplarza (`poczatek_formularza`).
Kolejne strony bez numeracji tego samego typu (np. kilka stron zrzutu z systemu ZUS) tworzą jeden dokument.
"""
from collections import Counter
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Fragment:
    typ: str
    strony: list[int] = field(default_factory=list)
    wariant: str | None = None
    stron_formularza: int | None = None
    osoby: list[str] = field(default_factory=list)
    obroty: dict[int, int] = field(default_factory=dict)   # strona → kąt do wyprostowania (tylko niezerowe)
    _ostatni_x: int | None = None

    @property
    def osoba(self) -> str | None:
        """Najczęstsza osoba wskazana na stronach dokumentu."""
        return Counter(self.osoby).most_common(1)[0][0] if self.osoby else None


def _nowy(cur: Fragment | None, s: dict[str, Any]) -> bool:
    if cur is None or s["typ"] != cur.typ:
        return True
    x, y, wariant = s.get("strona_formularza"), s.get("stron_formularza"), s.get("wariant")
    if x == 1:
        return True
    if x is not None and cur._ostatni_x is not None:
        if x <= cur._ostatni_x or (cur.stron_formularza and cur._ostatni_x >= cur.stron_formularza):
            return True
    if y and cur.stron_formularza and y != cur.stron_formularza:
        return True
    if wariant and cur.wariant and wariant != cur.wariant:
        return True
    if x is None and s.get("poczatek_formularza"):
        return True
    return False


def podziel(strony: list[dict[str, Any]]) -> list[Fragment]:
    wynik: list[Fragment] = []
    cur: Fragment | None = None
    for s in sorted(strony, key=lambda s: s["strona"]):
        if _nowy(cur, s):
            cur = Fragment(typ=s["typ"])
            wynik.append(cur)
        cur.strony.append(s["strona"])
        cur.wariant = cur.wariant or s.get("wariant")
        cur.stron_formularza = cur.stron_formularza or s.get("stron_formularza")
        if s.get("strona_formularza") is not None:
            cur._ostatni_x = s["strona_formularza"]
        if s.get("osoba"):
            cur.osoby.append(s["osoba"])
        if int(s.get("obrot") or 0):
            cur.obroty[s["strona"]] = int(s["obrot"])
    return wynik
