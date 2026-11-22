"""Podział stron PDF na dokumenty (egzemplarze formularzy) – sam kod, bez wywołań Claude."""
import json
from pathlib import Path

from app.extraction.pipeline import _uzupelnij_strony
from app.extraction.podzial import podziel

FIKSTURA = json.loads((Path(__file__).parent / "fixtures" / "odczyt" / "sprawa_przykladowa.json").read_text("utf-8"))


def _s(n, typ, x=None, y=None, wariant=None, poczatek=False, osoba=None):
    return {"strona": n, "typ": typ, "wariant": wariant, "strona_formularza": x, "stron_formularza": y,
            "poczatek_formularza": poczatek, "osoba": osoba, "obrocona": False}


def test_sprawa_przykladowa_zas53_pismo_4x_z3_zrzut_decyzja():
    fr = podziel(FIKSTURA["klasyfikacja"]["strony"])
    assert [f.typ for f in fr] == ["ZAS-53", "pismo_ZUS", "Z-3", "Z-3", "Z-3", "Z-3", "zrzut_systemu_ZUS",
                                   "decyzja_ZUS", "inne"]
    z3 = [f for f in fr if f.typ == "Z-3"]
    assert [f.strony for f in z3] == [[4, 5, 6, 7], [8, 9, 10, 11], [12, 13, 14, 15], [16, 17, 18, 19]]
    assert [f.wariant for f in z3] == ["pierwszorazowy", "w_kontynuacji", "w_kontynuacji", "w_kontynuacji"]
    assert fr[6].strony == [20, 21]  # zrzut bez numeracji – kolejne strony to jeden dokument
    assert fr[0].osoba == "matka"


def test_numeracja_nie_rosnie_to_nowy_egzemplarz():
    fr = podziel([_s(1, "Z-3", 1, 3), _s(2, "Z-3", 2, 3), _s(3, "Z-3", 2, 3), _s(4, "Z-3", 3, 3)])
    assert [f.strony for f in fr] == [[1, 2], [3, 4]]


def test_kompletny_egzemplarz_konczy_dokument_nawet_bez_strony_1():
    # po „3 z 3” kolejna strona tego samego typu (z nieodczytaną „1”) zaczyna nowy egzemplarz
    fr = podziel([_s(1, "Z-3", 1, 3), _s(2, "Z-3", 2, 3), _s(3, "Z-3", 3, 3), _s(4, "Z-3", 2, 3)])
    assert [f.strony for f in fr] == [[1, 2, 3], [4]]


def test_bez_numeracji_nowy_egzemplarz_po_naglowku():
    fr = podziel([_s(1, "Z-3", poczatek=True), _s(2, "Z-3"), _s(3, "Z-3", poczatek=True), _s(4, "Z-3")])
    assert [f.strony for f in fr] == [[1, 2], [3, 4]]


def test_zmiana_wariantu_i_typu_w_srodku():
    fr = podziel([_s(1, "Z-3", wariant="pierwszorazowy", poczatek=True), _s(2, "Z-3"),
                  _s(3, "Z-3", wariant="w_kontynuacji"), _s(4, "ZAS-53", 1, 1), _s(5, "Z-3")])
    assert [(f.typ, f.strony) for f in fr] == [("Z-3", [1, 2]), ("Z-3", [3]), ("ZAS-53", [4]), ("Z-3", [5])]


def test_kolejnosc_stron_wg_numeru_i_brakujace_strony_jako_inne():
    strony = _uzupelnij_strony([_s(2, "pismo_ZUS", poczatek=True), _s(1, "ZAS-53", 1, 1), _s(9, "Z-3")], 3)
    assert [(s["strona"], s["typ"]) for s in strony] == [(1, "ZAS-53"), (2, "pismo_ZUS"), (3, "inne")]
    assert [f.typ for f in podziel(strony)] == ["ZAS-53", "pismo_ZUS", "inne"]
