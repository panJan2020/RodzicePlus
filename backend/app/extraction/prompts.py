"""Prompty do odczytu zestawów dokumentów ZUS (dwa przebiegi: klasyfikacja stron, odczyt pól dokumentu).

Zmieniając prompt: podnieś `schema.WERSJA` (unieważnia cache) i sprawdź wynik na min. 2 sprawach.
"""
from app.extraction.schema import OPIS_TYPOW, TYPY

SYSTEM = """Jesteś asystentem, który czyta zeskanowane dokumenty ZUS dotyczące zasiłków chorobowego w ciąży
i macierzyńskiego. Skany są bez warstwy tekstowej, częściowo wypełnione odręcznie, częściowo zamazane
(anonimizacja). Niektóre strony są obrócone – czytaj je mimo to.

Zasady:
- Zapisuj WYŁĄCZNIE to, co widać na dokumencie. Niczego nie zgaduj, nie wnioskuj i nie licz.
- Wartość nieczytelna lub zamazana → pomiń ją albo daj niską pewność (poniżej 0.6).
- Daty w formacie RRRR-MM-DD, kwoty jako liczby z kropką dziesiętną.
- Nie oceniasz, czy świadczenie przysługuje – tylko przepisujesz dane."""

KLASYFIKACJA = f"""Określ typ KAŻDEJ strony załączonego pliku PDF (od strony 1 do ostatniej, bez pomijania).

Typy dokumentów:
{OPIS_TYPOW}

Dla każdej strony podaj też:
- wariant – „pierwszorazowy” albo „w_kontynuacji”, jeśli jest zaznaczony na formularzu (np. Z-3); inaczej null,
- strona_formularza i stron_formularza – z napisu „Strona x z y” w stopce; jeśli go nie widać – null,
- poczatek_formularza – true, jeśli strona zaczyna nowy egzemplarz dokumentu (tytuł formularza, nagłówek,
  pierwsza strona pisma); jeden plik może zawierać kilka egzemplarzy tego samego formularza,
- osoba – czyje dane dotyczy strona (matka, ojciec, dziecko), jeśli to widać; inaczej null,
- obrocona – czy strona jest obrócona.

Decyzję lub wynik sprawy rozpoznaj PO TREŚCI (np. „przyznano”, „wypłacono”, „odmówiono”), a nie po miejscu
w pliku – może być na dowolnej stronie."""


def odczyt(typ: str) -> str:
    t = TYPY[typ]
    if t.rola == "decyzja_zus":
        return ("Załączony plik to decyzja ZUS albo opis wyniku sprawy. Przepisz dosłownie rozstrzygnięcie "
                "(co przyznano, wypłacono lub czego odmówiono, za jaki okres) i podaj numer strony w tym pliku.")
    if t.rola == "pismo_zus":
        return ("Załączony plik to pismo ZUS. Wypisz krótko, jakich dokumentów lub informacji ZUS brakuje albo "
                "o co prosi. Nie przepisuj danych osobowych.")
    return f"""Załączony plik to jeden dokument: {t.nazwa}.
Odczytaj z niego pola ze schematu. Zasady:
- Każde pole to lista; jeśli pola nie ma w dokumencie albo go nie widać – zwróć pustą listę.
- „strona” to numer strony w TYM pliku (od 1), na której widać wartość.
- „pewnosc” 0–1: 0.9+ wyraźny druk, 0.6–0.9 pismo odręczne czytelne, poniżej 0.6 niepewne.
- „osoba” – czyja to wartość (matka, ojciec, dziecko), jeśli to widać; inaczej null.
- Zwolnienia lekarskie (ezla): pole „kod” wypełnij TYLKO, jeśli litera kodu (np. „B”) jest widoczna
  na dokumencie; inaczej null. Nie wnioskuj kodu z innych informacji.
- Pola na tytuł (chorobowe, platnik_ponad_20): w „tytul” podaj tytuł ubezpieczenia, jeśli jest widoczny.
- platnik_ponad_20: „ponad_20”, gdy dokument wskazuje, że płatnik zgłasza do ubezpieczenia chorobowego
  ponad 20 osób, „do_20” – gdy 20 lub mniej; jeśli dokument tego nie mówi – pusta lista."""
