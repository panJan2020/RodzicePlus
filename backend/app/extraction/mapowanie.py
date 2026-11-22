"""Odczyt skanu (wynik narzędzia Claude) → WartoscPola w sprawie (docs/architektura.md, rozdz. 5, krok 4).

Wystawca zależy od typu dokumentu (Z-3 → pracodawca, poświadczenie / zrzut systemu ZUS → zus, ZAM → uzytkownik).
Zapis zawsze przez `merge.dodaj` – odczyt AI nie nadpisuje innych źródeł, tylko dodaje wartość.
Pełny przebieg (podział na egzemplarze, porównanie z decyzją ZUS) – etap 2.
"""
from decimal import Decimal
from typing import Any

from app import merge
from app.domain.model import Kanal, Osoba, Rola, Sprawa, WartoscPola, Wystawca
from app.questions import engine

WYSTAWCA_DOKUMENTU: dict[str, Wystawca] = {
    "ZAM": Wystawca.UZYTKOWNIK, "ZAS-53": Wystawca.UZYTKOWNIK, "wniosek_urlop": Wystawca.UZYTKOWNIK,
    "oswiadczenie": Wystawca.UZYTKOWNIK, "POG": Wystawca.UZYTKOWNIK, "inne": Wystawca.UZYTKOWNIK,
    "Z-3": Wystawca.PRACODAWCA, "Z-3a": Wystawca.PRACODAWCA, "Z-3b": Wystawca.PRACODAWCA, "ZAS-12": Wystawca.PRACODAWCA,
    "akt_urodzenia": Wystawca.URZAD, "zaswiadczenie_lekarskie": Wystawca.LEKARZ,
    "poswiadczenie_ubezpieczenia": Wystawca.ZUS, "zrzut_systemu_ZUS": Wystawca.ZUS,
    "pismo_ZUS": Wystawca.ZUS, "opis_wyniku": Wystawca.ZUS,
}


def _osoba(s: Sprawa, pole: str, rola: str | None) -> Osoba:
    """Właściciel pola: dziecko dla pól dziecka, w innym razie osoba o podanej roli (brak → wnioskodawca)."""
    q = engine.pytanie_dla_pola(pole)
    if (q and q.get("osoba") == ["dziecko"]) or rola == Rola.DZIECKO.value:
        return next((o for o in s.osoby if o.rola == Rola.DZIECKO), None) or s.dodaj_osobe(Rola.DZIECKO, "Dziecko")
    if rola == Rola.OJCIEC.value:
        return next((o for o in s.osoby if o.rola == Rola.OJCIEC), None) or s.dodaj_osobe(Rola.OJCIEC)
    return s.wnioskodawca() or s.dodaj_osobe(Rola.MATKA)


def _kwota(v: Any) -> str | None:
    return None if v is None else str(Decimal(str(v)).quantize(Decimal("0.01")))


def miesiac_pola(m: dict[str, Any]) -> dict[str, Any]:
    """Miesiąc z odczytu → element pola `miesiace[]`: {miesiac, skladniki_stale, skladniki_zmienne,
    dni_przepracowane, dni_obowiazujace, stale_pelna_kwota} (kwoty jako tekst)."""
    return {"miesiac": m["miesiac"], "skladniki_stale": _kwota(m.get("skladniki_stale") or 0),
            "skladniki_zmienne": _kwota(m.get("skladniki_zmienne") or 0),
            "dni_przepracowane": int(m.get("dni_przepracowane") or 0),
            "dni_obowiazujace": int(m.get("dni_obowiazujace") or 0),
            "stale_pelna_kwota": _kwota(m.get("stale_pelna_kwota"))}


def zapisz_odczyt(s: Sprawa, dane: dict[str, Any], plik: str) -> None:
    if dane.get("oczekiwany_wynik"):
        s.oczekiwany_wynik = dane["oczekiwany_wynik"]  # tylko do porównania, nigdy dane wejściowe

    dokumenty: dict[str, str] = {}  # typ dokumentu → dokument_id w tym pliku

    def dokument_id(typ: str) -> str:
        if typ not in dokumenty:
            dokumenty[typ] = s.nowe_id("d")
        return dokumenty[typ]

    for item in dane.get("pola", []):
        typ = item.get("dokument") or "inne"
        q = engine.pytanie_dla_pola(item["pole"])
        w = WartoscPola(wartosc=item["wartosc"], wystawca=WYSTAWCA_DOKUMENTU.get(typ, Wystawca.UZYTKOWNIK),
                        kanal=Kanal.UPLOAD, zrodlo_opis=f"{typ}, str. {item.get('strona')}",
                        dokument_id=dokument_id(typ), strona=item.get("strona"),
                        pewnosc=float(item.get("pewnosc") or 0))
        try:
            merge.dodaj(s, _osoba(s, item["pole"], item.get("osoba")), item["pole"], w,
                        rodzaj=q["rodzaj"] if q else "fakt")
        except merge.NiedozwolonaWartosc:
            continue  # np. plan z dokumentu – pomijamy

    if dane.get("wynagrodzenia_miesieczne"):
        # Pole O4 `miesiace[]` (docs/pytania_kalkulator.md) – kwoty jako tekst, dni jako liczby.
        merge.dodaj(s, _osoba(s, "miesiace", None), "miesiace",
                    WartoscPola(wartosc=[miesiac_pola(m) for m in dane["wynagrodzenia_miesieczne"]],
                                wystawca=Wystawca.PRACODAWCA,
                                kanal=Kanal.UPLOAD, zrodlo_opis=f"Z-3 ({plik})", dokument_id=dokument_id("Z-3"),
                                pewnosc=1.0))
