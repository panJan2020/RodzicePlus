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

WERSJA = "2a-9"            # odczyt pól
WERSJA_KLASYFIKACJI = "k2"  # klasyfikacja stron  # zmień przy zmianie promptów lub schematów → unieważnia cache odczytu


@dataclass(frozen=True)
class TypDokumentu:
    kod: str
    nazwa: str
    wystawca: Wystawca
    aliasy: tuple[str, ...] = ()   # kody `upload:<alias>` w katalogu pytań
    archiwalny: bool = False       # formularz zlikwidowany od 24.10.2026 (ZUR, ZAO, Z-3b)
    rola: str = "dane"             # dane | pismo_zus | decyzja_zus
    domyslny_tytul: str | None = None  # tytuł ubezpieczenia, którego dotyczy dokument (pola „na tytuł”)
    osoba_w_odczycie: bool = True  # False: dokument jednej osoby – osobę bierzemy z klasyfikacji strony
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
                 domyslny_tytul="umowa_o_prace", osoba_w_odczycie=False),
    TypDokumentu("Z-3a", "Zaświadczenie płatnika składek (Z-3a)", Wystawca.PRACODAWCA, ("Z-3a",),
                 domyslny_tytul="zlecenie", osoba_w_odczycie=False),
    TypDokumentu("Z-3b", "Zaświadczenie płatnika składek (Z-3b)", Wystawca.PRACODAWCA, ("Z-3b",), archiwalny=True,
                 domyslny_tytul="dzialalnosc", osoba_w_odczycie=False),
    TypDokumentu("ZAS-12", "Zaświadczenie płatnika – dalszy okres (ZAS-12)", Wystawca.PRACODAWCA, ("ZAS-12",), osoba_w_odczycie=False),
    TypDokumentu("akt_urodzenia", "Akt urodzenia", Wystawca.URZAD, ("akt",), etykieta_="Akt urodzenia"),
    TypDokumentu("zaswiadczenie_lekarskie", "Zaświadczenie lekarskie", Wystawca.LEKARZ, ("zaswiadczenie_lek",),
                 etykieta_="Zaświadczenie lekarskie"),
    TypDokumentu("zaswiadczenie_za_zyciem", "Zaświadczenie „Za życiem”", Wystawca.LEKARZ, ("za_zyciem",),
                 etykieta_="Zaświadczenie „Za życiem”"),
    TypDokumentu("wniosek_urlop", "Wniosek o urlop", Wystawca.UZYTKOWNIK, etykieta_="Wniosek o urlop"),
    TypDokumentu("poswiadczenie_ubezpieczenia", "Poświadczenie ubezpieczenia (ZUS)", Wystawca.ZUS,
                 ("poswiadczenie",), osoba_w_odczycie=False,
                 etykieta_="Poświadczenie ZUS"),
    TypDokumentu("zrzut_systemu_ZUS", "Zrzut z systemu ZUS", Wystawca.ZUS, ("zrzut_zus",), osoba_w_odczycie=False,
                 etykieta_="Zrzut z systemu ZUS"),
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
NIEZNANA, NIEZNANY = "nieznana", "nieznany"  # zamiast null w schematach odczytu pól
TYTULY = ["umowa_o_prace", "zlecenie", "dzialalnosc", "wspolpraca", "dzielo", "inne"]
# Kody tytułu ubezpieczenia (4 cyfry, widoczne na poświadczeniu i zrzucie z systemu ZUS) → tytuł w aplikacji.
# Tylko kody podane przez zespół; inny kod zostaje jako `kod_tytulu` i daje tytuł „inne” (do sprawdzenia).
# Zweryfikuj z mentorami ZUS przed wdrożeniem (docs/pytania_kalkulator.md, sekcja Z).
KODY_TYTULU = {"0110": "umowa_o_prace", "0411": "zlecenie", "0510": "dzialalnosc", "0570": "dzialalnosc"}
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
        "opis": {"type": "string", "description": "kilka słów: czym jest ta strona"},
    })}})


# ---------- przebieg 2: odczyt pól dokumentu ----------
# Gramatyka structured outputs ma limit złożoności (liczby obiektów w tablicach), więc schemat jest płaski:
#   * `pola` – jedna lista wpisów {pole, wartosc (tekst), osoba, tytul, strona, pewnosc} dla wszystkich pól skalarnych,
#   * osobne tablice tylko dla tabel (`miesiace`, `ezla`, `okresy_ubezpieczenia`) – wiersz ma własną stronę i pewność.
# Typ wartości (data, liczba, tak/nie, wybór) waliduje kod w `mapowanie.py`.

def _wiersz(props: dict[str, Any]) -> dict[str, Any]:
    return _obj({**props, "strona": {"type": "integer"}, "pewnosc": {"type": "number", "description": "0–1"}})


_TABELE: dict[str, dict[str, Any]] = {
    # D1 – zwolnienia lekarskie; `kod` tylko, gdy widoczny na dokumencie.
    "ezla": _wiersz({"od": _DATA, "do": _DATA,
                     "kod": _null({"type": "string", "description": "litera kodu niezdolności, tylko jeśli widoczna"})}),
    # D3a – Z-3, „Informacje o wypłaconych świadczeniach” pkt 1: okresy wynagrodzenia chorobowego (art. 92 KP)
    "wynagrodzenie_chorobowe_okres": _wiersz({
        "od": _DATA, "do": _DATA,
        "kod": _null({"type": "string", "description": "kod literowy przy okresie, tylko jeśli wpisany"})}),
    # B5a – okresy ubezpieczenia (zrzut systemu / poświadczenie ZUS)
    "okresy_ubezpieczenia": _wiersz({
        "kod_tytulu": _null({"type": "string", "description": "4-cyfrowy kod tytułu ubezpieczenia, np. 0110"}),
        "tytul": _enum(TYTULY), "platnik": _null({"type": "string"}),
        "od": _DATA, "do": _null(_DATA), "chorobowe": _null({"type": "boolean"}),
        "chorobowe_dobrowolne": _null({"type": "boolean"})}),
    # Q1 – poświadczenie ZUS, pkt 4: podstawa składki chorobowej za każdy miesiąc (działalność)
    "podstawa_deklarowana": _wiersz({
        "miesiac": {"type": "string", "description": "RRRR-MM"},
        "podstawa": {"type": "number", "description": "podstawa wymiaru składki na ubezpieczenie chorobowe"},
        "wakacje_skladkowe": {"type": "boolean", "description": "zaznaczono wakacje składkowe"}}),
    # O4 – Z-3, „Składniki wynagrodzenia”; 0 = nie ma w dokumencie
    "miesiace": _wiersz({
        "miesiac": {"type": "string", "description": "RRRR-MM"},
        "skladniki_stale": {"type": "number", "description": "składniki stałe brutto w kwocie wypłaconej"},
        "skladniki_zmienne": {"type": "number", "description": "składniki zmienne brutto; 0 gdy brak"},
        "dni_przepracowane": {"type": "integer", "description": "0 gdy brak"},
        "dni_obowiazujace": {"type": "integer", "description": "dni, które trzeba było przepracować; 0 gdy brak"},
        "stale_pelna_kwota": {"type": "number",
                              "description": "pełna miesięczna kwota składników stałych z umowy; 0 gdy brak"}}),
}


def opcje_pola(p: dict[str, Any]) -> list[str]:
    return [o["wartosc"] if isinstance(o, dict) else o for o in p.get("opcje") or []]


def _opis_pola(p: dict[str, Any]) -> str:
    typ, opcje = p["typ"], opcje_pola(p)
    if typ == "wybor" and opcje:
        fmt = "jedna z: " + ", ".join(opcje)
    elif typ == "wielokrotny" and opcje:
        fmt = "wartości z listy, oddzielone przecinkami: " + ", ".join(opcje)
    else:
        fmt = {"data": "data RRRR-MM-DD", "liczba": "liczba z kropką dziesiętną, np. 0.25",
               "tak_nie": "„tak” albo „nie”"}.get(typ, "tekst")
    return f"- {p['pole']}: {p['tresc']} [{fmt}]"


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
    props: dict[str, Any] = {}
    skalary = [p for p in pola if p["pole"] not in _TABELE]
    if skalary:
        wpis: dict[str, Any] = {"pole": {"type": "string", "enum": [p["pole"] for p in skalary]},
                                "wartosc": {"type": "string", "description": "wartość zapisana tekstem, w podanym formacie"}}
        if t.osoba_w_odczycie:
            wpis["osoba"] = _enum(OSOBY + [NIEZNANA])
        if any(p["pole"] in POLA_NA_TYTUL for p in skalary) and not t.domyslny_tytul:
            wpis["tytul"] = _enum(TYTULY + [NIEZNANY])   # tylko dla pól na tytuł (chorobowe, platnik_ponad_20)
        wpis |= {"strona": {"type": "integer"}, "pewnosc": {"type": "number", "description": "0–1"}}
        props["pola"] = {"type": "array", "items": _obj(wpis),
                         "description": "Każde widoczne pole jako osobny wpis. Pola:" + "\n" +
                                        "\n".join(_opis_pola(p) for p in skalary)}
    for p in pola:
        if p["pole"] in _TABELE:
            props[p["pole"]] = {"type": "array", "items": _TABELE[p["pole"]], "description": p["tresc"]}
    return _obj(props)
