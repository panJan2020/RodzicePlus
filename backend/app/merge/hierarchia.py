"""Hierarchia wiarygodności – która wartość pola jest domyślnie aktywna (docs/architektura.md, rozdz. 6).

Kolejność (od najważniejszej):
  zus / urzad / wyliczone  >  sad  >  pracodawca / lekarz  >  odczyt AI z pewnością < progu  >  uzytkownik

Remisy (ta sama ranga):
  1. wartość z dokumentu (kanal upload) wygrywa z kreatorem – dotyczy wystawcy `uzytkownik`
     (np. wniosek ZAM złożony w ZUS jest ważniejszy niż odpowiedź wpisana w aplikacji),
  2. wyższa pewność,
  3. nowsza wartość.
"""
from app.domain.model import Kanal, WartoscPola, Wystawca

RANGA: dict[Wystawca, int] = {
    Wystawca.ZUS: 5,
    Wystawca.URZAD: 5,
    Wystawca.WYLICZONE: 5,
    Wystawca.SAD: 4,
    Wystawca.PRACODAWCA: 3,
    Wystawca.LEKARZ: 3,
    Wystawca.UZYTKOWNIK: 1,
}
RANGA_NIEPEWNY_ODCZYT = 2


def ranga(w: WartoscPola, prog_pewnosci: float) -> int:
    r = RANGA[w.wystawca]
    if w.kanal == Kanal.UPLOAD and w.pewnosc < prog_pewnosci:
        # Niepewny odczyt AI spada pod dokumenty, ale nigdy nie awansuje ponad swojego wystawcę.
        r = min(r, RANGA_NIEPEWNY_ODCZYT)
    return r


def klucz(w: WartoscPola, prog_pewnosci: float) -> tuple:
    """Klucz sortowania – większy = ważniejszy."""
    return (ranga(w, prog_pewnosci), w.kanal == Kanal.UPLOAD, w.pewnosc, w.utworzono)


def najlepsza(wartosci: list[WartoscPola], prog_pewnosci: float) -> WartoscPola | None:
    return max(wartosci, key=lambda w: klucz(w, prog_pewnosci), default=None)


def uzasadnienie(w: WartoscPola) -> str:
    """Krótkie wyjaśnienie automatycznego wyboru (do „Konfliktów” i „Moich danych”)."""
    if w.wystawca in (Wystawca.ZUS, Wystawca.URZAD):
        return f"Wybraliśmy: {w.zrodlo_opis} – dane z rejestru mają pierwszeństwo."
    if w.wystawca == Wystawca.UZYTKOWNIK and w.kanal == Kanal.UPLOAD:
        return f"Wybraliśmy: {w.zrodlo_opis} – ten wniosek trafił do ZUS, więc ma pierwszeństwo przed odpowiedzią w aplikacji."
    if w.wystawca == Wystawca.UZYTKOWNIK:
        return "Używamy Twojej odpowiedzi – nie mamy tej informacji z innego źródła."
    return f"Wybraliśmy: {w.zrodlo_opis} – dokument ma pierwszeństwo przed danymi wpisanymi ręcznie."
