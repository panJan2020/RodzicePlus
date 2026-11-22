"""Schemat narzędzia (tool use) – wymusza na Claude odpowiedź w przewidywalnym JSON.

Lista pól jest generowana z katalogu pytań (z_dokumentow=true), więc kwestionariusz
i odczyt skanów zawsze mają ten sam słownik pól.
"""
from typing import Any

from app.questions.engine import pola_z_dokumentow

TYPY_DOKUMENTOW = ["opis_wyniku", "akt_urodzenia", "wniosek_urlop", "oswiadczenie", "ZAM", "ZAS-53",
                   "Z-3", "Z-3a", "Z-3b", "ZAS-12", "POG", "pismo_ZUS", "zrzut_systemu_ZUS",
                   "poswiadczenie_ubezpieczenia", "zaswiadczenie_lekarskie", "inne"]


def tool_definition() -> dict[str, Any]:
    pola = {p["pole"]: p["tresc"] for p in pola_z_dokumentow()}
    opis_pol = "\n".join(f"- {k}: {v}" for k, v in pola.items())
    return {
        "name": "zapisz_dane_sprawy",
        "description": "Zapisuje dane odczytane z dokumentów sprawy. Dostępne pola:\n" + opis_pol,
        "input_schema": {
            "type": "object",
            "properties": {
                "strony": {
                    "type": "array",
                    "items": {"type": "object", "properties": {
                        "strona": {"type": "integer"},
                        "typ": {"type": "string", "enum": TYPY_DOKUMENTOW}},
                        "required": ["strona", "typ"]},
                },
                "pola": {
                    "type": "array",
                    "items": {"type": "object", "properties": {
                        "pole": {"type": "string", "enum": list(pola)},
                        "osoba": {"type": "string", "enum": ["matka", "ojciec", "dziecko"]},
                        "wartosc": {"description": "string, liczba, bool albo lista stringów"},
                        "dokument": {"type": "string", "enum": TYPY_DOKUMENTOW},
                        "strona": {"type": "integer"},
                        "pewnosc": {"type": "number", "minimum": 0, "maximum": 1}},
                        "required": ["pole", "wartosc", "dokument", "strona", "pewnosc"]},
                },
                # Pole O4 `miesiace[]` (Z-3, „Składniki wynagrodzenia”) – dane do podstawy wymiaru (art. 36–38).
                "wynagrodzenia_miesieczne": {
                    "type": "array",
                    "items": {"type": "object", "properties": {
                        "miesiac": {"type": "string", "description": "RRRR-MM"},
                        "skladniki_stale": {"type": "number", "description": "składniki stałe brutto w kwocie wypłaconej"},
                        "skladniki_zmienne": {"type": "number", "description": "składniki zmienne brutto"},
                        "dni_przepracowane": {"type": "integer"},
                        "dni_obowiazujace": {"type": "integer", "description": "dni, które trzeba było przepracować"},
                        "stale_pelna_kwota": {"type": "number",
                                              "description": "pełna miesięczna kwota składników stałych z umowy"},
                        "strona": {"type": "integer"}},
                        "required": ["miesiac", "skladniki_stale"]},
                },
                "oczekiwany_wynik": {"type": "string"},
                "uwagi": {"type": "string", "description": "co było nieczytelne lub niejasne"},
            },
            "required": ["strony", "pola"],
        },
    }
