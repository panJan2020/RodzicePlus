"""Porównanie wyniku aplikacji z decyzją ZUS zapisaną w `Sprawa.oczekiwany_wynik` (wersja minimalna).

Porównujemy tylko STATUS: „przysługuje” (decyzja: przyznano) albo „nie przysługuje” (odmowa). Bez kwot.
Rozpoznanie decyzji to proste słowa kluczowe w kodzie – bez AI. Decyzja nigdy nie jest daną wejściową reguł.

Wynik aplikacji `warunkowo` i `brak_danych` nie jest porównywalny z decyzją (`nie_do_porownania`).
"""
from app.domain.model import Sprawa
from app.domain.results import DecyzjaZus, Porownanie, Status, WynikPorownania, WynikSwiadczenia

ODMOWA = ("nie przyznano", "odmówiono", "odmowa", "odmowne", "nie przysługuje", "nie przysługiwał")
PRZYZNANO = ("przyznano", "wypłacono", "przysługuje", "przysługiwał")
SWIADCZENIA = (("chorobow", "zasilek_chorobowy_ciaza"), ("macierzy", "zasilek_macierzynski_urlop_macierzynski"))


def rozstrzygniecie(tekst: str) -> str | None:
    """„przyznano” albo „odmowa” (zaprzeczenia sprawdzamy najpierw: „nie przyznano” zawiera „przyznano”)."""
    t = tekst.lower()
    if any(s in t for s in ODMOWA):
        return "odmowa"
    if any(s in t for s in PRZYZNANO):
        return "przyznano"
    return None


def swiadczenie_z_tekstu(tekst: str) -> str | None:
    t = tekst.lower()
    return next((kod for slowo, kod in SWIADCZENIA if slowo in t), None)


def porownaj(s: Sprawa, wyniki: list[WynikSwiadczenia]) -> Porownanie | None:
    """None – sprawa nie ma decyzji ZUS."""
    if not s.oczekiwany_wynik:
        return None
    dok = next((d for d in s.dokumenty if d.rola == "decyzja_zus"), None)
    decyzja = DecyzjaZus(tekst=s.oczekiwany_wynik, dokument_id=dok.id if dok else None,
                         strona=dok.strony[0] if dok and dok.strony else None,
                         swiadczenie=swiadczenie_z_tekstu(s.oczekiwany_wynik),
                         rozstrzygniecie=rozstrzygniecie(s.oczekiwany_wynik))
    uwagi: list[str] = []
    if decyzja.swiadczenie is None or decyzja.rozstrzygniecie is None:
        return Porownanie(decyzja_zus=decyzja, zgodnosc="nie_do_porownania",
                          uwagi=["Nie rozpoznaliśmy, jakiego świadczenia dotyczy decyzja ZUS albo jak rozstrzygnięto."])
    wynik = next((w for w in wyniki if w.swiadczenie == decyzja.swiadczenie), None)
    if wynik is None:
        return Porownanie(decyzja_zus=decyzja, zgodnosc="nie_do_porownania",
                          uwagi=["Aplikacja nie ma jeszcze wyniku dla tego świadczenia."])
    porownywany = WynikPorownania(swiadczenie=wynik.swiadczenie, status=wynik.status)
    if wynik.status in (Status.WARUNKOWO, Status.BRAK_DANYCH):
        uwagi.append("Wynik aplikacji jest warunkowy albo brakuje danych – nie porównujemy go z decyzją ZUS.")
        return Porownanie(decyzja_zus=decyzja, wynik_aplikacji=porownywany, zgodnosc="nie_do_porownania", uwagi=uwagi)
    zgodne = (wynik.status == Status.PRZYSLUGUJE) == (decyzja.rozstrzygniecie == "przyznano")
    if wynik.orientacyjny:
        uwagi.append("Wynik aplikacji jest orientacyjny (zob. pola do potwierdzenia).")
    return Porownanie(decyzja_zus=decyzja, wynik_aplikacji=porownywany, zgodnosc="zgodne" if zgodne else "rozne",
                      uwagi=uwagi)
