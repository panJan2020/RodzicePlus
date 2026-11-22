"""Scalanie wartości pól: dodawanie, wybór aktywnej wartości, ręczny wybór, konflikty.

Wszystkie zapisy wartości przechodzą przez ten moduł (CLAUDE.md, sekcja 8). Zasady:
  * nowa informacja = nowa WartoscPola; wartości z innych źródeł nie są nadpisywane,
  * to samo źródło (ten sam kanał i dokument) podające nową wartość aktualizuje SWOJĄ wartość
    (np. ponowne pobranie z ZUS, zmiana odpowiedzi w kreatorze),
  * pola rodzaju `plan` przyjmują tylko wartości z kreatora, pola `wybor` nie trafiają do osób
    (należą do scenariusza),
  * po każdej zmianie aktywną wartość wybiera hierarchia, chyba że użytkownik wybrał ręcznie.

Niespójności między różnymi polami – później (etap 5).
"""
import json
from typing import Any

from app.domain.model import Kanal, Osoba, Sprawa, WartoscPola
from app.merge import hierarchia, okresy
from app.params.store import get_params


class NiedozwolonaWartosc(ValueError):
    """Wartość nie może trafić do tego pola (np. plan z dokumentu, wybór scenariusza w polach osoby)."""


def prog_pewnosci() -> float:
    return float(get_params()["prog_pewnosci_ai"])


def _ten_sam_zrodlo(a: WartoscPola, b: WartoscPola) -> bool:
    return a.kanal == b.kanal and a.dokument_id == b.dokument_id and a.wystawca == b.wystawca


def _normalizuj(v: Any) -> str:
    return json.dumps(v, sort_keys=True, ensure_ascii=False, default=str)


def dodaj(sprawa: Sprawa, osoba: Osoba, pole: str, nowa: WartoscPola, rodzaj: str = "fakt",
          prog: float | None = None) -> WartoscPola:
    """Dodaje wartość (albo aktualizuje wartość z tego samego źródła) i przelicza aktywną.

    Zwraca zapisaną wartość (z nadanym `id`).
    """
    if rodzaj == "wybor":
        raise NiedozwolonaWartosc(f"Pole „{pole}” to wybór do symulacji – ustawia się je w kalkulatorze, nie w danych osoby.")
    if rodzaj == "plan" and nowa.kanal != Kanal.KREATOR:
        raise NiedozwolonaWartosc(f"Pole „{pole}” opisuje plan – może je podać tylko użytkownik.")

    wartosci = osoba.pola.setdefault(pole, [])
    stara = next((w for w in wartosci if _ten_sam_zrodlo(w, nowa)), None)
    if stara is not None:
        stara.wartosc, stara.zrodlo_opis, stara.strona = nowa.wartosc, nowa.zrodlo_opis, nowa.strona
        stara.pewnosc, stara.utworzono = nowa.pewnosc, nowa.utworzono
        zapisana = stara
    else:
        nowa.id = sprawa.nowe_id("w")
        wartosci.append(nowa)
        zapisana = nowa
    if pole in okresy.POLA_SCALANE:
        okresy.scal(sprawa, osoba, pole)
    przelicz(osoba, pole, prog)
    return zapisana


def usun(osoba: Osoba, pole: str, kanal: Kanal, dokument_id: str | None = None, prog: float | None = None) -> bool:
    """Usuwa wartości danego źródła (np. „wyczyść moją odpowiedź”). Wartości z innych źródeł zostają."""
    wartosci = osoba.pola.get(pole, [])
    zostaja = [w for w in wartosci if not (w.kanal == kanal and w.dokument_id == dokument_id)]
    if len(zostaja) == len(wartosci):
        return False
    if zostaja:
        osoba.pola[pole] = zostaja
    else:
        osoba.pola.pop(pole, None)
    przelicz(osoba, pole, prog)
    return True


def usun_dokument(sprawa: Sprawa, dokument_id: str, prog: float | None = None) -> int:
    """Usuwa wszystkie wartości odczytane z dokumentu (u wszystkich osób) i przelicza aktywne. Zwraca liczbę usuniętych."""
    usuniete = 0
    for o in sprawa.osoby:
        for pole in list(o.pola):
            przed = len(o.pola[pole])
            if usun(o, pole, Kanal.UPLOAD, dokument_id, prog):
                usuniete += przed - len(o.pola.get(pole, []))
    for o in sprawa.osoby:   # po usunięciu części przeliczamy wartości scalone
        for pole in okresy.POLA_SCALANE:
            if pole in o.pola:
                okresy.scal(sprawa, o, pole)
                przelicz(o, pole, prog)
    return usuniete


def przelicz(osoba: Osoba, pole: str, prog: float | None = None) -> None:
    """Ustawia flagę `aktywna` – ręczny wybór użytkownika albo najlepsza według hierarchii."""
    wartosci = [w for w in osoba.pola.get(pole, []) if w.czesc_z is None]   # części scalone nie biorą udziału
    reczna = osoba.wybor_reczny.get(pole)
    if reczna and not any(w.id == reczna for w in wartosci):
        osoba.wybor_reczny.pop(pole)  # wybrana wartość zniknęła (np. usunięty dokument) → wracamy do automatu
        reczna = None
    wybrana = next((w for w in wartosci if w.id == reczna), None) if reczna else \
        hierarchia.najlepsza(wartosci, prog if prog is not None else prog_pewnosci())
    for w in osoba.pola.get(pole, []):
        w.aktywna = w is wybrana


def ustaw_recznie(osoba: Osoba, pole: str, wartosc_id: str | None, prog: float | None = None) -> None:
    """Użytkownik wybiera źródło pola. `None` przywraca wybór automatyczny."""
    if wartosc_id is None:
        osoba.wybor_reczny.pop(pole, None)
    else:
        if not any(w.id == wartosc_id for w in osoba.pola.get(pole, [])):
            raise KeyError(wartosc_id)
        osoba.wybor_reczny[pole] = wartosc_id
    przelicz(osoba, pole, prog)


def wybor_aktywnej(osoba: Osoba, pole: str) -> str:
    return "uzytkownik" if pole in osoba.wybor_reczny else "automatyczny"


def konflikt(osoba: Osoba, pole: str) -> bool:
    """Konflikt = to samo pole tej samej osoby ma różne wartości z różnych źródeł."""
    return len({_normalizuj(w.wartosc) for w in osoba.pola.get(pole, []) if w.czesc_z is None}) > 1


def konflikty(sprawa: Sprawa) -> list[tuple[str, str]]:
    """Lista (osoba_id, pole) z konfliktem."""
    return [(o.id, pole) for o in sprawa.osoby for pole in o.pola if konflikt(o, pole)]


def aktywne_wartosci(osoba: Osoba) -> dict[str, Any]:
    """pole → aktywna wartość (dla reguł i kalkulatora)."""
    return {pole: w.wartosc for pole, lista in osoba.pola.items() for w in lista if w.aktywna}


def migawka(sprawa: Sprawa) -> dict[tuple[str, str], tuple[str, str]]:
    """(osoba_id, pole) → (id aktywnej wartości, wartość) – do porównania „przed / po” w ZmianaDanych."""
    return {(o.id, pole): (w.id, _normalizuj(w.wartosc))
            for o in sprawa.osoby for pole, lista in o.pola.items() for w in lista if w.aktywna}
