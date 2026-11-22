# Słownik pól i katalog pytań – ustalanie prawa i wyliczanie świadczeń

> **Jedyne źródło nazw pól** w projekcie. Z tego pliku powstaje `backend/app/questions/katalog.json`, schematy odczytu
> dokumentów (Claude API), wymagania reguł w `rules/` i parametry w `params/`.
> Model danych: `docs/architektura.md` (rozdz. 3). Funkcje i ekrany: `docs/opis_aplikacji.md`.

Podstawa: treść wyzwania, ustawa zasiłkowa (wyciąg), Kodeks pracy (wyciąg), rozporządzenie z 27.09.2026 r. w sprawie
zakresu informacji i dokumentów (zwł. załączniki 2, 3, 6, 7), rozporządzenie w sprawie wniosków o urlopy, Poradnik ZUS 2026,
załącznik ZUS (wymiary, wysokości, podstawa wymiaru).

---

## 0. Jak czytać

| Kolumna | Znaczenie |
|---|---|
| **ID** | identyfikator pytania (kod, testy, dokumentacja). Pytanie z kilkoma polami ma pod-ID (`B3` + `B3a`); tryb uproszczony ma przyrostek `s` (`O4s`). |
| **Pole** | nazwa pola w `Osoba.pola` – **ta sama** w kreatorze, odczycie skanów, regułach i API |
| **Osoba** | czyje to pole: `rodzic` (osobno dla matki i ojca / drugiego rodzica), `dziecko` (osobno dla każdego dziecka), `wnioskodawca` (osoba, która wnioskuje o dane świadczenie) |
| **Rodzaj** | `fakt` – stan rzeczy, może mieć wiele wartości z różnych źródeł · `plan` – zamiar, **tylko** od użytkownika · `wybór` – decyzja do symulacji, trafia do **scenariusza** (`Scenariusz.wybory`), nie do pól osoby · `wyliczone` – liczy system, użytkownik nie odpowiada |
| **Pokaż, gdy** | warunek wyświetlenia. Niespełniony → pytanie `wykluczone` (wartość zostaje, reguły jej nie używają); czeka na odpowiedź nadrzędną → `zablokowane` |
| **Źródła** | kody źródeł (kanałów), z których może przyjść wartość – patrz niżej |

### Kody źródeł

| Kod | Wystawca | Kanał | Uwagi |
|---|---|---|---|
| `mobywatel` | urząd | mObywatel / PESEL | symulacja |
| `rsc` | urząd | rejestr stanu cywilnego | symulacja |
| `zus_konto` | ZUS | konto ubezpieczonego (zgłoszenia, RCA) | symulacja; w sprawach testowych także strony „poświadczenie ubezpieczenia” i „zrzut systemu ZUS” |
| `zus_platnik` | ZUS | dane płatnika | symulacja |
| `zus_historia` | ZUS | historia świadczeń | symulacja; w sprawach testowych także zrzuty systemu |
| `ezla` | lekarz | e-ZLA | symulacja |
| `pue` | ZUS | PUE / eZUS | symulacja |
| `upload:<typ>` | wg typu dokumentu | upload | np. `upload:Z-3` (wystawca `pracodawca`), `upload:akt` (`urzad`), `upload:zaswiadczenie_lek` (`lekarz`), `upload:postanowienie` (`sad`) |
| `kreator` | użytkownik | kreator / Moje dane | zawsze możliwe dla pól `fakt` i `plan` |
| `wyliczone` | system | – | pola `wyliczone` |

**Hierarchia przy konflikcie** (domyślna aktywna wartość): `zus` / `urzad` > `sad` > `pracodawca` / `lekarz` >
odczyt AI z pewnością < 0,6 > `uzytkownik`. Pola `plan` – tylko `kreator`.

**Kreator nie pyta o pole, które ma już aktywną wartość** z innego źródła.

---

## A. Sytuacja i rola (zawsze)

| ID | Pytanie (odpowiedzi) | Pole | Osoba | Rodzaj | Pokaż, gdy | Po co (reguła / przepis) | Źródła |
|---|---|---|---|---|---|---|---|
| A1 | Jaka jest Twoja sytuacja? (wielokrotny: planuję dziecko / jestem w ciąży / dziecko się urodziło / dziecko urodziło się martwe lub zmarło / przyjąłem(-am) dziecko na wychowanie / opiekuję się dzieckiem lub chorym członkiem rodziny) | `sytuacja[]` | wnioskodawca | fakt | zawsze | wybór ścieżek pytań; `Sprawa.zdarzenie` | kreator, upload:ZAM |
| A2 | Kim jesteś dla dziecka? (matka / ojciec / inny członek najbliższej rodziny / osoba, która przyjęła dziecko i złożyła wniosek o przysposobienie / rodzina zastępcza) | `rola` | rodzic | fakt | zawsze | uprawnienia zależą od roli (art. 29 ust. 1–10 u.z.); = `Osoba.rola` | kreator, upload:ZAM, rsc |
| A3 | Czy drugi rodzic też będzie korzystał z urlopów lub zasiłków? (tak / nie / nie wiem) | `drugi_rodzic_aktywny` | wnioskodawca | plan | A1 ≠ tylko opieka | „tak” → dodanie osoby `ojciec` / `drugi_rodzic` i symulacja podziału (wym. d) | kreator |
| A4 | Data urodzenia | `data_urodzenia` | rodzic, dziecko | fakt | zawsze | wynagrodzenie chorobowe 33 albo 14 dni (art. 92 KP); u dziecka – limity wieku | mobywatel, rsc, upload:akt, upload:ZAM, kreator |

## B. Tytuł ubezpieczenia i ubezpieczenie chorobowe

| ID | Pytanie | Pole | Osoba | Rodzaj | Pokaż, gdy | Po co | Źródła |
|---|---|---|---|---|---|---|---|
| B1 | Na jakiej podstawie pracujesz? (wielokrotny: umowa o pracę / zlecenie lub agencyjna / działalność / współpraca przy działalności / umowa o dzieło / inne / nie pracuję) | `tytuly[]` | rodzic | fakt | zawsze | urlop (tylko pracownik) albo zasiłek „za okres odpowiadający urlopowi”; kto wypłaca; sposób liczenia podstawy | zus_konto, upload:Z-3, upload:Z-3a, kreator |
| B2 | Wymiar etatu | `etat` | rodzic | fakt | B1 ∋ umowa o pracę | minimalna podstawa przy pełnym etacie (art. 45); łączenie z urlopem rodzicielskim | zus_konto, upload:Z-3 (pkt 1), kreator |
| B3 | Rodzaj umowy o pracę i data jej końca (nieokreślony / określony / próbny ponad 1 mies. / na zastępstwo) | `umowa_rodzaj`, `umowa_do` | rodzic | fakt | B1 ∋ umowa o pracę | umowa kończąca się po 3. mies. ciąży przedłuża się do porodu, chyba że to zastępstwo (art. 177 §3, §3¹ KP); zasiłek po ustaniu (art. 30 ust. 4 u.z.) | upload:Z-3 (pkt 1–2), kreator |
| B4 | Czy z danego tytułu podlegasz ubezpieczeniu chorobowemu? (przy zleceniu i działalności tylko dobrowolnie, po zgłoszeniu ZUS ZUA) | `chorobowe[tytul]` | rodzic | fakt | B1 ≠ tylko umowa o pracę | „nie” = brak zasiłków z tego tytułu; przy zbiegu z umową o pracę z co najmniej minimalnym wynagrodzeniem nie można zgłosić się dobrowolnie z działalności ani ze zlecenia (Poradnik) | zus_konto, upload:poswiadczenie, kreator |
| B4a | Czy ubezpieczenie chorobowe jest dobrowolne (zlecenie, działalność – zgłoszenie ZUS ZUA)? | `chorobowe_dobrowolne` | rodzic | fakt | B1 ∋ zlecenie, działalność lub współpraca | okres wyczekiwania 90 dni zamiast 30 (art. 4 ust. 1); przy zbiegu z obowiązkowym ubezpieczeniem liczy się obowiązkowe | zus_konto, upload:poswiadczenie, kreator |
| B5 | Od kiedy nieprzerwanie podlegasz ubezpieczeniu chorobowemu? Czy wcześniejsze okresy dzieliła przerwa do 30 dni (albo urlop wychowawczy lub bezpłatny)? | `chorobowe_od`, `okresy_wczesniejsze[]` | rodzic | fakt | zawsze | okres wyczekiwania 30 albo 90 dni (art. 4 ust. 1–2); liczba pełnych miesięcy do podstawy | zus_konto, upload:poswiadczenie, upload:zrzut_zus, kreator |
| B5a | (bez pytania – podgląd) Okresy ubezpieczenia: tytuł, płatnik, od–do, wymiar etatu, chorobowe, dobrowolne | `okresy_ubezpieczenia[]` | rodzic | fakt | zawsze | ekran „Moje ubezpieczenie” (stan ubezpieczenia na dzień), ubezpieczenie w dniu zdarzenia (B7); element listy: `{tytul, platnik, platnik_ponad_20, od, do, wymiar_etatu, chorobowe, chorobowe_dobrowolne}` | zus_konto, upload:poswiadczenie, upload:zrzut_zus |
| B6 | Czy masz co najmniej 10 lat obowiązkowego ubezpieczenia chorobowego albo zgłosiłeś(-aś) się do ubezpieczenia w ciągu 90 dni od ukończenia szkoły lub uczelni? | `zwolnienie_z_wyczekiwania` | rodzic | fakt | ścieżka zasiłku chorobowego i B5 < 30/90 dni | prawo do zasiłku od 1. dnia (art. 4 ust. 3) | zus_konto, kreator |
| B7 | Czy w dniu porodu (przyjęcia dziecka) będziesz ubezpieczony(-a) chorobowo albo na urlopie wychowawczym? | `ubezpieczony_w_dniu_zdarzenia` | rodzic | **wyliczone** | ścieżki zasiłku macierzyńskiego | warunek konieczny (art. 29 ust. 1); wyjątki w sekcji F. Liczone z B3, B5, S3 i daty zdarzenia; jeśli zdarzenie w przyszłości → wynik **`warunkowo`** | wyliczone |
| B8 | Zadłużenie składkowe na dzień powstania prawa | `zadluzenie_kwota` | rodzic | fakt | B1 ∋ działalność lub współpraca | powyżej 1% minimalnego wynagrodzenia świadczenie nie przysługuje do spłaty; brak spłaty przez 6 mies. = przedawnienie (art. 2a) | zus_platnik (zaświadczenie o zadłużeniu) |
| B9 | Czy korzystasz z „ulgi na start”? | `ulga_na_start` | rodzic | fakt | B1 ∋ działalność | brak ubezpieczeń = brak zasiłków (Poradnik) | zus_konto, kreator |
| B10 | Czy masz prawo do emerytury, renty z tytułu niezdolności do pracy, zasiłku dla bezrobotnych, świadczenia lub zasiłku przedemerytalnego, rodzicielskiego świadczenia uzupełniającego albo nauczycielskiego świadczenia kompensacyjnego? | `inne_swiadczenia[]` | rodzic | fakt | ścieżki zasiłku chorobowego po ustaniu i świadczenia rehabilitacyjnego | wyłączenia (art. 13 ust. 1, art. 18 ust. 7) | zus_historia, kreator |
| B11 | Czy w okresie zwolnienia jesteś na urlopie bezpłatnym, wychowawczym albo opiekuńczym? | `urlop_bez_zasilku` | rodzic | fakt | ścieżka zasiłku chorobowego | zasiłek za te okresy nie przysługuje (art. 12 ust. 2) | upload:Z-3 (pkt 5), kreator |

## C. Kto ustala i wypłaca zasiłek

| ID | Pytanie | Pole | Osoba | Rodzaj | Pokaż, gdy | Po co | Źródła |
|---|---|---|---|---|---|---|---|
| C1 | Ilu ubezpieczonych zgłaszał Twój płatnik do ubezpieczenia chorobowego na 30 listopada poprzedniego roku? (ponad 20 / najwyżej 20 / nie wiem) | `platnik_ponad_20[tytul]` | rodzic | fakt | B1 ∋ umowa o pracę lub zlecenie | wejście do C2 | zus_platnik, upload:Z-3 („Pozostałe informacje”), kreator |
| C2 | Kto wypłaca? (płatnik / ZUS) | `kto_wyplaca[tytul]` | rodzic | **wyliczone** | B1 niepuste | ponad 20 → płatnik; w innym razie, przy działalności i po ustaniu ubezpieczenia → ZUS (art. 61). Od tego zależą kroki poradnika i „gdzie złożyć” (wym. g) | wyliczone |

## D. Ciąża – zasiłek chorobowy

| ID | Pytanie | Pole | Osoba | Rodzaj | Pokaż, gdy | Po co | Źródła |
|---|---|---|---|---|---|---|---|
| D1 | Zwolnienia lekarskie e-ZLA w ciąży: okresy od–do i czy mają kod „B” (okresy z kilku dokumentów tego samego wystawcy scalamy w jedną wartość – sąsiednie i nakładające się; nakładanie to ostrzeżenie, nie konflikt) | `ezla[]` | rodzic (matka) | fakt | A1 ∋ ciąża | 100% z kodem B (art. 11 ust. 2); okres zasiłkowy 270 dni (art. 8); każdy dzień płatny, także wolny (art. 11 ust. 4) | ezla, upload:ZAS-53, upload:Z-3 (okresy), upload:ZAS-12, upload:zrzut_zus (e-ZLA; kod tylko z obrazu), kreator |
| D1a | Czy zwolnienie lekarskie ma kod „B” (ciąża)? | `ezla_kod_b` | rodzic (matka) | fakt | A1 ∋ ciąża | kod nie zmienia PRAWA, tylko stawkę: 100% z kodem B, 80% bez niego (art. 11 ust. 2). Pytamy, gdy kodu nie widać na dokumentach – nigdy go nie zgadujemy | kreator |
| D2 | Czy przed zwolnieniami z kodem B były zwolnienia bez kodu B? Kiedy się skończyły? | `ezla_przed_ciaza[]` | rodzic (matka) | fakt | D1 niepuste | okresów sprzed przerwy nie wlicza się do okresu zasiłkowego, jeśli po przerwie niezdolność przypada w ciąży (art. 9 ust. 2) | ezla, kreator |
| D3 | Ile dni wynagrodzenia chorobowego wypłacił pracodawca w tym roku kalendarzowym? | `dni_wynagr_chorobowego_rok` | rodzic | fakt | B1 ∋ umowa o pracę | pierwsze 33 dni (14 dni po roku, w którym skończyłaś 50 lat) płaci pracodawca, potem zasiłek (art. 92 KP). **Reguła zasiłku chorobowego tego pola nie używa** (znaczenie do wyjaśnienia – sekcja Z); druk Z-3 nie podaje liczby dni, tylko okresy (D3a) | zus_historia, kreator |
| D3a | Za jakie okresy pracodawca wypłacił wynagrodzenie chorobowe? | `wynagrodzenie_chorobowe_okres[]` (od, do, kod) | rodzic | fakt | A1 ∋ ciąża i B1 ∋ umowa o pracę | koniec płatności pracodawcy i początek zasiłku (art. 92 KP); 33 dni (14 po 50. r.ż.) to kontrola i rezerwa, gdy okresu brak (wynik orientacyjny). Druk Z-3, „Informacje o wypłaconych świadczeniach” pkt 1: „okresy od–do oraz kod literowy”, także okresy z poprzedniego roku wliczane do jednego okresu zasiłkowego | upload:Z-3 |
| D4 | Czy niezdolność do pracy powstała po ustaniu tytułu ubezpieczenia? Data ustania, data początku niezdolności, czy trwała co najmniej 30 dni bez przerwy | `po_ustaniu{}` | rodzic | fakt | D1 i ustał tytuł | prawo, jeśli niezdolność powstała do 14 dni od ustania (art. 7); w ciąży bez limitu 91 dni (art. 8 ust. 2) | upload:ZAS-53, zus_konto, kreator |
| D5 | Czy po ustaniu tytułu kontynuujesz albo podjęłaś działalność zarobkową? | `praca_po_ustaniu` | rodzic | fakt | D4 = tak | wyłącza zasiłek za okres po ustaniu (art. 13 ust. 1 pkt 2) | kreator |
| D6 | Czy w czasie zwolnienia wykonujesz pracę zarobkową (także z innego tytułu)? | `praca_na_zwolnieniu` | rodzic | fakt | D1 niepuste | utrata zasiłku za całe zwolnienie (art. 17); od 2027 r. można nie wystawiać zwolnienia z tytułu, w którym da się pracować (art. 17 ust. 1d–1e) | kreator (ostrzeżenie) |

## E. Świadczenie rehabilitacyjne

| ID | Pytanie | Pole | Osoba | Rodzaj | Pokaż, gdy | Po co | Źródła |
|---|---|---|---|---|---|---|---|
| E1 | Czy wyczerpałaś okres zasiłkowy (270 dni) i nadal jesteś niezdolna do pracy? | `okres_wyczerpany` | rodzic | **wyliczone** (z D1, D2) + fakt (dalsza niezdolność) | suma D1 ≥ 250 dni albo pytanie użytkownika | warunek prawa (art. 18 ust. 1) | wyliczone, kreator |
| E2 | Czy lekarz prowadzący ocenia, że dalsze leczenie lub rehabilitacja rokują odzyskanie zdolności do pracy? | `rokowanie` | rodzic | fakt | E1 = tak | o prawie decyduje lekarz orzecznik ZUS (art. 18 ust. 3) → wynik najwyżej `warunkowo` | kreator, upload:zaswiadczenie_lek |
| E3 | Czy niezdolność nadal przypada w ciąży? | `rehab_w_ciazy` | rodzic | fakt | E1 = tak | 100% w ciąży; w innym razie 90% przez 3 mies., potem 75%; maks. 12 mies. (art. 18 ust. 2, art. 19 ust. 1) | kreator, ezla |
| E4 | Data rozpoczęcia świadczenia | `rehab_od` | rodzic | fakt | E1 = tak | waloryzacja podstawy według kwartału (art. 19 ust. 2) | kreator, zus_historia |

Wyłączenia: pytanie B10.

## F. Utrata pracy w ciąży (zasiłek w wysokości zasiłku macierzyńskiego)

| ID | Pytanie | Pole | Osoba | Rodzaj | Pokaż, gdy | Po co | Źródła |
|---|---|---|---|---|---|---|---|
| F1 | Czy umowa o pracę ustała w czasie ciąży? Kiedy? | `ustanie_data` | rodzic (matka) | fakt | A1 ∋ ciąża i B1 ∋ umowa o pracę | ścieżka art. 30 | zus_konto, upload:swiadectwo_pracy, kreator |
| F2 | Z jakiej przyczyny? (upadłość / likwidacja / śmierć pracodawcy / rozwiązanie z naruszeniem prawa potwierdzone prawomocnym wyrokiem / inna) | `ustanie_przyczyna` | rodzic (matka) | fakt | F1 = tak | upadłość, likwidacja, śmierć → zasiłek w wysokości zasiłku macierzyńskiego do porodu (art. 30 ust. 3); cztery wymienione → zasiłek macierzyński po porodzie (art. 30 ust. 1); „inna” → brak | upload:wyrok, upload:swiadectwo_pracy, kreator |
| F3 | Czy zapewniono Ci inne zatrudnienie? | `inne_zatrudnienie` | rodzic (matka) | fakt | F2 ∈ {upadłość, likwidacja, śmierć} | warunek art. 30 ust. 3 | kreator, zus_konto |
| F4 | Czy ciążę stwierdzono zaświadczeniem lekarskim w czasie zatrudnienia? | `ciaza_w_zatrudnieniu` | rodzic (matka) | fakt | F1 = tak | wymagany dokument (§15, §17 rozporządzenia) | upload:zaswiadczenie_lek, kreator |

## G. Poród i dziecko

| ID | Pytanie | Pole | Osoba | Rodzaj | Pokaż, gdy | Po co | Źródła |
|---|---|---|---|---|---|---|---|
| G1 | Przewidywana data porodu | `pdp` | rodzic (matka) | fakt | A1 ∋ ciąża | urlop do 6 tyg. przed porodem; 3. miesiąc ciąży przy B3; oś czasu; data zdarzenia dla B7, dopóki nie ma G2 | upload:zaswiadczenie_lek, kreator |
| G2 | Data porodu | `data_porodu` | rodzic (matka) | fakt | A1 ∋ urodzenie | początek urlopu (art. 183¹ §2 KP); termin 21 dni na 81,5%; limity wieku. **Niespójność**, jeśli ≠ `data_urodzenia` dziecka | rsc, upload:akt, upload:ZAM, kreator |
| G3 | Ile dzieci urodziło się przy jednym porodzie? | `liczba_dzieci` | rodzic (matka) | fakt | A1 ∋ urodzenie lub ciąża | urlop macierzyński 20/31/33/35/37 tyg.; rodzicielski 41 albo 43 tyg. **Niespójność**, jeśli po porodzie ≠ liczbie osób `dziecko` | rsc, upload:ZAM, upload:akt, kreator |
| G4 | Czy dziecko ma zaświadczenie „Za życiem”? | `za_zyciem` | dziecko | fakt | A1 ∋ urodzenie lub przyjęcie | rodzicielski 65/67 tyg. (62 przy przyjęciu); limity łączenia z pracą 130/134 tyg. | upload:za_zyciem, upload:ZAM, kreator |
| G5 | Czy dziecko zostało porzucone albo umieszczone (orzeczeniem sądu) w pieczy zastępczej, zakładzie opiekuńczo-leczniczym, pielęgnacyjno-opiekuńczym lub rehabilitacji leczniczej? Kiedy? | `umieszczenie_data` | dziecko | fakt | A1 ∋ urodzenie | matce nie przysługuje część urlopu po tej dacie, ale co najmniej 8 tyg. po porodzie (art. 182 KP) | upload:postanowienie, kreator |

## H. Wcześniak albo hospitalizacja dziecka (uzupełniający urlop macierzyński)

| ID | Pytanie | Pole | Osoba | Rodzaj | Pokaż, gdy | Po co | Źródła |
|---|---|---|---|---|---|---|---|
| H1 | W którym tygodniu ciąży urodziło się dziecko? | `tydzien_ciazy` | dziecko | fakt | A1 ∋ urodzenie i dziecko było w szpitalu | przed 28. tyg. → do 15. tyg. po porodzie; 28–37 tyg. i ponad 1000 g → do 8. tyg.; po 37. tyg. → od 5. dnia do 8. tyg. (art. 180² KP) | upload:karta_szpitala, kreator |
| H2 | Masa urodzeniowa (g) | `masa_g` | dziecko | fakt | jw. | do 1000 g → wariant do 15. tyg.; przy wieloraczkach liczy się najniższa masa (min. po dzieciach) | upload:karta_szpitala, kreator |
| H3 | Okresy pobytu w szpitalu po porodzie (od–do) | `hospitalizacje[]` | dziecko | fakt | jw. | tydzień urlopu za tydzień pobytu, okresy się sumuje, niepełny tydzień w górę; po 37. tyg. co najmniej 2 kolejne dni, z pierwszym w 5.–28. dniu; przy wieloraczkach najdłuższa hospitalizacja | upload:karta_szpitala, kreator |
| H4 | Kto skorzysta (matka / ojciec)? Czy drugi rodzic oświadcza, że nie skorzysta? | `uzup_kto` → **wybór**; `uzup_oswiadczenie_drugiego` → fakt | rodzic | wybór + fakt | jw. | tylko jeden rodzic, jednorazowo, bezpośrednio po urlopie macierzyńskim | scenariusz; upload:oswiadczenie, kreator |
| H5 | (przy przyjęciu) Czy pobyt w szpitalu był już po przyjęciu na wychowanie? | `hosp_po_przyjeciu` | dziecko | fakt | A1 ∋ przyjęcie | warunek art. 183 §3¹ KP | kreator |

## I. Martwe urodzenie lub zgon dziecka

| ID | Pytanie | Pole | Osoba | Rodzaj | Pokaż, gdy | Po co | Źródła |
|---|---|---|---|---|---|---|---|
| I1 | Czy dziecko urodziło się martwe? | `martwe_urodzenie` | dziecko | fakt | A1 ∋ martwe lub zgon | 8 tyg. po porodzie (art. 180¹ §1 KP) | rsc, upload:akt, upload:zaswiadczenie_lek, kreator |
| I2 | Data zgonu dziecka | `data_zgonu` | dziecko | fakt | A1 ∋ martwe lub zgon | zgon przed 8. tyg. życia → 8 tyg. po porodzie, ale co najmniej 7 dni od zgonu; później → 7 dni od zgonu | rsc, upload:akt_zgonu, kreator |
| I3 | Ile dzieci z tego porodu żyje? | `dzieci_zyjace` | rodzic (matka) | **wyliczone** (z I1, I2 dzieci) | G3 > 1 | wymiar urlopu według liczby żyjących dzieci | wyliczone |

Dodatkowa informacja (poza listą świadczeń, treść w `content/`): przy martwym urodzeniu przysługuje zasiłek pogrzebowy
(kwota w parametrach). Ton komunikatów: spokojny, bez wykrzykników.

## J. Urlop macierzyński – plan i wariant wypłaty

| ID | Pytanie | Pole | Osoba | Rodzaj | Pokaż, gdy | Po co | Źródła |
|---|---|---|---|---|---|---|---|
| J1 | Czy chcesz zacząć urlop (zasiłek) przed porodem? Od kiedy? | `macierzynski_od` → `wybory.start_urlopu_macierzynskiego` | rodzic (matka) | **wybór** (fakt, gdy już udzielony – Z-3 pkt 6, ZAM) | A1 ∋ ciąża i A2 = matka | najwyżej 6 tyg. przed porodem; potrzebne zaświadczenie o przewidywanej dacie porodu; wniosek 14 dni przed | scenariusz; upload:Z-3, upload:ZAM |
| J2 | Wariant wypłaty: 81,5% za cały okres czy 100% + 70%? Data złożenia wniosku | `wariant` → `wybory.wniosek_81_5`; `wniosek_81_5_data` → fakt | rodzic | **wybór** + fakt (data złożonego wniosku) | ścieżki macierzyński i rodzicielski | 81,5% tylko przy wniosku do 21 dni po porodzie (przyjęciu); 9 tyg. drugiego rodzica zawsze 70% (art. 30a, art. 31 ust. 3, 3f) | scenariusz; upload:ZAM, upload:Z-3 (pkt 6 „data złożenia wniosku”) |
| J3 | Czy co najmniej jeden dzień urlopu rodzicielskiego wykorzystasz przed 1. urodzinami dziecka? | `rodz_w_1_roku` | rodzic | **wyliczone** (z `wybory.podzial_rodzicielskiego`) | J2 = 81,5% | jeśli nie: rodzicielski po 70%, a macierzyński wyrównywany do 100% na wniosek (art. 31 ust. 3g, ust. 4; zał. 6 pkt 15) | wyliczone |
| J4 | Czy matka wróci do pracy po co najmniej 14 tyg. i odda resztę urlopu ojcu? Od kiedy? | `rezygnacja_od` → `wybory.przejecie_macierzynskiego_przez` | rodzic | **wybór** | A3 = tak | art. 180 §4–5 KP, art. 29 ust. 3 u.z.; wniosek o rezygnację 7 dni przed powrotem, wniosek ojca 14 dni przed | scenariusz |

## K. Szczególne sytuacje matki (prawa ojca albo członka rodziny)

| ID | Pytanie | Pole | Osoba | Rodzaj | Pokaż, gdy | Po co | Źródła |
|---|---|---|---|---|---|---|---|
| K1 | Czy matka dziecka ma tytuł do ubezpieczenia chorobowego? | `matka_ubezpieczona` | wnioskodawca (≠ matka) | fakt | A2 ≠ matka | ścieżki: ubezpieczona (art. 29 ust. 3–7) i bez tytułu (ust. 9–10); rodzicielski ojca, gdy matka nieubezpieczona. Jeśli matka jest osobą w sprawie → **wyliczone** z jej pól B | wyliczone, kreator |
| K2 | Czy matka ma orzeczenie o niezdolności do samodzielnej egzystencji? | `matka_nse` | wnioskodawca (≠ matka) | fakt | A2 ≠ matka | przejęcie urlopu po 8 tyg. (art. 29 ust. 5, art. 180 §6–7 KP) | upload:orzeczenie, kreator |
| K3 | Czy matka przebywa w szpitalu i nie może opiekować się dzieckiem? Daty przyjęcia i wypisu | `matka_szpital[]` | wnioskodawca (≠ matka) | fakt | A2 ≠ matka | ojciec przejmuje zasiłek za ten okres po 8 tyg. (art. 29 ust. 6, art. 180 §10–11 KP) | upload:karta_szpitala, kreator |
| K4 | Czy matka zmarła albo porzuciła dziecko? Data | `matka_zgon_porzucenie` | wnioskodawca (≠ matka) | fakt | A2 ≠ matka | przejęcie od dnia zdarzenia; przy porzuceniu nie wcześniej niż po 8 tyg. (art. 29 ust. 7 i 9) | rsc, upload:akt_zgonu, kreator |
| K5 | (matka bez tytułu) Czy matka podjęła zatrudnienie na co najmniej pół etatu? Od–do | `matka_zatrudnienie` | wnioskodawca (≠ matka) | fakt | K1 = nie | ojciec dostaje zasiłek do wyczerpania wymiaru, najdłużej na czas jej zatrudnienia (art. 29 ust. 10, art. 180 §17 KP) | kreator, upload:oswiadczenie |
| K6 | Czy ojciec (członek rodziny) przerwie działalność zarobkową, żeby opiekować się dzieckiem, albo dostanie urlop od pracodawcy? | `przerwanie_dzialalnosci` | wnioskodawca (≠ matka) | plan | A2 ≠ matka | warunek przejęcia zasiłku przez osobę, która nie jest pracownikiem | kreator |
| K7 | Za jaki okres i w jakiej stawce wypłacono już zasiłek matce? | `wyplacono_matce{}` | wnioskodawca (≠ matka) | fakt | A2 ≠ matka | okres zasiłku ojca zmniejsza się o okres wypłacony matce (art. 29a ust. 2) | zus_historia, upload:Z-3 (matki), kreator |

## L. Urlop rodzicielski – podział i łączenie z pracą

| ID | Pytanie | Pole | Osoba | Rodzaj | Pokaż, gdy | Po co | Źródła |
|---|---|---|---|---|---|---|---|
| L1 | Plan części urlopu: dla każdej części kto, od–do, czy jednocześnie z drugim rodzicem | `rodzicielski_czesci[]` → `wybory.podzial_rodzicielskiego` | sprawa | **wybór** | ścieżka rodzicielska | pula 41/43 (65/67) tyg. wspólna; po 9 tyg. nieprzenoszalnych dla każdego rodzica; razem najwyżej 5 części; do końca roku, w którym dziecko kończy 6 lat; przy jednoczesnym korzystaniu łączny wymiar nie przekracza puli (art. 182¹a, 182¹c KP; art. 29a ust. 3) | scenariusz |
| L2 | Ile urlopu rodzicielskiego już wykorzystano (tygodnie, liczba części, stawka)? | `rodzicielski_wykorzystany{}` | rodzic | fakt | ścieżka rodzicielska | limit części i puli; liczą się także wnioski osób, które nie są pracownikami (art. 182¹d §2 KP) | zus_historia, upload:Z-3, upload:ZAM, kreator |
| L3 | Czy w trakcie części urlopu będziesz pracować u tego samego pracodawcy? W jakim wymiarze (najwyżej ½) i przez ile tygodni? | `laczenie_praca[]` → `wybory.podzial_rodzicielskiego[].praca_wymiar` | rodzic | **wybór** (fakt, gdy już udzielony – Z-3 pkt 7) | B1 ∋ umowa o pracę | zasiłek maleje proporcjonalnie (art. 31 ust. 4a); urlop wydłuża się o liczbę tygodni × wymiar, najwyżej do 82/86 (130/134) tyg. (art. 182¹e–f KP) | scenariusz; upload:Z-3 |
| L4 | Czy wydłużoną część urlopu też chcesz łączyć z pracą? W jakim wymiarze? | `laczenie_wydluzenia` → `wybory.podzial_rodzicielskiego[].praca_wymiar_wydluzenia` | rodzic | **wybór** | L3 niepuste | wzór art. 182¹f §7 KP (długość ÷ (1 − wymiar)) | scenariusz |

## M. Urlop ojcowski

| ID | Pytanie | Pole | Osoba | Rodzaj | Pokaż, gdy | Po co | Źródła |
|---|---|---|---|---|---|---|---|
| M1 | Plan: 14 dni jednorazowo czy 2 części po co najmniej 7 dni? Daty | `ojcowski_czesci[]` → `wybory.urlop_ojcowski` | rodzic (ojciec) | **wybór** | A2 = ojciec | 2 tyg. ze 100%; do ukończenia przez dziecko 12 mies.; liczba dzieci nie wydłuża urlopu (art. 182³ KP) | scenariusz; upload:ZAO (archiwalny), upload:ZAM |
| M2 | Czy wykorzystałeś już część urlopu ojcowskiego? Czy zasiłek za urlop ojcowski pobrałeś z innego tytułu? | `ojcowski_wykorzystany`, `ojcowski_inny_tytul` | rodzic (ojciec) | fakt | A2 = ojciec | limit 14 dni; wymagane oświadczenie (§33 rozporządzenia) | zus_historia, kreator |
| M3 | (adopcja) Data uprawomocnienia postanowienia o przysposobieniu | `przysposobienie_prawomocne` | dziecko | fakt | A1 ∋ przyjęcie i A2 = ojciec | 12 mies. od uprawomocnienia, najpóźniej do 14. urodzin dziecka | upload:postanowienie, kreator |

## N. Przyjęcie dziecka na wychowanie (adopcja, rodzina zastępcza)

| ID | Pytanie | Pole | Osoba | Rodzaj | Pokaż, gdy | Po co | Źródła |
|---|---|---|---|---|---|---|---|
| N1 | Forma przyjęcia (przysposobienie z wnioskiem do sądu / rodzina zastępcza niezawodowa / zawodowa / inna) | `forma_przyjecia` | rodzic | fakt | A1 ∋ przyjęcie | zawodowa rodzina zastępcza i „inna” → brak prawa (art. 29 ust. 1 pkt 2–3); `Sprawa.zdarzenie` | upload:postanowienie, upload:umowa_starosta, kreator |
| N2 | Data przyjęcia dziecka na wychowanie | `data_przyjecia` | dziecko | fakt | A1 ∋ przyjęcie | początek uprawnień; wniosek o urlop 7 dni od przyjęcia, start najpóźniej po 21 dniach (art. 183 §6 KP); 81,5% przy wniosku do 21 dni | upload:postanowienie, upload:oswiadczenie, kreator |
| N3 | Data wystąpienia do sądu o przysposobienie | `data_wniosku_sad` | dziecko | fakt | N1 = przysposobienie | warunek prawa | upload:zaswiadczenie_sadu, kreator |
| N4 | Data urodzenia dziecka | `data_urodzenia` (pole A4 osoby `dziecko`; dawniej `dziecko_data_ur[]`) | dziecko | fakt | A1 ∋ przyjęcie | rodzina zastępcza: do 7 lat (10 przy odroczeniu); przysposobienie: do 14 lat; urlop kończy się z limitem wieku, ale trwa co najmniej 9 tyg.; wtedy rodzicielski 38 (62) tyg. (art. 183 §1–4² KP) | rsc, upload:akt, kreator |
| N5 | Czy dziecku odroczono obowiązek szkolny? | `odroczenie_szkolne` | dziecko | fakt | N1 = rodzina zastępcza | limit 10 lat | upload:decyzja, kreator |
| N6 | Ile dzieci przyjęto jednocześnie? | `liczba_przyjetych` | rodzic | **wyliczone** (liczba osób `dziecko` z tą samą `data_przyjecia`) | A1 ∋ przyjęcie | 20/31/33/35/37 tyg.; rodzicielski 41/43 | wyliczone, kreator |
| N7 | Czy jako rodzina zastępcza korzystałeś(-aś) już z urlopu na warunkach urlopu macierzyńskiego lub rodzicielskiego dla tego dziecka? Ile? | `wykorzystane_jako_rz{}` | rodzic | fakt | N1 = przysposobienie | wymiar zmniejsza się o wykorzystane okresy (art. 183 §7–8 KP) | zus_historia, kreator |

Pytania wspólne: G4 („Za życiem”), J2 (81,5% liczone od przyjęcia), L1–L4, M3.

## O. Podstawa wymiaru – pracownik

| ID | Pytanie | Pole | Osoba | Rodzaj | Pokaż, gdy | Po co | Źródła |
|---|---|---|---|---|---|---|---|
| O1 | Data powstania prawa do zasiłku | `data_prawa` | rodzic | **wyliczone** (pierwszy dzień zwolnienia, porodu albo przyjęcia) | zawsze przy kwocie | wyznacza 12 miesięcy kalendarzowych wstecz (art. 36 ust. 1) i wersję parametrów | wyliczone |
| O2 | (bez pytania – podgląd) Czy tuż przed (przerwa krótsza niż miesiąc kalendarzowy) pobierałaś inny zasiłek? Jaka była jego podstawa? | `poprzedni_zasilek{data_do, podstawa}` | rodzic | fakt | zawsze przy kwocie | podstawy nie ustala się na nowo (art. 43), chyba że zmienił się wymiar etatu | zus_historia, upload:Z-3, upload:decyzja, kreator |
| O3 | Od kiedy jesteś zatrudniony(-a) u tego płatnika bez przerwy? | `zatrudnienie_od` | rodzic | fakt | B1 ∋ umowa o pracę | krócej niż 12 mies. → pełne miesiące; krócej niż 1 mies. → wynagrodzenie z umowy (art. 36 ust. 2, art. 37) | zus_konto, upload:Z-3 (pkt 1), kreator |
| O4 | (bez pytania – podgląd) Wynagrodzenie za każdy z 12 miesięcy: składniki stałe, zmienne, dni przepracowane i obowiązujące | `miesiace[]` | rodzic | fakt | B1 ∋ umowa o pracę | miesiące z mniej niż połową czasu pracy pomija się; pozostałe uzupełnia się do pełnego miesiąca; minus 13,71% (art. 38, załącznik ZUS). Element listy: `{miesiac: "RRRR-MM", skladniki_stale, skladniki_zmienne, dni_przepracowane, dni_obowiazujace, stale_pelna_kwota}` (kwoty jako tekst, dni jako liczby) | upload:Z-3 („Składniki wynagrodzenia” pkt 1), zus_konto (RCA – przybliżenie) · kreator: tryb uproszczony `O4s` „średnie brutto z 12 mies.” → wynik **orientacyjny** |
| O4s | (tryb uproszczony O4) Średnie miesięczne wynagrodzenie brutto z ostatnich 12 miesięcy | `srednie_wynagrodzenie_brutto` | rodzic | fakt | B1 ∋ umowa o pracę i brak `miesiace[]` | podstawa wymiaru w przybliżeniu → wynik **orientacyjny**; pełne wyliczenie z `miesiace[]` | zus_konto (RCA – przybliżenie), kreator |
| O5 | Premie i nagrody kwartalne (4 kwartały) oraz roczne (poprzedni rok) | `premie_kwartalne[]`, `premie_roczne` | rodzic | fakt | jw. | doliczane po 1/12 (art. 42) | upload:Z-3 (pkt 2–3), kreator |
| O6 | Czy któreś składniki przysługują też w czasie zasiłku albo tylko do określonego terminu? | `skladniki_wylaczone[]` | rodzic | fakt | jw. | pomija się je w podstawie (art. 41) | upload:Z-3, kreator |
| O7 | Czy w tym okresie zmienił się wymiar etatu? Kiedy? | `zmiana_etatu{data, nowy}` | rodzic | fakt | jw. | podstawa według nowego wymiaru (art. 40) | zus_konto, upload:Z-3 (pkt 1), kreator |
| O8 | Czy u tego pracodawcy masz też umowę zlecenia lub o dzieło? Kwoty za kolejne miesiące | `umowy_u_pracodawcy[]` | rodzic | fakt | jw. | przychód wliczany do podstawy | upload:Z-3 (pkt 5 „Składniki”), kreator |

Reguły bez pytań: podstawa przy pełnym etacie nie niższa niż minimalne wynagrodzenie minus 13,71% (art. 45 ust. 1); przy niepełnym etacie parametr `art45_niepelny_etat` (`proporcjonalnie` – domyślnie, z komentarzy, albo `brak`); gdy ta reguła zmienia podstawę, wynik jest orientacyjny, a w uwagach jest drugi wariant (sekcja Z, pyt. 15);
dzienna stawka = 1/30 podstawy (art. 36 ust. 3).

## P. Podstawa wymiaru – zleceniobiorca

| ID | Pytanie | Pole | Osoba | Rodzaj | Pokaż, gdy | Po co | Źródła |
|---|---|---|---|---|---|---|---|
| P1 | Przychód (podstawa składek) za każdy z 12 miesięcy oraz dni przepracowane i obowiązujące | `przychod_miesiace[]` | rodzic | fakt | B1 ∋ zlecenie | średnia minus 13,71% (art. 48, art. 3 pkt 4); miesiące z pracą krótszą niż pół miesiąca przez zasiłki są pomijane (art. 50) | upload:Z-3a (pkt 14), zus_konto (RCA), kreator |
| P2 | Czy to kolejne umowy z tym samym zleceniodawcą bez przerwy? | `ciaglosc_zlecen` | rodzic | fakt | B1 ∋ zlecenie | okres nieprzerwanego ubezpieczenia (Poradnik) | zus_konto, upload:Z-3a, kreator |
| P3 | Jeśli zachorowałaś (urodziłaś) w pierwszym miesiącu: kwota przychodu z umowy za ten miesiąc | `przychod_umowny` | rodzic | fakt | ubezpieczenie krótsze niż miesiąc | art. 49 ust. 1 pkt 2 | upload:umowa, kreator |
| P4 | Czy przed tym ubezpieczeniem było inne, zakończone najwyżej 30 dni wcześniej? | `poprzedni_tytul_30dni` | rodzic | fakt (zus) / wyliczone z B5 | ubezpieczenie krótsze niż 12 mies. | łączenie okresów (art. 48a ust. 2, art. 49 ust. 2) | zus_konto, kreator |

## Q. Podstawa wymiaru – działalność gospodarcza

| ID | Pytanie | Pole | Osoba | Rodzaj | Pokaż, gdy | Po co | Źródła |
|---|---|---|---|---|---|---|---|
| Q1 | Podstawa składki chorobowej za każdy z ostatnich 12 miesięcy (miesiąc, kwota, wakacje składkowe) | `podstawa_deklarowana[]` `{miesiac, podstawa, wakacje_skladkowe}` | rodzic | fakt | B1 ∋ działalność | średnia z 12 miesięcy minus 13,71%, z limitem maksymalnej podstawy (parametr). **W próbce z działalnością tabela jest w poświadczeniu ZUS (pkt 4), nie w Z-3b** (Z-3b z próbki nie ma pól o podstawie) | zus_konto, upload:poswiadczenie (pkt 4), upload:Z-3b (archiwalny) |
| Q1s | (tryb uproszczony Q1) Średnia zadeklarowana podstawa składki chorobowej z ostatnich 12 miesięcy | `podstawa_deklarowana_srednia` | rodzic | fakt | B1 ∋ działalność i brak `podstawa_deklarowana[]` | podstawa wymiaru w przybliżeniu → wynik **orientacyjny** | zus_konto, kreator |
| Q2 | Rodzaj składek: standardowe / preferencyjne / mały ZUS+ / dobrowolnie wyższa podstawa | `rodzaj_skladek` | rodzic | fakt | jw. | potrzebne do art. 48a (najniższa podstawa) – wzór **do potwierdzenia z aktualnym tekstem ustawy** (sekcja Z, pyt. 17) | zus_konto, kreator |
| Q3 | Liczba pełnych miesięcy ubezpieczenia chorobowego z tytułu działalności | `miesiace_ubezpieczenia` | rodzic | **wyliczone** (z B5) / zus | jw. | poniżej 12 → może mieć zastosowanie art. 48a (obowiązuje od 1.01.2016; orzecznictwo SN: II USKP 227/21, III UK 193/19) – dotyczy osób niebędących pracownikami, gdy ubezpieczenie chorobowe zaczęło się po raz pierwszy lub po przerwie. **Wzór nie jest potwierdzony – w 2c kwoty w tym przypadku nie liczymy**, tylko ostrzegamy | wyliczone, zus_konto |
| Q6 | Czy w całym okresie ubezpieczenia podstawa składki chorobowej wynosiła co najmniej 60% prognozowanego przeciętnego wynagrodzenia? | `podstawa_60_proc` | rodzic | fakt | B1 ∋ działalność | nie → może mieć zastosowanie art. 48a, więc kwoty nie liczymy (poświadczenie ZUS, pkt 11; znaczenie progu do wyjaśnienia – sekcja Z, pyt. 18) | upload:poswiadczenie, kreator |
| Q4 | Czy były przerwy w ubezpieczeniu z powodu nieopłacenia albo spóźnienia składki? | `przerwy_skladkowe[]` | rodzic | fakt | jw. | uwzględnia się wtedy także miesiące sprzed przerwy (art. 48a ust. 4) | zus_konto, kreator |
| Q5 | Czy w okresie obliczeniowym były miesiące, w których przez zasiłki prowadziłaś działalność krócej niż pół miesiąca? | `miesiace_niepelne[]` | rodzic | fakt / wyliczone z zus_historia | jw. | wyłączenie z podstawy (art. 50) | zus_historia, kreator |

Zadłużenie: pytanie B8.

## R. Kwota końcowa

| ID | Pytanie | Pole | Osoba | Rodzaj | Pokaż, gdy | Po co | Źródła |
|---|---|---|---|---|---|---|---|
| R1 | Czy masz prawo do zasiłku macierzyńskiego z więcej niż jednego tytułu? Kwoty z pozostałych tytułów; który płatnik ma wypłacić podwyższenie? | `inne_zasilki_mac[]` | rodzic | fakt | zawsze przy zasiłku macierzyńskim | podwyższenie do kwoty świadczenia rodzicielskiego, gdy łączna kwota jest niższa; proporcjonalnie za część miesiąca (art. 31 ust. 3a–3c, art. 62 ust. 4–6) | zus_konto, upload:oswiadczenie, kreator |
| R2 | (opcjonalnie) Czy płatnik pomniejsza zaliczkę na PIT (PIT-2, stawka)? | `pit{}` | rodzic | fakt | gdy pokazujemy kwotę netto | Poradnik porównuje z kwotą świadczenia rodzicielskiego zasiłek pomniejszony o zaliczkę na PIT | kreator |

## S. Ryzyka (ostrzeżenia i status `warunkowo`, nie automatyczna odmowa – wymaganie h)

Każde ryzyko ma kod w `content/ryzyka` (API: `Ryzyko.kod`). Flaga `dotyczy_ciebie` jest liczona z pól poniżej.

| ID | Pytanie | Pole | Osoba | Rodzaj | Pokaż, gdy | Ostrzeżenie (kod ryzyka) | Źródła |
|---|---|---|---|---|---|---|---|
| S1 | Kiedy zawarto umowę, otwarto działalność albo zgłoszono się do dobrowolnego ubezpieczenia chorobowego? | `data_zgloszenia` | rodzic | fakt | zawsze | zgłoszenie w ciąży lub tuż przed nią → ZUS może badać pozorność (`umowa_dla_pozoru`) | zus_konto, upload:Z-3, kreator |
| S2 | Czy w czasie ciąży podwyższono wynagrodzenie albo deklarowaną podstawę składek? Kiedy i o ile? | `podwyzka_w_ciazy{}` | rodzic | fakt (wyliczane też z O4 / Q1 i `pdp`) | zawsze | ZUS może ustalić niższą podstawę (`podwyzszenie_podstawy_w_ciazy`) | zus_konto, upload:Z-3, kreator |
| S3 + S3a | Czy przed porodem planujesz rozwiązać umowę, zamknąć lub zawiesić działalność, zakończyć zlecenie albo wyrejestrować się z dobrowolnego ubezpieczenia chorobowego? (tak / nie) + ostatni dzień umowy lub ubezpieczenia (data, gdy „tak”). Rodzaj ustania – później | `plan_ustania`, `plan_ustania_data` | rodzic | **plan** | A1 ∋ ciąża (S3a: S3 = tak) | brak ubezpieczenia w dniu porodu = brak zasiłku macierzyńskiego, poza wyjątkami z F (`brak_ubezpieczenia_w_dniu_porodu`); wchodzi do B7 | kreator |
| S4 | Czy opłacasz składki terminowo? | `terminowosc_skladek` | rodzic | fakt | B1 ∋ działalność | zadłużenie i przerwy w ubezpieczeniu (`zadluzenie_skladkowe`; B8, Q4) | zus_platnik, kreator |
| S5 | Praca w czasie zwolnienia | pytanie D6 | rodzic | fakt | D1 niepuste | utrata zasiłku (`praca_na_zwolnieniu`) | kreator |
| S6 | Czy w czasie ciąży zmieniono warunki zatrudnienia (etat, rodzaj umowy, pracodawcę)? | `zmiana_warunkow_w_ciazy{}` | rodzic | fakt / wyliczone z B2, O7 | A1 ∋ ciąża | wpływ na prawo i wysokość zasiłku (`zmiana_warunkow_zatrudnienia`) | zus_konto, upload:Z-3, kreator |

## T. Zasiłek opiekuńczy – poza zakresem pierwszej wersji

Nie ma go w punktach a–j treści wyzwania ani w `docs/opis_aplikacji.md`. Pytania zostają jako zapas
(`sytuacja` ∋ opieka): wyłączony moduł w panelu admina, dopóki mentorzy nie potwierdzą, że jest oczekiwany.

| ID | Pytanie | Pole | Osoba | Rodzaj | Pokaż, gdy | Po co | Źródła |
|---|---|---|---|---|---|---|---|
| T1 | Nad kim sprawujesz opiekę? (zdrowe dziecko do 8 lat: nieprzewidziane zamknięcie żłobka, przedszkola lub szkoły [zawiadomienie mniej niż 7 dni wcześniej], choroba niani lub dziennego opiekuna, poród lub choroba drugiego rodzica stale opiekującego się dzieckiem, jego pobyt w szpitalu, izolacja dziecka / chore dziecko do 14 lat / dziecko z niepełnosprawnością do 18 lat / inny chory członek rodziny) | `opieka_typ` | rodzic | fakt | A1 ∋ opieka | rodzaj i limit dni (Poradnik) | kreator, ezla |
| T2 | Data urodzenia dziecka albo stopień pokrewieństwa | `podopieczny{}` | rodzic | fakt | A1 ∋ opieka | progi 8, 14 i 18 lat; członek rodziny we wspólnym gospodarstwie | kreator, rsc |
| T3 | Czy jest domownik, który może zapewnić opiekę? | `inny_domownik` | rodzic | fakt | A1 ∋ opieka | „tak” = brak zasiłku, chyba że chore dziecko ma mniej niż 2 lata | kreator |
| T4 | Ile dni zasiłku opiekuńczego w tym roku pobrałeś(-aś) Ty, drugi rodzic lub małżonek, inny członek rodziny? | `dni_opiekuncze_rok{}` | rodzic | fakt | A1 ∋ opieka | limity 60 / 30 / 14 dni, łącznie najwyżej 60 dni w roku (zał. 7 pkt 6) | zus_historia, kreator |
| T5 | Okres opieki (e-ZLA albo oświadczenie) | `opieka_od_do` | rodzic | fakt | A1 ∋ opieka | okres wypłaty | ezla, kreator |
| T6 | Czy dziecko ma orzeczenie o znacznym stopniu niepełnosprawności (albo ze wskazaniami)? | `orzeczenie_niepelnosprawnosci` | dziecko | fakt | T1 ∋ niepełnosprawność | wyższy limit wieku | upload:orzeczenie, kreator |

Reguły: 80% podstawy; bez okresu wyczekiwania; dotyczy go zadłużenie z B8. Wyciąg ustawy nie zawiera art. 32–35,
więc reguły pochodzą z Poradnika.

---

## U. Pola wyliczane (bez pytań)

| Pole | Osoba | Z czego | Używane w |
|---|---|---|---|
| `wiek` | rodzic, dziecko | `data_urodzenia` + data odniesienia | D3 (33/14 dni), limity wieku dziecka |
| `okres_wyczekiwania_spelniony` | rodzic | B5, B6, `chorobowe_dobrowolne`, data prawa | zasiłek chorobowy |
| `ubezpieczony_w_dniu_zdarzenia` | rodzic | B3, B5, S3, F, data zdarzenia (`data_porodu` / `pdp` / `data_przyjecia`) | B7, status `warunkowo` |
| `kto_wyplaca[tytul]` | rodzic | C1, B1, D4 | C2, poradnik, `gdzie_zlozyc` |
| `data_prawa` | rodzic | D1 / G2 / N2 | O1, wersja parametrów |
| `dni_okresu_zasilkowego` | rodzic | D1, D2, zus_historia | E1, limit 270 dni |
| `okres_wyczerpany` | rodzic | `dni_okresu_zasilkowego` | E1 |
| `dzieci_zyjace` | rodzic (matka) | I1, I2 osób `dziecko` | I3, wymiar urlopu |
| `liczba_przyjetych` | rodzic | osoby `dziecko` z `data_przyjecia` | N6 |
| `rodz_w_1_roku` | rodzic | `wybory.podzial_rodzicielskiego`, `data_urodzenia` dziecka | J3 |
| `miesiace_ubezpieczenia` | rodzic | B5 | Q3, P4 |

## V. Wybory scenariusza (`Scenariusz.wybory`)

Nie są polami osoby. Kreator ich nie zadaje – ustawia je użytkownik w kalkulatorze. Klucze jak w `docs/api.md` (3.7).

| Klucz | Pytanie źródłowe | Typ | Walidacja (z parametrów) |
|---|---|---|---|
| `wniosek_81_5` | J2 | tak / nie | możliwe tylko, gdy data wniosku ≤ 21 dni od porodu / przyjęcia |
| `start_urlopu_macierzynskiego` | J1 | data | najwcześniej 6 tyg. przed `pdp` |
| `przejecie_macierzynskiego_przez` | J4, K2–K5 | `{osoba_id, od}` | po 14 tyg. (sytuacje szczególne – po 8 tyg.) |
| `uzupelniajacy_kto` | H4 | `osoba_id` | jeden rodzic, bezpośrednio po macierzyńskim |
| `podzial_rodzicielskiego` | L1, L3, L4 | lista `{osoba_id, od, tygodnie, praca_wymiar, praca_wymiar_wydluzenia}` | pula, 9 tyg. nieprzenoszalnych, max 5 części, termin 6. urodzin, `praca_wymiar` ≤ ½ |
| `urlop_ojcowski` | M1 | lista `{osoba_id, od, dni}` | 14 dni, max 2 części ≥ 7 dni, do 12 mies. życia |

Jeśli dokument pokazuje, że urlop **już udzielono** (Z-3 pkt 6–7, ZAM), wartości trafiają do pól faktów
(`macierzynski_od`, `laczenie_praca[]`, `rodzicielski_wykorzystany`), a scenariusz domyślny jest z nich budowany.

---

## W. Dokumenty → pola (dla odczytu skanów)

| Typ dokumentu | Wystawca | Pola |
|---|---|---|
| **ZAS-53** – wniosek o zasiłek chorobowy | uzytkownik | `ezla[]` (okresy), `po_ustaniu{}` („po ustaniu tytułu”), `sytuacja` |
| **ZAM** (i archiwalne **ZUR**, **ZAO**) – wniosek o zasiłek macierzyński | uzytkownik | `rola`, `data_porodu`, `liczba_dzieci`, `za_zyciem`, `wariant`, `wniosek_81_5_data`, `rodzicielski_czesci[]`, `ojcowski_czesci[]`, dane dziecka |
| **Z-3** – zaświadczenie płatnika (pracownik); może być „pierwszorazowy” i kilka „w kontynuacji” | pracodawca | `tytuly` (umowa o pracę), `zatrudnienie_od`, `etat`, `umowa_rodzaj`, `urlop_bez_zasilku`, `wynagrodzenie_chorobowe_okres[]`, `ezla[]` (okresy zasiłku), okresy zasiłków, udzielone urlopy (`macierzynski_od`, `laczenie_praca[]`), `miesiace[]`, `premie_kwartalne[]`, `premie_roczne`, `umowy_u_pracodawcy[]`, `platnik_ponad_20` |
| **Z-3a** – zaświadczenie płatnika (zleceniobiorca) | pracodawca | `tytuly` (zlecenie), `przychod_miesiace[]`, `ciaglosc_zlecen`, `platnik_ponad_20` |
| **Z-3b** (archiwalny) – działalność | pracodawca / uzytkownik | `podstawa_deklarowana[]` |
| **ZAS-12** – płatnik, dalszy okres | pracodawca | `ezla[]` (kolejne okresy), wypłacone świadczenia |
| **Poświadczenie ubezpieczenia chorobowego** (wewnętrzny ZUS) | zus | `tytuly`, `chorobowe`, `chorobowe_od`, `okresy_wczesniejsze`, `podstawa_deklarowana[]` / podstawy składek |
| **Zrzut z systemu ZUS** | zus | okresy ubezpieczenia, tytuły (kod tytułu: 0110, 0411, 0510, 0570 – tytuł z kodu, nie z kontekstu), `ezla[]` (zrzut e-ZLA; kod literowy tylko z obrazu), przyznane świadczenia (`poprzedni_zasilek`, `rodzicielski_wykorzystany`) |
| **Akt urodzenia / zgonu** | urzad | dziecko: `data_urodzenia`, `martwe_urodzenie`, `data_zgonu`; `data_porodu`, `liczba_dzieci` |
| **Zaświadczenie lekarskie** (przewidywana data porodu, ciąża) | lekarz | `pdp`, `ciaza_w_zatrudnieniu` |
| **Karta informacyjna szpitala** | lekarz | dziecko: `tydzien_ciazy`, `masa_g`, `hospitalizacje[]`; `matka_szpital[]` |
| **Zaświadczenie „Za życiem”** | lekarz | dziecko: `za_zyciem` |
| **Postanowienie / zaświadczenie sądu, umowa ze starostą** | sad / urzad | `forma_przyjecia`, `data_przyjecia`, `data_wniosku_sad`, `przysposobienie_prawomocne`, `umieszczenie_data` |
| **Wyrok sądu, świadectwo pracy** | sad / pracodawca | `ustanie_data`, `ustanie_przyczyna` |
| **Orzeczenie o niezdolności do samodzielnej egzystencji** | urzad | `matka_nse` |
| **Pismo ZUS** (np. „brakuje Z-3”) | zus | **żadnych pól** – informacja dla użytkownika (lista braków) |
| **Decyzja / wynik sprawy** | zus | **żadnych pól** – tylko `Sprawa.oczekiwany_wynik` (rozpoznawana po treści, nie po pozycji) |

---

## X. Macierz: świadczenie → potrzebne pytania

Reguła zwraca `brak_danych`, gdy brakuje aktywnej wartości któregokolwiek pola z kolumny „Warunki prawa” (dla statusu)
albo „Okres” / „Kwota” (dla wyliczeń – wtedy status prawa jest znany, a kwota oznaczona jako brakująca).

| Świadczenie | Warunki prawa | Okres | Kwota |
|---|---|---|---|
| Zasiłek chorobowy w ciąży | A1, B1, B4–B6, B8, B10–B11, D1, D4–D6 | D1–D3a, A4 | C2, O/P/Q (100%) |
| Świadczenie rehabilitacyjne | E1–E2, B10 | E3 | O/P/Q, E3–E4 |
| Zasiłek w wysokości zasiłku macierzyńskiego | F1–F4, B3 | F1 → G1/G2 | O (100%) |
| Urlop macierzyński | A2, B1 (umowa o pracę), G1–G3, G5 | V: start, przejęcie; I1–I3, K2–K5 | – |
| Zasiłek macierzyński za okres urlopu macierzyńskiego | A2, B4, B7, B8, F (wyjątki), K | G2, G3, G5, K7; V: start, przejęcie | V: `wniosek_81_5`, O/P/Q, R1 |
| Zasiłek przy martwym urodzeniu lub zgonie dziecka | I1, B4, B7 | I1–I3, G2 | O/P/Q (100%) |
| Uzupełniający urlop macierzyński i zasiłek | H1–H3, H5, B4 | H1–H3; V: `uzupelniajacy_kto` | O/P/Q (100%) |
| Urlop rodzicielski i zasiłek | B1/B4, K1, A3 | G3, G4, L2; V: `podzial_rodzicielskiego` | V: `wniosek_81_5`, J3, O/P/Q, R1 |
| Urlop ojcowski i zasiłek | A2, B4/B7, M2 | M3, G2; V: `urlop_ojcowski` | O/P/Q (100%) |
| Urlop na warunkach urlopu macierzyńskiego i zasiłek | N1–N3, B4, B7 | N4–N7 | V: `wniosek_81_5`, O/P/Q |
| Urlop rodzicielski przy przyjęciu dziecka | N1–N5 | N4, N6, N7, G4; V: `podzial_rodzicielskiego` | V: `wniosek_81_5`, O/P/Q |
| Zasiłek opiekuńczy (moduł wyłączony) | T1–T3, B4, B8 | T4–T5 | O/P/Q (80%) |

---

## Y. Parametry do panelu administracyjnego (`params/`, stałe, nie pytania)

Każda wersja ma `obowiazuje_od`. Do wyliczeń bierzemy wersję obowiązującą w dniu `data_prawa`.

| Parametr | Wartość z materiałów |
|---|---|
| Urlop macierzyński / na warunkach (1–5+ dzieci) | 20 / 31 / 33 / 35 / 37 tyg. |
| Minimalny urlop na warunkach urlopu macierzyńskiego | 9 tyg. |
| Urlop rodzicielski (1 / 2+ dzieci) | 41 / 43 tyg.; „Za życiem” 65 / 67; przy przyjęciu w szczególnym przypadku 38 (62) |
| Część nieprzenoszalna dla każdego rodzica | 9 tyg. |
| Liczba części urlopu rodzicielskiego, termin | 5; do końca roku, w którym dziecko kończy 6 lat |
| Łączenie z pracą: maks. wymiar, limity | ½ etatu; 82 / 86 tyg. („Za życiem” 130 / 134) |
| Urlop ojcowski | 2 tyg., najwyżej 2 części po co najmniej 1 tyg., do 12 mies. życia (adopcja: 12 mies. od uprawomocnienia, do 14 lat) |
| Uzupełniający urlop macierzyński | progi 28 i 37 tyg. ciąży, 1000 g; limity do 8. i 15. tyg. po porodzie; dni 5–28 |
| Martwe urodzenie lub zgon | 8 tyg.; co najmniej 7 dni od zgonu |
| Stawki | 100% / 70% / 81,5%; chorobowy 80% (w ciąży 100%); rehabilitacyjne 90% → 75% (w ciąży 100%); opiekuńczy 80% |
| Termin wniosku o 81,5% | 21 dni |
| Start urlopu przed porodem | maks. 6 tyg. |
| Przejęcie urlopu przez ojca | po 14 tyg. (sytuacje szczególne – po 8 tyg.) |
| Okres wyczekiwania | 30 dni (obowiązkowe) / 90 dni (dobrowolne); wliczana przerwa do 30 dni |
| Okres zasiłkowy | 182 dni / 270 dni (ciąża); przerwa 60 dni; po ustaniu 91 dni (nie w ciąży) |
| Wynagrodzenie chorobowe | 33 dni / 14 dni (50+) |
| Świadczenie rehabilitacyjne | maks. 12 mies.; kwartalny wskaźnik waloryzacji |
| Składki odliczane od podstawy | 13,71% |
| Minimalne wynagrodzenie 2024 / 2025 / 2026 | 4 242 zł do 30.06.2024 i 4 300 zł od 1.07.2024 (Dz.U. 2023 poz. 1893) / 4 666 zł (Dz.U. 2024 poz. 1362) / 4 806 zł → minimalna podstawa 4 147,10 zł |
| Maks. podstawa przy dobrowolnym ubezpieczeniu 2024 / 2025 / 2026 | 19 560 zł (źródło wtórne, do_weryfikacji) / 21 682,50 zł (komunikat ZUS 13.12.2024, kwota ze źródła wtórnego, do_weryfikacji) / 23 550 zł → 20 321,30 zł |
| Najniższa podstawa przy niepełnym etacie (`art45_niepelny_etat`) | `proporcjonalnie` (× wymiar etatu; z komentarzy) albo `brak`; do_weryfikacji – sekcja Z, pyt. 15. Dotyczy zasiłku chorobowego i macierzyńskiego |
| Próg zadłużenia | 1% minimalnego wynagrodzenia (48,06 zł); spłata w 6 mies. |
| Kwota świadczenia rodzicielskiego (podwyższenie) | 1 000 zł (z pisma ZUS w sprawie z 2025 r.); do potwierdzenia na 2026 |
| Duży płatnik | ponad 20 ubezpieczonych, stan na 30.11 poprzedniego roku |
| Przedawnienie | 6 mies. (3 lata przy błędzie płatnika lub ZUS) |
| Opiekuńczy – limity | 60 / 30 / 14 dni; łącznie 60 dni w roku |
| Zasiłek pogrzebowy (informacja) | 7 000 zł |
| Tydzień urlopu / miesiąc zasiłku | 7 dni kalendarzowych / 30 dni (stawka dzienna = 1/30) |
| Próg pewności odczytu AI | 0,6 (poniżej → `do_sprawdzenia`, niższy priorytet w hierarchii) |
| Okres obliczeniowy podstawy (`okres_obliczeniowy_mies`) | 12 miesięcy kalendarzowych przed miesiącem powstania prawa (art. 36 ust. 1) |
| Miesiąc pomijany w podstawie (`art38_min_czesc_czasu_pracy`) | przepracowano mniej niż ½ obowiązującego czasu pracy (art. 38 ust. 2) |
| Ta sama podstawa (`art43_przerwa_mies`) | przerwa między zasiłkami krótsza niż 1 miesiąc kalendarzowy (art. 43) |
| Przedłużenie umowy do porodu (`ciaza_tyg`, `przedluzenie_umowy_po_miesiacu_ciazy`) | umowa kończąca się po 3. miesiącu ciąży (art. 177 §3 KP); początek ciąży w przybliżeniu = `pdp` − 40 tyg. |

Pliki parametrów: `params_2024-01-01.json`, `params_2024-07-01.json`, `params_2025-01-01.json`, `params_2026.json`. Każdy ma `obowiazuje_od`/`obowiazuje_do` i klucz `_zrodla` (podstawa prawna, źródło i status `zweryfikowane` / `do_weryfikacji` dla każdej wartości rocznej oraz zbiorczo `pozostale` – przepisane z 2026 i niesprawdzone). Brak pliku na rok prawa → widoczne ostrzeżenie w wyniku (CLAUDE.md, zasada 15).

Parametry z poprzednich lat (np. minimalne wynagrodzenie 2025 dla spraw testowych z 2025 r.) dodajemy jako osobne
wersje z wcześniejszym `obowiazuje_od`, bo sprawy ZUS dotyczą różnych lat.

---

## Z. Do wyjaśnienia z mentorami ZUS

Pytania o prawo i wyliczenia. Pytania o demo i zakres: `docs/opis_aplikacji.md`, rozdz. 15.

1. **Art. 183 §3 i §4 pkt 3 KP:** kiedy dokładnie przysługuje 9 tyg. urlopu na warunkach urlopu macierzyńskiego i 38 tyg. rodzicielskiego przy przyjęciu dziecka? Czy wtedy, gdy limit wieku skróciłby urlop poniżej 9 tyg.?
2. **Kwota świadczenia rodzicielskiego w 2026 r.** i to, czy porównujemy z nią zasiłek brutto, czy po zaliczce na PIT (Poradnik mówi o kwocie po PIT).
3. **Tabela minimalnej podstawy 2026** jest pusta w załączniku ZUS; wyliczyliśmy 4 147,10 zł. Brakuje też najniższych podstaw dla działalności (standardowej i preferencyjnej) na 2026 r.
4. **Wariant 81,5% przy urlopie zaczętym przed porodem:** jak rozliczyć 100% wypłacone przed porodem?
5. **Zasiłek opiekuńczy:** wyciąg ustawy nie zawiera art. 32–35. Czy w ogóle oczekujecie go w aplikacji?
6. **Formularze ZUR, ZAO i Z-3b** zlikwidowano od 24.10.2026, ale występują w sprawach testowych. Aplikacja ma je tylko czytać, a nowe wnioski generować na ZAM?
7. **Art. 9 ust. 4 i art. 17 ust. 1d–1e** wchodzą w życie 1.01.2027. Uwzględniać datę wejścia w życie jako parametr?
8. **Parametry z lat poprzednich** (sprawy testowe z 2025 r.): czy możecie potwierdzić wartości 2025 (minimalne wynagrodzenie, limity) do wyliczeń w tych sprawach?
9. **Wyjątki od okresu wyczekiwania zasiłku chorobowego** (30 dni, dobrowolne 90): wliczanie wcześniejszych okresów ubezpieczenia przy przerwie do 30 dni, zwolnienia od wyczekiwania (B6: 10 lat ubezpieczenia, absolwenci) i inne przypadki z art. 4 ustawy zasiłkowej. Reguła ich jeszcze nie stosuje (tylko wskazówka w `co_zrobic`). Numery ustępów do potwierdzenia.
10. **Czy dni wynagrodzenia chorobowego wliczają się do 270 dni okresu zasiłkowego w ciąży?** Zakładamy, że tak (okres liczony od pierwszego dnia niezdolności, razem z wynagrodzeniem).
11. **33 dni wynagrodzenia, gdy niezdolność trwa nieprzerwanie na przełomie roku:** czy w nowym roku liczy się nowy limit 33 dni, czy dni z poprzedniego roku? Druk Z-3 prosi o „okresy wynagrodzenia wypłaconego w poprzednim roku wliczane do jednego okresu zasiłkowego”. Dziś liczymy limit od początku niezdolności i tylko ostrzegamy, gdy okres z Z-3 przekracza limit.
12. **Przerwy między zwolnieniami:** jak liczyć okres zasiłkowy i 33 dni, gdy między zwolnieniami są dni bez zwolnienia (przerwa do 60 dni sumuje okresy)? Dziś liczymy tylko dni objęte zwolnieniem i ostrzegamy o przerwie.
13. **Granica 50 lat dla 14 dni wynagrodzenia:** zakładamy 14 dni od roku kalendarzowego następującego po tym, w którym pracownik ukończył 50 lat. Prosimy o potwierdzenie.
14. **`dni_wynagr_chorobowego_rok` (D3):** druk Z-3 nie ma pola „liczba dni”, tylko okresy od–do (D3a). Czy mamy gdzieś indziej wartość, którą ma zawierać to pole (np. historia świadczeń w ZUS), czy pole usunąć?
15. **Art. 45 – najniższa podstawa przy niepełnym etacie** (pytanie nr 1): ust. 1 mówi o „pracy w pełnym wymiarze czasu pracy”, a proporcjonalne obniżenie dla niepełnego etatu pochodzi z komentarzy (infor.pl, poradnikprzedsiebiorcy.pl). Czy podstawa przy etacie 0,25 jest podnoszona do 1/4 najniższej podstawy? Parametr `art45_niepelny_etat` (domyślnie `proporcjonalnie`) i drugi wariant w uwagach wyniku.
16. **Art. 36 ust. 1 – 12 czy 6 miesięcy?** Zostaje 12 (`okres_obliczeniowy_mies`, do_weryfikacji). Nie udało się pobrać aktualnego tekstu (lexlege.pl/pb.pl niedostępne dla narzędzia); api.sejm.gov.pl to tekst z 1999 r. (6 miesięcy, 18,71%) i nie jest źródłem. Prosimy o potwierdzenie na aktualnym tekście jednolitym.
17. **Art. 48a – aktualny tekst i wzór** (obowiązuje od 1.01.2016; SN II USKP 227/21, III UK 193/19): dotyczy osób niebędących pracownikami, gdy ubezpieczenie chorobowe zaczęło się po raz pierwszy lub po przerwie. Jak dokładnie liczyć podstawę (najniższa podstawa, liczba miesięcy)? Do czasu odpowiedzi: bez kwoty przy ubezpieczeniu krótszym niż 12 miesięcy albo niespełnionym progu 60%.
18. **Poświadczenie ZUS, pkt 11 (próg 60%)**: jak wynik „NIE” i „ostatni miesiąc poniżej 60%” wpływają na podstawę zasiłku z działalności (w próbce podstawa wzrosła z 1 399,80 zł do 5 652,00 zł w ostatnich 5 miesiącach)? Czy to ten sam mechanizm co art. 48a, czy osobne ograniczenie?
19. **Parametry 2024 i 2025 do_weryfikacji:** limit 250% prognozowanego wynagrodzenia (19 560 zł; 21 682,50 zł) z komunikatów ZUS oraz wszystkie wartości przepisane z 2026 (wyczekiwanie, okres zasiłkowy, 33/14 dni, stawki, 13,71%). Płaca minimalna 2024 i 2025 jest zweryfikowana w rozporządzeniach.
20. **Zaokrąglenia stawki dziennej przy 80%:** stosujemy jedno zaokrąglenie (podstawa × stawka ÷ 30), co dla sprawy testowej daje ten sam wynik co „dzienna 100% zaokrąglona, potem × 80%”. Prosimy o potwierdzenie kolejności zaokrągleń ZUS.
