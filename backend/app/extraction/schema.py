"""Typy dokumentów i schematy JSON odpowiedzi Claude (structured outputs – wymuszony schemat JSON).

Dwa przebiegi (docs/architektura.md, rozdz. 5):
  1. klasyfikacja stron – `schemat_klasyfikacji()`,
  2. odczyt pól jednego dokumentu – `schemat_odczytu(typ)`; pola generowane z katalogu pytań:
     pole trafia do schematu typu, gdy ma `z_dokumentow: true` i w `zrodla` kod `upload:<alias typu>`.
     Dzięki temu kreator i odczyt skanów mają zawsze ten sam słownik pól.

Schematy są „ścisłe”: każdy obiekt ma `additionalProperties: false` i wszystkie pola wymagane
(brak wartości = `null` albo pusta lista).
"""
from dataclasses import dataclass
from typing import Any

from app.domain.model import Wystawca
from app.questions.engine import pola_z_dokumentow

WERSJA = "2a-1"  # zmień przy zmianie promptów lub schematów → unieważnia cache odczytu


@dataclass(frozen=True)
class TypDokumentu:
    kod: str
    nazwa: str
    wystawca: Wystawca
    aliasy: tuple[str, ...] = ()   # kody `upload:<alias>` w katalogu pytań
    archiwalny: bool = False       # formularz zlikwidowany od 24.10.2026 (ZUR, ZAO, Z-3b)
    rola: str = "dane"             # dane | pismo_zus | decyzja_zus
    domyslny_tytul: str | None = None  # tytuł ubezpieczenia, którego dotyczy dokument (pola „na tytuł”)
    etykieta_: str = ""            # krótka nazwa do „Skąd to wiemy” (domyślnie kod, np. „Z-3”)

    @property
    def etykieta(self) -> str:
        return self.etykieta_ or self.kod


TYPY: dict[str, TypDokumentu] = {t.kod: t for t in [
    TypDokumentu("ZAM", "Wniosek o zasiłek macierzyński (ZAM)", Wystawca.UZYTKOWNIK, ("ZAM",)),
    TypDokumentu("ZUR", "Wniosek o zasiłek macierzyński (ZUR)", Wystawca.UZYTKOWNIK, ("ZAM",), archiwalny=True),
    TypDokumentu("ZAO", "Wniosek o zasiłek opiekuńczy / macierzyński (ZAO)", Wystawca.UZYTKOWNIK, ("ZAM",),
                 archiwalny=True),
    TypDokumentu("ZAS-53", "Wniosek o zasiłek chorobowy (ZAS-53)", Wystawca.UZYTKOWNIK, ("ZAS-53",)),
    TypDokumentu("Z-3", "Zaświadczenie płatnika składek (Z-3)", Wystawca.PRACODAWCA, ("Z-3",),
                 domyslny_tytul="umowa_o_prace"),
    TypDokumentu("Z-3a", "Zaświadczenie płatnika składek (Z-3a)", Wystawca.PRACODAWCA, ("Z-3a",),
                 domyslny_tytul="zlecenie"),
    TypDokumentu("Z-3b", "Zaświadczenie płatnika składek (Z-3b)", Wystawca.PRACODAWCA, ("Z-3b",), archiwalny=True,
                 domyslny_tytul="dzialalnosc"),
    TypDokumentu("ZAS-12", "Zaświadczenie płatnika – dalszy okres (ZAS-12)", Wystawca.PRACODAWCA, ("ZAS-12",)),
    TypDokumentu("akt_urodzenia", "Akt urodzenia", Wystawca.URZAD, ("akt",), etykieta_="Akt urodzenia"),
    TypDokumentu("zaswiadczenie_lekarskie", "Zaświadczenie lekarskie", Wystawca.LEKARZ, ("zaswiadczenie_lek",),
                 etykieta_="Zaświadczenie lekarskie"),
    TypDokumentu("zaswiadczenie_za_zyciem", "Zaświadczenie „Za życiem”", Wystawca.LEKARZ, ("za_zyciem",),
                 etykieta_="Zaświadczenie „Za życiem”"),
    TypDokumentu("wniosek_urlop", "Wniosek o urlop", Wystawca.UZYTKOWNIK, etykieta_="Wniosek o urlop"),
    TypDokumentu("poswiadczenie_ubezpieczenia", "Poświadczenie ubezpieczenia (ZUS)", Wystawca.ZUS,
                 ("poswiadczenie",), etykieta_="Poświadczenie ZUS"),
    TypDokumentu("zrzut_systemu_ZUS", "Zrzut z systemu ZUS", Wystawca.ZUS, ("zrzut_zus",), etykieta_="Zrzut z systemu ZUS"),
    TypDokumentu("pismo_ZUS", "Pismo z ZUS", Wystawca.ZUS, rola="pismo_zus", etykieta_="Pismo ZUS"),
    TypDokumentu("decyzja_ZUS", "Decyzja / wynik sprawy w ZUS", Wystawca.ZUS, rola="decyzja_zus", etykieta_="Decyzja ZUS"),
    TypDokumentu("inne", "Inny dokument", Wystawca.UZYTKOWNIK, etykieta_="Inny dokument"),
]}

OPIS_TYPOW = """- ZAM – wniosek o zasiłek macierzyński (od 24.10.2026),
- ZUR, ZAO – archiwalne wnioski o zasiłek macierzyński / opiekuńczy,
- ZAS-53 – wniosek o zasiłek chorobowy (osoby niebędące pracownikami lub po ustaniu ubezpieczenia),
- Z-3 – zaświadczenie płatnika składek dla pracownika; Z-3a – dla zleceniobiorcy; Z-3b – działalność (archiwalny),
- ZAS-12 – zaświadczenie płatnika o zasiłku za dalszy okres,
- akt_urodzenia – akt urodzenia (lub zgonu) dziecka,
- zaswiadczenie_lekarskie – zaświadczenie lekarskie (ciąża, przewidywana data porodu),
- zaswiadczenie_za_zyciem – zaświadczenie o ciężkim i nieodwracalnym upośledzeniu („Za życiem”),
- wniosek_urlop – wniosek pracownika o urlop macierzyński / rodzicielski / ojcowski,
- poswiadczenie_ubezpieczenia – wewnętrzny dokument ZUS potwierdzający ubezpieczenie chorobowe,
- zrzut_systemu_ZUS – wydruk / zrzut ekranu z systemu ZUS (tabele okresów ubezpieczenia, świadczeń),
- pismo_ZUS – pismo ZUS do ubezpieczonego lub płatnika (np. wezwanie do uzupełnienia dokumentów),
- decyzja_ZUS – decyzja ZUS albo kartka z opisem wyniku sprawy (np. „wypłacono zasiłek”, „odmówiono”),
- inne – wszystko inne (koperta, pusta strona, nieczytelna strona)."""

OSOBY = ["matka", "ojciec", "dziecko"]
TYTULY = ["umowa_o_prace", "zlecenie", "dzialalnosc", "wspolpraca", "dzielo", "inne"]
POLA_NA_TYTUL = {"chorobowe", "platnik_ponad_20"}  # wartość-słownik {tytul: wartość} (docs/architektura.md, rozdz. 4)


# ---------- pomocnicze konstruktory schematu ----------

def _obj(props: dict[str, Any]) -> dict[str, Any]:
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


def _null(s: dict[str, Any]) -> dict[str, Any]:
    return {"anyOf": [s, {"type": "null"}]}


def _enum(wartosci: list[str]) -> dict[str, Any]:
    return {"type": "string", "enum": wartosci}


_DATA = {"type": "string", "description": "data RRRR-MM-DD"}


# ---------- przebieg 1: klasyfikacja stron ----------

def schemat_klasyfikacji() -> dict[str, Any]:
    return _obj({"strony": {"type": "array", "items": _obj({
        "strona": {"type": "integer", "description": "numer strony w pliku PDF, od 1"},
        "typ": _enum(list(TYPY)),
        "wariant": _null(_enum(["pierwszorazowy", "w_kontynuacji"])),
        "strona_formularza": _null({"type": "integer", "description": "x z napisu „Strona x z y”"}),
        "stron_formularza": _null({"type": "integer", "description": "y z napisu „Strona x z y”"}),
        "poczatek_formularza": {"type": "boolean",
                                "description": "strona zaczyna nowy egzemplarz dokumentu (nagłówek, tytuł formularza)"},
        "osoba": _null(_enum(OSOBY)),
        "obrocona": {"type": "boolean"},
    })}})


# ---------- przebieg 2: odczyt pól dokumentu ----------

_ELEMENTY: dict[str, dict[str, Any]] = {
    # D1 – zwolnienia lekarskie; `kod` tylko, gdy widoczny na dokumencie.
    "ezla": _obj({"od": _DATA, "do": _DATA,
                  "kod": _null({"type": "string", "description": "litera kodu niezdolności, tylko jeśli widoczna"})}),
    # B5a – okresy ubezpieczenia (zrzut systemu / poświadczenie ZUS)
    "okresy_ubezpieczenia": _obj({
        "tytul": _enum(TYTULY), "platnik": _null({"type": "string"}),
        "od": _DATA, "do": _null(_DATA), "chorobowe": _null({"type": "boolean"}),
        "chorobowe_dobrowolne": _null({"type": "boolean"})}),
    # O4 – Z-3, „Składniki wynagrodzenia”
    "miesiace": _obj({
        "miesiac": {"type": "string", "description": "RRRR-MM"},
        "skladniki_stale": {"type": "number", "description": "składniki stałe brutto w kwocie wypłaconej"},
        "skladniki_zmienne": _null({"type": "number"}),
        "dni_przepracowane": _null({"type": "integer"}),
        "dni_obowiazujace": _null({"type": "integer", "description": "dni, które trzeba było przepracować"}),
        "stale_pelna_kwota": _null({"type": "number", "description": "pełna miesięczna kwota składników stałych"})}),
}


def _schemat_wartosci(p: dict[str, Any]) -> dict[str, Any]:
    if p["pole"] in _ELEMENTY:
        return {"type": "array", "items": _ELEMENTY[p["pole"]]}
    opcje = [o["wartosc"] if isinstance(o, dict) else o for o in p.get("opcje") or []]
    typ = p["typ"]
    if typ == "data":
        return _DATA
    if typ == "liczba":
        return {"type": "number"}
    if typ == "tak_nie":
        return {"type": "boolean"}
    if typ == "wybor" and opcje:
        return _enum(opcje)
    if typ == "wielokrotny" and opcje:
        return {"type": "array", "items": _enum(opcje)}
    return {"type": "string"}


def pola_typu(typ: str) -> list[dict[str, Any]]:
    """Pola katalogu, które można odczytać z dokumentu tego typu."""
    t = TYPY[typ]
    kody = {f"upload:{a}" for a in t.aliasy}
    return [p for p in pola_z_dokumentow() if kody & set(p["zrodla"])]


def schemat_odczytu(typ: str) -> dict[str, Any] | None:
    """Schemat odczytu dla typu dokumentu; None – dokument bez pól (nie wołamy Claude)."""
    t = TYPY[typ]
    if t.rola == "decyzja_zus":
        return _obj({"tekst": {"type": "string", "description": "rozstrzygnięcie sprawy, przepisane dosłownie"},
                     "strona": {"type": "integer"}})
    if t.rola == "pismo_zus":
        return _obj({"braki": {"type": "array", "items": {"type": "string"},
                               "description": "czego ZUS brakuje / o co prosi, krótko"},
                     "strona": {"type": "integer"}})
    pola = pola_typu(typ)
    if not pola:
        return None
    props = {}
    for p in pola:
        wpis = {"wartosc": _schemat_wartosci(p), "osoba": _null(_enum(OSOBY)),
                "strona": {"type": "integer"}, "pewnosc": {"type": "number", "description": "0–1"}}
        if p["pole"] in POLA_NA_TYTUL:
            wpis["tytul"] = _null(_enum(TYTULY))
        props[p["pole"]] = {"type": "array", "description": p["tresc"], "items": _obj(wpis)}
    return _obj(props)
