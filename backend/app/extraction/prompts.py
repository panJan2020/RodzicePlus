"""Prompty do odczytu zestawów dokumentów ZUS (dwa przebiegi: klasyfikacja stron, odczyt pól dokumentu).

Zmieniając prompt: podnieś `schema.WERSJA` (unieważnia cache) i sprawdź wynik na min. 2 sprawach.
"""
from app.extraction.schema import KODY_TYTULU, OPIS_TYPOW, TYPY

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
- obrocona – czy strona jest obrócona,
- opis – kilka słów, czym jest strona (np. „koperta”, „załącznik – kopia dowodu”, „pusta strona”); przy typie „inne”
  opis jest obowiązkowy i konkretny. Nie zmieniaj strony na znany typ, jeśli nie jesteś pewien.

Decyzję lub wynik sprawy rozpoznaj PO TREŚCI (np. „przyznano”, „wypłacono”, „odmówiono”), a nie po miejscu
w pliku – może być na dowolnej stronie."""


_NAZWY_TYTULOW = {"umowa_o_prace": "pracownik / umowa o pracę", "zlecenie": "zleceniobiorca",
                   "dzialalnosc": "działalność pozarolnicza"}
KODY_TYTULU_OPIS = "; ".join(f"{k} = {_NAZWY_TYTULOW[v]}" for k, v in KODY_TYTULU.items())

TYTUL_Z_KODU = f"""
Tytuł ubezpieczenia (okresy_ubezpieczenia, tytuly, chorobowe):
- Czytaj 4-cyfrowy KOD TYTUŁU UBEZPIECZENIA zapisany w dokumencie i wpisz go do „kod_tytulu”. Nie zgaduj tytułu
  z kontekstu (nazwy płatnika, kwot, wyglądu dokumentu).
- Znane kody: {KODY_TYTULU_OPIS}. Inny kod przepisz bez zmian (w „tytul” wtedy „inne”).
- Jeśli kodu nie widać albo jest nieczytelny – kod_tytulu = null, a pewność tego wpisu poniżej 0.6.
- Okres bez daty końca (ubezpieczenie trwa) – „do” = null."""

PODSTAWY = """
Poświadczenie ubezpieczenia – podstawy składek (działalność):
- podstawa_deklarowana: tabela „Podstawa wymiaru składek na ubezpieczenie chorobowe za okres 12 miesięcy…” (pkt 4) –
  jeden wiersz na miesiąc (RRRR-MM): kwota podstawy i czy zaznaczono „wakacje składkowe”.
- podstawa_60_proc (pkt 11): odpowiedź „tak” albo „nie” na pytanie, czy w całym okresie podstawa wynosiła co najmniej
  60% prognozowanego przeciętnego wynagrodzenia. Gdy takiego pytania na dokumencie nie ma – nie dodawaj wpisu."""

ZRZUT = """
Zrzut z systemu ZUS to tabela(e) okresów ubezpieczenia, często obrócona o 90°. Przepisz każdy wiersz okresu
(od, do, kod tytułu, płatnik) do „okresy_ubezpieczenia”; „chorobowe_od” to początek nieprzerwanego ubezpieczenia
chorobowego, jeśli da się go ustalić z wierszy; „tytuly” – tytuły trwających okresów.
Jeśli zrzut przedstawia zwolnienia lekarskie (e-ZLA) – okresy niezdolności od–do wpisz do „ezla”, a literę kodu
niezdolności tylko wtedy, gdy jest widoczna na obrazie (inaczej null, nie wnioskuj jej)."""


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
- Każde widoczne pole skalarne to osobny wpis na liście „pola” (wartość zapisana tekstem w podanym formacie);
  pól, których nie ma w dokumencie albo nie widać, NIE dodawaj. To samo dotyczy tabel (ezla, miesiace,
  okresy_ubezpieczenia): jeden wiersz tabeli = jeden element, bez wierszy, których nie widać.
- „strona” to numer strony w TYM pliku (od 1), na której widać wartość.
- „pewnosc” 0–1: 0.9+ wyraźny druk, 0.6–0.9 pismo odręczne czytelne, poniżej 0.6 niepewne.
- „osoba” (jeśli jest w schemacie) – czyja to wartość (matka, ojciec, dziecko), jeśli to widać; inaczej „nieznana”.
- Zwolnienia lekarskie (ezla): pole „kod” wypełnij TYLKO, jeśli litera kodu (np. „B”) jest widoczna
  na dokumencie; inaczej null. Nie wnioskuj kodu z innych informacji.
- wynagrodzenie_chorobowe_okres (Z-3, „Informacje o wypłaconych świadczeniach” pkt 1, art. 92 Kodeksu pracy):
  tylko gdy zaznaczono TAK – każdy wpisany okres od–do jako osobny wiersz; „kod” tylko jeśli wpisany. Gdy zaznaczono
  NIE albo pole jest puste – nie dodawaj wierszy. Okresy wynagrodzenia i zasiłku (pkt 2) to różne pola.
- Pola na tytuł (chorobowe, platnik_ponad_20): jeśli schemat ma „tytul”, podaj tytuł ubezpieczenia, jeśli jest
  widoczny; inaczej „nieznany”.
- platnik_ponad_20: „ponad_20”, gdy dokument wskazuje, że płatnik zgłasza do ubezpieczenia chorobowego
  ponad 20 osób, „do_20” – gdy 20 lub mniej; jeśli dokument tego nie mówi – pusta lista.""" + (
        TYTUL_Z_KODU + (ZRZUT if t.kod == "zrzut_systemu_ZUS" else "")
        if t.kod in ("poswiadczenie_ubezpieczenia", "zrzut_systemu_ZUS") else "") + (
        PODSTAWY if t.kod == "poswiadczenie_ubezpieczenia" else "")
