"""Scalanie okresów (np. zwolnień e-ZLA) z kilku dokumentów tego samego wystawcy w jedną wartość pola.

Przykład: cztery zaświadczenia Z-3 podają kolejne części jednego okresu niezdolności. Każda część zostaje
osobną `WartoscPola` (z dokumentem i stroną – „Skąd to wiemy”, usuwanie dokumentu), a razem tworzą
jedną wartość „scaloną”, którą widzą reguły (części są nieaktywne i nie liczą się do konfliktu).

Zasady:
  * scalamy tylko wartości TEGO SAMEGO wystawcy (dwa i więcej źródeł); wystawcy różnią się hierarchią jak zawsze,
  * łączymy okresy sąsiadujące (koniec + 1 dzień = początek) i nakładające się, o ile mają ten sam kod,
  * odcinki z różnymi kodami (np. „B” i brak kodu) zostają osobne – o kodzie decyduje reguła,
  * nakładanie się okresów z RÓŻNYCH dokumentów nie jest konfliktem, tylko ostrzeżeniem (`WartoscPola.uwagi`).
"""
from datetime import date, datetime, timedelta, timezone
from typing import Any

from app.domain.model import Kanal, Osoba, Sprawa, WartoscPola

POLA_SCALANE = ("ezla",)   # pola typu „okresy”, które scalamy (okresy ubezpieczenia mają tytuły – nie scalamy)


def _data(v: Any) -> date:
    return date.fromisoformat(str(v)[:10])


def _tekst(d: date) -> str:
    return d.strftime("%d.%m.%Y")


def _odcinki(w: WartoscPola) -> list[tuple[date, date, str | None]]:
    wynik = []
    for o in w.wartosc or []:
        try:
            wynik.append((_data(o["od"]), _data(o["do"]), o.get("kod") or None))
        except (KeyError, TypeError, ValueError):
            continue  # element bez poprawnych dat – mapowanie i tak go odrzuca
    return wynik


def scal_odcinki(odcinki: list[tuple[date, date, str | None]]) -> list[tuple[date, date, str | None]]:
    """Łączy sąsiadujące i nakładające się odcinki o tym samym kodzie. Wynik posortowany po początku."""
    wynik: list[tuple[date, date, str | None]] = []
    for kod in dict.fromkeys(k for _, _, k in odcinki):
        biezacy: list[date] | None = None
        for od, do, _ in sorted(x for x in odcinki if x[2] == kod):
            if biezacy and od <= biezacy[1] + timedelta(days=1):
                biezacy[1] = max(biezacy[1], do)
            else:
                if biezacy:
                    wynik.append((biezacy[0], biezacy[1], kod))
                biezacy = [od, do]
        if biezacy:
            wynik.append((biezacy[0], biezacy[1], kod))
    return sorted(wynik, key=lambda x: (x[0], x[1], x[2] or ""))


def nakladania(czesci: list[list[tuple[date, date, str | None]]]) -> list[str]:
    """Ostrzeżenia o dniach wspólnych dla okresów z RÓŻNYCH dokumentów (po jednym tekście na zakres)."""
    dni: dict[date, int] = {}
    for odcinki in czesci:
        for dzien in {d for od, do, _ in odcinki for d in (od + timedelta(days=i) for i in range((do - od).days + 1))}:
            dni[dzien] = dni.get(dzien, 0) + 1
    wspolne = sorted(d for d, n in dni.items() if n > 1)
    zakresy: list[list[date]] = []
    for d in wspolne:
        if zakresy and d - zakresy[-1][1] == timedelta(days=1):
            zakresy[-1][1] = d
        else:
            zakresy.append([d, d])
    return [f"Okresy z różnych dokumentów nakładają się: {_tekst(a) if a == b else f'{_tekst(a)}–{_tekst(b)}'}. "
            "Sprawdź daty zwolnień." for a, b in zakresy]


def scal(sprawa: Sprawa, osoba: Osoba, pole: str) -> None:
    """Przelicza wartości scalone pola `pole` osoby (po dodaniu albo usunięciu wartości). Nie wybiera aktywnej –
    po tej funkcji wołamy `przelicz`."""
    wartosci = osoba.pola.get(pole, [])
    stare = {w.wystawca: w for w in wartosci if w.czesci}                 # wartości scalone (po jednej na wystawcę)
    zrodlowe = [w for w in wartosci if not w.czesci]
    for w in zrodlowe:
        w.czesc_z = None
    nowe: list[WartoscPola] = []
    for wystawca in dict.fromkeys(w.wystawca for w in zrodlowe):
        czesci = [w for w in zrodlowe if w.wystawca == wystawca]
        if len(czesci) < 2:
            continue
        odcinki = [_odcinki(w) for w in czesci]
        kanaly = {w.kanal for w in czesci}
        scalona = stare.get(wystawca) or WartoscPola(
            id=sprawa.nowe_id("w"), wartosc=None, wystawca=wystawca, kanal=Kanal.SYSTEM, zrodlo_opis="")
        scalona.wartosc = [{"od": od.isoformat(), "do": do.isoformat(), "kod": kod}
                           for od, do, kod in scal_odcinki([x for lista in odcinki for x in lista])]
        scalona.kanal = kanaly.pop() if len(kanaly) == 1 else Kanal.SYSTEM
        scalona.zrodlo_opis = "; ".join(w.zrodlo_opis for w in czesci) + " – okresy połączone"
        scalona.dokument_id, scalona.strona = None, None
        scalona.pewnosc = min(w.pewnosc for w in czesci)
        scalona.czesci = [w.id for w in czesci]
        scalona.uwagi = nakladania(odcinki)
        scalona.utworzono = datetime.now(timezone.utc)
        for w in czesci:
            w.czesc_z, w.aktywna = scalona.id, False
        nowe.append(scalona)
    osoba.pola[pole] = zrodlowe + nowe
    if not osoba.pola[pole]:
        osoba.pola.pop(pole)
