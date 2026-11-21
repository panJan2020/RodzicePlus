# Zasiłkowy Przewodnik – pełna lista pytań do ustalenia prawa i wyliczenia świadczeń

Lista na podstawie: treści wyzwania, ustawy zasiłkowej (wyciąg), Kodeksu pracy (wyciąg), rozporządzenia z 27.09.2026 r. w sprawie zakresu informacji i dokumentów (zwł. załączniki 2, 3, 6, 7), rozporządzenia w sprawie wniosków o urlopy, Poradnika ZUS 2026 oraz załącznika ZUS (wymiary, wysokości, podstawa wymiaru).

## Jak czytać

- **ID** – identyfikator pytania (do kodu, testów i dokumentacji).
- **Pole** – proponowana nazwa pola we wspólnym schemacie danych (ten sam schemat dla kwestionariusza i odczytu skanów).
- **Pokaż, gdy** – warunek wyświetlenia pytania. Pytań nie zadajemy wszystkich naraz, tylko po kolei według odpowiedzi.
- **Źródło odpowiedzi:** 👤 użytkownik · 🏛 dane ZUS (symulacja: PUE/eZUS, e-ZLA, konto płatnika) · 📄 dokumenty ze sprawy (ZAM, Z-3, Z-3a, Z-3b, ZAS-53, ZAS-12, akt urodzenia, zaświadczenia).
- Jeśli w sprawie są **dwie osoby** (matka i ojciec), sekcje B, C oraz O–R wypełnia się osobno dla każdej z nich.
- „Dziecko” oznacza każde dziecko z jednego porodu albo przyjęte jednocześnie. Pola dziecka są listą.

---

## A. Sytuacja i rola (zawsze)

| ID | Pytanie (odpowiedzi) | Pole | Pokaż, gdy | Po co (reguła / przepis) | Źródło |
|---|---|---|---|---|---|
| A1 | Jaka jest Twoja sytuacja? (wielokrotny wybór: planuję dziecko / jestem w ciąży / dziecko się urodziło / dziecko urodziło się martwe lub zmarło / przyjąłem(-am) dziecko na wychowanie / muszę opiekować się dzieckiem lub chorym członkiem rodziny) | `sytuacja[]` | zawsze | wybór ścieżek pytań | 👤 📄 |
| A2 | Kim jesteś dla dziecka? (matka / ojciec / inny członek najbliższej rodziny / osoba, która przyjęła dziecko i złożyła wniosek o przysposobienie / rodzina zastępcza) | `rola` | zawsze | uprawnienia zależą od roli (art. 29 ust. 1–10 u.z.) | 👤 📄 ZAM |
| A3 | Czy drugi rodzic też będzie korzystał z urlopów lub zasiłków? (tak / nie / nie wiem) | `drugi_rodzic_aktywny` | A1 ≠ tylko opieka | uruchamia drugi profil i symulację podziału (wym. d) | 👤 |
| A4 | Data urodzenia wnioskodawcy | `data_urodzenia` | zawsze | wynagrodzenie chorobowe 33 albo 14 dni (art. 92 KP) | 🏛 📄 |

## B. Tytuł ubezpieczenia i ubezpieczenie chorobowe (dla każdej osoby)

| ID | Pytanie | Pole | Pokaż, gdy | Po co | Źródło |
|---|---|---|---|---|---|
| B1 | Na jakiej podstawie pracujesz? (wielokrotny: umowa o pracę / umowa zlecenia lub agencyjna / działalność gospodarcza / współpraca przy działalności / umowa o dzieło / inne / nie pracuję) | `tytuly[]` | zawsze | urlop (tylko pracownik) albo zasiłek „za okres odpowiadający urlopowi”; kto wypłaca; sposób liczenia podstawy | 🏛 📄 |
| B2 | Wymiar etatu | `etat` | B1 ∋ umowa o pracę | minimalna podstawa przy pełnym etacie (art. 45); łączenie z urlopem rodzicielskim | 🏛 📄 Z-3 |
| B3 | Rodzaj umowy o pracę i data jej końca (nieokreślony / określony / próbny ponad 1 mies. / na zastępstwo) | `umowa_rodzaj`, `umowa_do` | B1 ∋ umowa o pracę | umowa kończąca się po 3. mies. ciąży przedłuża się do porodu, chyba że to zastępstwo (art. 177 §3, §3¹ KP); zasiłek po ustaniu (art. 30 ust. 4 u.z.) | 👤 📄 |
| B4 | Czy z danego tytułu podlegasz ubezpieczeniu chorobowemu? (przy zleceniu i działalności tylko dobrowolnie, po zgłoszeniu ZUS ZUA) | `chorobowe[tytul]` | B1 ≠ tylko umowa o pracę | „nie” = brak zasiłków z tego tytułu; przy zbiegu z umową o pracę z co najmniej minimalnym wynagrodzeniem nie można zgłosić się dobrowolnie z działalności ani ze zlecenia (Poradnik) | 🏛 📄 poświadczenie |
| B5 | Od kiedy nieprzerwanie podlegasz ubezpieczeniu chorobowemu? Czy wcześniejsze okresy dzieliła przerwa do 30 dni (albo urlop wychowawczy lub bezpłatny)? | `chorobowe_od`, `okresy_wczesniejsze[]` | zawsze | okres wyczekiwania 30 albo 90 dni (art. 4 ust. 1–2); liczba pełnych miesięcy do podstawy | 🏛 📄 |
| B6 | Czy masz co najmniej 10 lat obowiązkowego ubezpieczenia chorobowego albo zgłosiłeś(-aś) się do ubezpieczenia w ciągu 90 dni od ukończenia szkoły lub uczelni? | `zwolnienie_z_wyczekiwania` | ścieżka zasiłku chorobowego i B5 < 30/90 dni | prawo do zasiłku od 1. dnia (art. 4 ust. 3) | 👤 |
| B7 | Czy w dniu porodu (przyjęcia dziecka) będziesz ubezpieczony(-a) chorobowo albo przebywał(a) na urlopie wychowawczym? | `ubezpieczony_w_dniu_zdarzenia` | ścieżki zasiłku macierzyńskiego | warunek konieczny zasiłku macierzyńskiego (art. 29 ust. 1); wyjątki w sekcji F | 🏛 👤 (wyliczane z B3, B5, S3) |
| B8 | Zadłużenie składkowe na dzień powstania prawa do świadczenia | `zadluzenie_kwota` | B1 ∋ działalność lub współpraca | powyżej 1% minimalnego wynagrodzenia świadczenie nie przysługuje do czasu spłaty; brak spłaty przez 6 mies. = przedawnienie (art. 2a) | 🏛 |
| B9 | Czy korzystasz z „ulgi na start”? | `ulga_na_start` | B1 ∋ działalność | brak ubezpieczeń = brak zasiłków (Poradnik) | 🏛 👤 |
| B10 | Czy masz prawo do emerytury, renty z tytułu niezdolności do pracy, zasiłku dla bezrobotnych, świadczenia lub zasiłku przedemerytalnego, rodzicielskiego świadczenia uzupełniającego albo nauczycielskiego świadczenia kompensacyjnego? | `inne_swiadczenia[]` | ścieżki zasiłku chorobowego po ustaniu i świadczenia rehabilitacyjnego | wyłączenia (art. 13 ust. 1, art. 18 ust. 7) | 👤 🏛 |
| B11 | Czy w okresie zwolnienia jesteś na urlopie bezpłatnym, wychowawczym albo opiekuńczym? | `urlop_bez_zasilku` | ścieżka zasiłku chorobowego | zasiłek za te okresy nie przysługuje (art. 12 ust. 2) | 📄 Z-3 |

## C. Kto ustala i wypłaca zasiłek

| ID | Pytanie | Pole | Pokaż, gdy | Po co | Źródło |
|---|---|---|---|---|---|
| C1 | Ilu ubezpieczonych zgłaszał Twój płatnik do ubezpieczenia chorobowego na 30 listopada poprzedniego roku? (ponad 20 / najwyżej 20 / nie wiem) | `platnik_ponad_20[tytul]` | B1 ∋ umowa o pracę lub zlecenie | ponad 20 → wypłaca płatnik, w innym razie ZUS; przy działalności i po ustaniu ubezpieczenia zawsze ZUS (art. 61). Od tego zależy, gdzie złożyć dokumenty (wym. g) | 🏛 📄 Z-3 pkt 11 |

## D. Ciąża – zasiłek chorobowy

| ID | Pytanie | Pole | Pokaż, gdy | Po co | Źródło |
|---|---|---|---|---|---|
| D1 | Zwolnienia lekarskie e-ZLA w ciąży: okresy od–do i czy mają kod „B” | `ezla[]` | A1 ∋ ciąża | 100% podstawy z kodem B (art. 11 ust. 2); okres zasiłkowy 270 dni (art. 8); każdy dzień płatny, także wolny (art. 11 ust. 4) | 🏛 e-ZLA 📄 |
| D2 | Czy przed zwolnieniami z kodem B miałaś zwolnienia bez kodu B? Kiedy się skończyły? | `ezla_przed_ciaza[]` | D1 niepuste | okresów sprzed przerwy nie wlicza się do okresu zasiłkowego, jeśli po przerwie niezdolność przypada w ciąży (art. 9 ust. 2) | 🏛 |
| D3 | Ile dni wynagrodzenia chorobowego wypłacił Ci pracodawca w tym roku kalendarzowym? | `dni_wynagr_chorobowego_rok` | B1 ∋ umowa o pracę | pierwsze 33 dni (14 dni po roku, w którym skończyłaś 50 lat) płaci pracodawca, potem zasiłek (art. 92 KP); w ciąży również 100% | 🏛 📄 Z-3 pkt 9 |
| D4 | Czy niezdolność do pracy powstała po ustaniu tytułu ubezpieczenia? Data ustania, data początku niezdolności, czy trwała co najmniej 30 dni bez przerwy | `po_ustaniu{}` | D1 i ustał tytuł | prawo, jeśli niezdolność powstała do 14 dni od ustania (art. 7); w ciąży bez limitu 91 dni (art. 8 ust. 2) | 👤 📄 oświadczenie |
| D5 | Czy po ustaniu tytułu kontynuujesz albo podjęłaś działalność zarobkową? | `praca_po_ustaniu` | D4 = tak | wyłącza zasiłek za okres po ustaniu (art. 13 ust. 1 pkt 2) | 👤 |
| D6 | Czy w czasie zwolnienia wykonujesz pracę zarobkową (także z innego tytułu)? | `praca_na_zwolnieniu` | D1 niepuste | utrata zasiłku za całe zwolnienie (art. 17); od 2027 r. można nie wystawiać zwolnienia z tytułu, w którym da się pracować (art. 17 ust. 1d–1e) | 👤 (ostrzeżenie) |

## E. Świadczenie rehabilitacyjne

| ID | Pytanie | Pole | Pokaż, gdy | Po co | Źródło |
|---|---|---|---|---|---|
| E1 | Czy wyczerpałaś okres zasiłkowy (270 dni) i nadal jesteś niezdolna do pracy? | `okres_wyczerpany` (wyliczane z D1) | D1 suma ≥ 250 dni albo pytanie użytkownika | warunek prawa (art. 18 ust. 1) | 🏛 |
| E2 | Czy lekarz prowadzący ocenia, że dalsze leczenie lub rehabilitacja rokują odzyskanie zdolności do pracy? | `rokowanie` | E1 = tak | o prawie decyduje lekarz orzecznik ZUS (art. 18 ust. 3), więc aplikacja tylko informuje | 👤 |
| E3 | Czy niezdolność nadal przypada w ciąży? | `rehab_w_ciazy` | E1 = tak | 100% w ciąży; w innym razie 90% przez 3 mies., potem 75%; maksymalnie 12 mies. (art. 18 ust. 2, art. 19 ust. 1) | 👤 |
| E4 | Data rozpoczęcia świadczenia | `rehab_od` | E1 = tak | waloryzacja podstawy według kwartału (art. 19 ust. 2) | 👤 |

Wyłączenia: pytanie B10.

## F. Utrata pracy w ciąży (zasiłek w wysokości zasiłku macierzyńskiego)

| ID | Pytanie | Pole | Pokaż, gdy | Po co | Źródło |
|---|---|---|---|---|---|
| F1 | Czy umowa o pracę ustała w czasie ciąży? Kiedy? | `ustanie_data` | A1 ∋ ciąża i B1 ∋ umowa o pracę | ścieżka art. 30 | 👤 📄 świadectwo pracy |
| F2 | Z jakiej przyczyny? (upadłość / likwidacja / śmierć pracodawcy / rozwiązanie z naruszeniem prawa potwierdzone prawomocnym wyrokiem / inna) | `ustanie_przyczyna` | F1 = tak | upadłość, likwidacja, śmierć → zasiłek w wysokości zasiłku macierzyńskiego do porodu (art. 30 ust. 3); cztery wymienione przyczyny → zasiłek macierzyński po porodzie (art. 30 ust. 1); „inna” → brak | 👤 📄 |
| F3 | Czy zapewniono Ci inne zatrudnienie? | `inne_zatrudnienie` | F2 ∈ {upadłość, likwidacja, śmierć} | warunek art. 30 ust. 3 | 👤 📄 oświadczenie |
| F4 | Czy ciążę stwierdzono zaświadczeniem lekarskim w czasie zatrudnienia? | `ciaza_w_zatrudnieniu` | F1 = tak | wymagany dokument (§15, §17 rozporządzenia) | 👤 📄 |

## G. Poród i dziecko

| ID | Pytanie | Pole | Pokaż, gdy | Po co | Źródło |
|---|---|---|---|---|---|
| G1 | Przewidywana data porodu | `pdp` | A1 ∋ ciąża | urlop do 6 tyg. przed porodem; 3. miesiąc ciąży przy B3; oś czasu | 👤 📄 zaświadczenie |
| G2 | Data porodu | `data_porodu` | A1 ∋ urodzenie | początek urlopu (art. 183¹ §2 KP); termin 21 dni na wariant 81,5%; limity wieku dziecka | 📄 akt urodzenia, ZAM |
| G3 | Ile dzieci urodziło się przy jednym porodzie? | `liczba_dzieci` | A1 ∋ urodzenie lub ciąża | urlop macierzyński 20/31/33/35/37 tyg.; rodzicielski 41 albo 43 tyg. | 📄 ZAM |
| G4 | Czy dziecko ma zaświadczenie „Za życiem”? | `za_zyciem` | A1 ∋ urodzenie lub przyjęcie | rodzicielski 65/67 tyg. (62 przy przyjęciu); limity łączenia z pracą 130/134 tyg. | 👤 📄 oświadczenie |
| G5 | Czy dziecko zostało porzucone albo umieszczone (orzeczeniem sądu) w pieczy zastępczej, zakładzie opiekuńczo-leczniczym, pielęgnacyjno-opiekuńczym lub rehabilitacji leczniczej? Kiedy? | `umieszczenie_data` | A1 ∋ urodzenie | matce nie przysługuje część urlopu po tej dacie, ale co najmniej 8 tyg. po porodzie (art. 182 KP) | 👤 |

## H. Wcześniak albo hospitalizacja dziecka (uzupełniający urlop macierzyński)

| ID | Pytanie | Pole | Pokaż, gdy | Po co | Źródło |
|---|---|---|---|---|---|
| H1 | W którym tygodniu ciąży urodziło się dziecko? | `tydzien_ciazy` | A1 ∋ urodzenie i dziecko było w szpitalu | przed 28. tyg. → do 15. tyg. po porodzie; 28–37 tyg. i ponad 1000 g → do 8. tyg.; po 37. tyg. → od 5. dnia do 8. tyg. (art. 180² KP) | 📄 zaświadczenie szpitala |
| H2 | Masa urodzeniowa każdego dziecka (g) | `masa_g[]` | jw. | do 1000 g → wariant do 15. tyg.; przy wieloraczkach liczy się najniższa masa | 📄 |
| H3 | Okresy pobytu w szpitalu po porodzie (od–do, każde dziecko) | `hospitalizacje[]` | jw. | tydzień urlopu za tydzień pobytu, okresy się sumuje, niepełny tydzień w górę; po 37. tyg. ciąży co najmniej 2 kolejne dni, z pierwszym w 5.–28. dniu; przy wieloraczkach najdłuższa hospitalizacja | 📄 |
| H4 | Kto skorzysta (matka / ojciec)? Czy drugi rodzic oświadcza, że nie skorzysta? | `uzup_kto`, `uzup_oswiadczenie_drugiego` | jw. | tylko jeden rodzic, jednorazowo, bezpośrednio po urlopie macierzyńskim | 👤 📄 |
| H5 | (przy przyjęciu dziecka) Czy pobyt w szpitalu był już po przyjęciu na wychowanie? | `hosp_po_przyjeciu` | A1 ∋ przyjęcie | warunek art. 183 §3¹ KP | 👤 |

## I. Martwe urodzenie lub zgon dziecka

| ID | Pytanie | Pole | Pokaż, gdy | Po co | Źródło |
|---|---|---|---|---|---|
| I1 | Czy dziecko urodziło się martwe? | `martwe_urodzenie` | A1 ∋ martwe lub zgon | 8 tyg. po porodzie (art. 180¹ §1 KP) | 📄 akt z adnotacją / zaświadczenie |
| I2 | Data zgonu dziecka (każdego) | `data_zgonu[]` | A1 ∋ martwe lub zgon | zgon przed 8. tyg. życia → 8 tyg. po porodzie, ale co najmniej 7 dni od zgonu; później → 7 dni od zgonu | 📄 |
| I3 | Ile dzieci z tego porodu żyje? | `dzieci_zyjace` | G3 > 1 | wymiar urlopu według liczby żyjących dzieci | 👤 |

Dodatkowa informacja (poza listą świadczeń): przy martwym urodzeniu przysługuje zasiłek pogrzebowy 7000 zł (Poradnik).

## J. Urlop macierzyński – plan i wariant wypłaty

| ID | Pytanie | Pole | Pokaż, gdy | Po co | Źródło |
|---|---|---|---|---|---|
| J1 | Czy chcesz zacząć urlop (zasiłek) przed porodem? Od kiedy? | `macierzynski_od` | A1 ∋ ciąża i A2 = matka | najwyżej 6 tyg. przed porodem; potrzebne zaświadczenie o przewidywanej dacie porodu; wniosek 14 dni przed | 👤 📄 |
| J2 | Wariant wypłaty: 81,5% za cały okres czy 100% + 70%? Data złożenia wniosku | `wariant`, `wniosek_81_5_data` | ścieżki macierzyński i rodzicielski | 81,5% tylko przy wniosku do 21 dni po porodzie (przyjęciu); 9 tyg. drugiego rodzica zawsze 70% (art. 30a, art. 31 ust. 3, 3f) | 👤 📄 ZAM |
| J3 | Czy co najmniej jeden dzień urlopu rodzicielskiego wykorzystasz przed 1. urodzinami dziecka? | `rodz_w_1_roku` | J2 = 81,5% | jeśli nie: rodzicielski po 70%, a macierzyński wyrównywany do 100% na wniosek (art. 31 ust. 3g, ust. 4; zał. 6 pkt 15) | 👤 |
| J4 | Czy matka wróci do pracy po co najmniej 14 tyg. i odda resztę urlopu ojcu? Od kiedy? | `rezygnacja_od` | A3 = tak | art. 180 §4–5 KP, art. 29 ust. 3 u.z.; wniosek o rezygnację 7 dni przed powrotem, wniosek ojca 14 dni przed | 👤 |

## K. Szczególne sytuacje matki (prawa ojca albo członka rodziny)

| ID | Pytanie | Pole | Pokaż, gdy | Po co | Źródło |
|---|---|---|---|---|---|
| K1 | Czy matka dziecka ma tytuł do ubezpieczenia chorobowego (jest ubezpieczona)? | `matka_ubezpieczona` | A2 ≠ matka | rozróżnia ścieżki: ubezpieczona (art. 29 ust. 3–7) i bez tytułu (ust. 9–10); rodzicielski ojca, gdy matka nieubezpieczona | 👤 🏛 |
| K2 | Czy matka ma orzeczenie o niezdolności do samodzielnej egzystencji? | `matka_nse` | A2 ≠ matka | przejęcie urlopu po 8 tyg. (art. 29 ust. 5, art. 180 §6–7 KP) | 👤 📄 orzeczenie |
| K3 | Czy matka przebywa w szpitalu i nie może opiekować się dzieckiem? Daty przyjęcia i wypisu | `matka_szpital[]` | A2 ≠ matka | ojciec przejmuje zasiłek za ten okres po 8 tyg. (art. 29 ust. 6, art. 180 §10–11 KP) | 📄 zaświadczenia |
| K4 | Czy matka zmarła albo porzuciła dziecko? Data | `matka_zgon_porzucenie` | A2 ≠ matka | przejęcie od dnia zdarzenia; przy porzuceniu nie wcześniej niż po 8 tyg. (art. 29 ust. 7 i 9) | 👤 📄 oświadczenie |
| K5 | (matka bez tytułu do ubezpieczenia) Czy matka podjęła zatrudnienie na co najmniej pół etatu? Od–do | `matka_zatrudnienie` | K1 = nie | ojciec dostaje zasiłek do wyczerpania wymiaru, najdłużej na czas jej zatrudnienia (art. 29 ust. 10, art. 180 §17 KP) | 👤 📄 oświadczenie |
| K6 | Czy ojciec (członek rodziny) przerwie działalność zarobkową, żeby opiekować się dzieckiem, albo dostanie urlop od pracodawcy? | `przerwanie_dzialalnosci` | A2 ≠ matka | warunek przejęcia zasiłku przez osobę, która nie jest pracownikiem | 👤 |
| K7 | Za jaki okres i w jakiej stawce wypłacono już zasiłek matce? | `wyplacono_matce{}` | A2 ≠ matka | okres zasiłku ojca zmniejsza się o okres wypłacony matce (art. 29a ust. 2) | 📄 zaświadczenie płatnika |

## L. Urlop rodzicielski – plan, podział, łączenie z pracą

| ID | Pytanie | Pole | Pokaż, gdy | Po co | Źródło |
|---|---|---|---|---|---|
| L1 | Plan części urlopu: dla każdej części kto (matka / ojciec), od–do, czy jednocześnie z drugim rodzicem | `rodzicielski_czesci[]` | ścieżka rodzicielska | pula 41/43 (65/67) tyg. wspólna dla obojga; po 9 tyg. nieprzenoszalnych dla każdego rodzica; razem najwyżej 5 części; do końca roku, w którym dziecko kończy 6 lat; przy jednoczesnym korzystaniu łączny wymiar nie przekracza puli (art. 182¹a, 182¹c KP; art. 29a ust. 3) | 👤 📄 ZAM |
| L2 | Ile urlopu rodzicielskiego już wykorzystano (tygodnie, liczba części, stawka)? | `rodzicielski_wykorzystany{}` | ścieżka rodzicielska | limit części i puli; liczą się także wnioski osób, które nie są pracownikami (art. 182¹d §2 KP) | 🏛 📄 |
| L3 | Czy w trakcie części urlopu będziesz pracować u tego samego pracodawcy? W jakim wymiarze (najwyżej ½) i przez ile tygodni? | `laczenie_praca[]{wymiar, od, do}` | B1 ∋ umowa o pracę | zasiłek maleje proporcjonalnie (art. 31 ust. 4a); urlop wydłuża się o liczbę tygodni × wymiar, najwyżej do 82/86 (130/134) tyg. (art. 182¹e–f KP) | 👤 |
| L4 | Czy wydłużoną część urlopu też chcesz łączyć z pracą? W jakim wymiarze? | `laczenie_wydluzenia` | L3 niepuste | wzór art. 182¹f §7 KP (długość ÷ (1 − wymiar)) | 👤 |

## M. Urlop ojcowski

| ID | Pytanie | Pole | Pokaż, gdy | Po co | Źródło |
|---|---|---|---|---|---|
| M1 | Plan: 14 dni jednorazowo czy 2 części po co najmniej 7 dni? Daty | `ojcowski_czesci[]` | A2 = ojciec | 2 tyg. ze 100%; do ukończenia przez dziecko 12 mies.; liczba dzieci nie wydłuża urlopu (art. 182³ KP) | 👤 📄 |
| M2 | Czy wykorzystałeś już część urlopu ojcowskiego? Czy zasiłek za urlop ojcowski pobrałeś z innego tytułu? | `ojcowski_wykorzystany`, `ojcowski_inny_tytul` | A2 = ojciec | limit 14 dni; wymagane oświadczenie (§33 rozporządzenia) | 👤 🏛 |
| M3 | (adopcja) Data uprawomocnienia postanowienia o przysposobieniu | `przysposobienie_prawomocne` | A1 ∋ przyjęcie i A2 = ojciec | 12 mies. od uprawomocnienia, najpóźniej do 14. urodzin dziecka | 📄 postanowienie |

## N. Przyjęcie dziecka na wychowanie (adopcja, rodzina zastępcza)

| ID | Pytanie | Pole | Pokaż, gdy | Po co | Źródło |
|---|---|---|---|---|---|
| N1 | Forma przyjęcia (przysposobienie z wnioskiem do sądu / rodzina zastępcza niezawodowa / rodzina zastępcza zawodowa / inna) | `forma_przyjecia` | A1 ∋ przyjęcie | zawodowa rodzina zastępcza i „inna” → brak prawa (art. 29 ust. 1 pkt 2–3) | 👤 📄 orzeczenie lub umowa ze starostą |
| N2 | Data przyjęcia dziecka na wychowanie | `data_przyjecia` | A1 ∋ przyjęcie | początek uprawnień; wniosek o urlop 7 dni od przyjęcia, start najpóźniej po 21 dniach (art. 183 §6 KP); 81,5% przy wniosku do 21 dni | 👤 📄 oświadczenie |
| N3 | Data wystąpienia do sądu o przysposobienie | `data_wniosku_sad` | N1 = przysposobienie | warunek prawa | 📄 zaświadczenie sądu |
| N4 | Data urodzenia każdego dziecka | `dziecko_data_ur[]` | A1 ∋ przyjęcie | rodzina zastępcza: do 7 lat (10 przy odroczeniu); przysposobienie: do 14 lat; urlop kończy się z limitem wieku, ale trwa co najmniej 9 tyg.; wtedy rodzicielski 38 (62) tyg. (art. 183 §1–4² KP) | 📄 |
| N5 | Czy dziecku odroczono obowiązek szkolny? | `odroczenie_szkolne` | N1 = rodzina zastępcza | limit 10 lat | 📄 decyzja |
| N6 | Ile dzieci przyjęto jednocześnie? | `liczba_przyjetych` | A1 ∋ przyjęcie | 20/31/33/35/37 tyg.; rodzicielski 41/43 | 👤 📄 |
| N7 | Czy jako rodzina zastępcza korzystałeś(-aś) już z urlopu na warunkach urlopu macierzyńskiego lub rodzicielskiego dla tego dziecka? Ile? | `wykorzystane_jako_rz{}` | N1 = przysposobienie | wymiar zmniejsza się o wykorzystane okresy (art. 183 §7–8 KP) | 👤 🏛 |

Pytania wspólne: G4 („Za życiem”), J2 (wariant 81,5% liczony od przyjęcia), L1–L4, M3.

## O. Podstawa wymiaru – pracownik

| ID | Pytanie | Pole | Pokaż, gdy | Po co | Źródło |
|---|---|---|---|---|---|
| O1 | Data powstania prawa do zasiłku (pierwszy dzień zwolnienia, porodu albo przyjęcia) | `data_prawa` (wyliczane) | zawsze przy kwocie | wyznacza 12 miesięcy kalendarzowych wstecz (art. 36 ust. 1) | 📄 |
| O2 | Czy tuż przed (przerwa krótsza niż miesiąc kalendarzowy) pobierałaś inny zasiłek, np. chorobowy w ciąży? Jaka była jego podstawa? | `poprzedni_zasilek{data_do, podstawa}` | zawsze przy kwocie | podstawy nie ustala się na nowo (art. 43), chyba że zmienił się wymiar etatu | 🏛 📄 Z-3, decyzje |
| O3 | Od kiedy jesteś zatrudniony(-a) u tego płatnika bez przerwy? | `zatrudnienie_od` | B1 ∋ umowa o pracę | krócej niż 12 mies. → pełne miesiące; krócej niż 1 mies. → wynagrodzenie z umowy (art. 36 ust. 2, art. 37) | 📄 Z-3 pkt 4 |
| O4 | Wynagrodzenie za każdy z 12 miesięcy: składniki stałe, składniki zmienne, dni przepracowane i obowiązujące, przyczyna nieprzepracowania | `miesiace[]` | B1 ∋ umowa o pracę | miesiące z mniej niż połową czasu pracy pomija się; pozostałe uzupełnia się do pełnego miesiąca; minus 13,71% (art. 38, załącznik ZUS) | 📄 Z-3 pkt 16 · 👤 tryb uproszczony: „średnie brutto z 12 mies.” |
| O5 | Premie i nagrody kwartalne (4 kwartały) oraz roczne (poprzedni rok) | `premie_kwartalne[]`, `premie_roczne` | jw. | doliczane po 1/12 (art. 42) | 📄 Z-3 |
| O6 | Czy któreś składniki przysługują też w czasie zasiłku albo tylko do określonego terminu? | `skladniki_wylaczone[]` | jw. | pomija się je w podstawie (art. 41) | 📄 Z-3 |
| O7 | Czy w tym okresie zmienił się wymiar etatu? Kiedy? | `zmiana_etatu{data, nowy}` | jw. | podstawa według nowego wymiaru (art. 40) | 📄 Z-3 pkt 4 |
| O8 | Czy u tego pracodawcy masz też umowę zlecenia lub o dzieło? Kwoty za kolejne miesiące | `umowy_u_pracodawcy[]` | jw. | przychód wliczany do podstawy (Z-3 pkt 17) | 📄 Z-3 |

Reguły bez pytań: podstawa przy pełnym etacie nie niższa niż minimalne wynagrodzenie minus 13,71% (art. 45); dzienna stawka = 1/30 podstawy (art. 36 ust. 3).

## P. Podstawa wymiaru – zleceniobiorca

| ID | Pytanie | Pole | Pokaż, gdy | Po co | Źródło |
|---|---|---|---|---|---|
| P1 | Przychód (podstawa składek) za każdy z 12 miesięcy oraz dni przepracowane i obowiązujące | `przychod_miesiace[]` | B1 ∋ zlecenie | średnia minus 13,71% (art. 48, art. 3 pkt 4); miesiące z pracą krótszą niż pół miesiąca przez zasiłki są pomijane (art. 50) | 📄 Z-3a pkt 14 |
| P2 | Czy to kolejne umowy z tym samym zleceniodawcą bez przerwy? | `ciaglosc_zlecen` | B1 ∋ zlecenie | okres nieprzerwanego ubezpieczenia (Poradnik) | 📄 🏛 |
| P3 | Jeśli zachorowałaś (urodziłaś) w pierwszym miesiącu: kwota przychodu z umowy za ten miesiąc | `przychod_umowny` | ubezpieczenie krótsze niż miesiąc | art. 49 ust. 1 pkt 2 | 📄 umowa |
| P4 | Czy przed tym ubezpieczeniem było inne, zakończone najwyżej 30 dni wcześniej? | `poprzedni_tytul_30dni` | ubezpieczenie krótsze niż 12 mies. | łączenie okresów (art. 48a ust. 2, art. 49 ust. 2) | 🏛 |

## Q. Podstawa wymiaru – działalność gospodarcza

| ID | Pytanie | Pole | Pokaż, gdy | Po co | Źródło |
|---|---|---|---|---|---|
| Q1 | Zadeklarowana podstawa składki chorobowej za każdy z ostatnich 12 miesięcy | `podstawa_deklarowana[]` | B1 ∋ działalność | średnia minus 13,71%; limit 20 321,30 zł w 2026 r. (załącznik ZUS) | 🏛 📄 Z-3b, poświadczenie |
| Q2 | Rodzaj składek: standardowe / preferencyjne / mały ZUS+ / dobrowolnie wyższa podstawa | `rodzaj_skladek` | jw. | „najniższa podstawa” we wzorze art. 48a (ust. 5) | 🏛 |
| Q3 | Liczba pełnych miesięcy ubezpieczenia chorobowego z tytułu działalności | `miesiace_ubezpieczenia` | jw. | poniżej 12 → wzór art. 48a: najniższa podstawa + (nadwyżka ÷ 12) × liczba miesięcy | 🏛 |
| Q4 | Czy były przerwy w ubezpieczeniu z powodu nieopłacenia albo spóźnienia składki? | `przerwy_skladkowe[]` | jw. | uwzględnia się wtedy także miesiące sprzed przerwy (art. 48a ust. 4) | 🏛 |
| Q5 | Czy w okresie obliczeniowym były miesiące, w których przez zasiłki prowadziłaś działalność krócej niż pół miesiąca? | `miesiace_niepelne[]` | jw. | wyłączenie z podstawy (art. 50) | 🏛 |

Zadłużenie: pytanie B8.

## R. Kwota końcowa

| ID | Pytanie | Pole | Pokaż, gdy | Po co | Źródło |
|---|---|---|---|---|---|
| R1 | Czy masz prawo do zasiłku macierzyńskiego z więcej niż jednego tytułu? Kwoty z pozostałych tytułów; który płatnik ma wypłacić podwyższenie? | `inne_zasilki_mac[]` | zawsze przy zasiłku macierzyńskim | podwyższenie do kwoty świadczenia rodzicielskiego, gdy łączna kwota jest niższa; proporcjonalnie za część miesiąca (art. 31 ust. 3a–3c, art. 62 ust. 4–6) | 👤 📄 oświadczenie |
| R2 | (opcjonalnie) Czy płatnik pomniejsza zaliczkę na PIT (złożony PIT-2, stawka)? | `pit{}` | gdy pokazujemy kwotę netto | Poradnik porównuje z kwotą świadczenia rodzicielskiego zasiłek pomniejszony o zaliczkę na PIT | 👤 |

## S. Ryzyka (ostrzeżenia, nie automatyczna odmowa – wymaganie h)

| ID | Pytanie | Pole | Pokaż, gdy | Ostrzeżenie | Źródło |
|---|---|---|---|---|---|
| S1 | Kiedy zawarto umowę, otwarto działalność albo zgłoszono się do dobrowolnego ubezpieczenia chorobowego? | `data_zgloszenia` | zawsze | zgłoszenie w ciąży lub tuż przed nią → ZUS może badać pozorność umowy | 🏛 📄 |
| S2 | Czy w czasie ciąży podwyższono wynagrodzenie albo deklarowaną podstawę składek? Kiedy i o ile? | `podwyzka_w_ciazy{}` | zawsze | ZUS może ustalić niższą podstawę | 👤 🏛 |
| S3 | Czy przed porodem planujesz rozwiązać umowę, zamknąć lub zawiesić działalność, zakończyć zlecenie albo wyrejestrować się z dobrowolnego ubezpieczenia chorobowego? | `plan_ustania{}` | A1 ∋ ciąża | brak ubezpieczenia w dniu porodu = brak zasiłku macierzyńskiego (poza wyjątkami z sekcji F) | 👤 |
| S4 | Czy opłacasz składki terminowo? | `terminowosc_skladek` | B1 ∋ działalność | zadłużenie i przerwy w ubezpieczeniu (B8, Q4) | 🏛 |
| S5 | Praca w czasie zwolnienia | pytanie D6 | D1 niepuste | utrata zasiłku | 👤 |

## T. Zasiłek opiekuńczy (zgodnie z listą świadczeń; poza punktami a–j treści wyzwania)

| ID | Pytanie | Pole | Pokaż, gdy | Po co | Źródło |
|---|---|---|---|---|---|
| T1 | Nad kim sprawujesz opiekę? (zdrowe dziecko do 8 lat: nieprzewidziane zamknięcie żłobka, przedszkola lub szkoły [zawiadomienie mniej niż 7 dni wcześniej], choroba niani lub dziennego opiekuna, poród lub choroba drugiego rodzica stale opiekującego się dzieckiem, jego pobyt w szpitalu, izolacja dziecka / chore dziecko do 14 lat / dziecko z niepełnosprawnością do 18 lat / inny chory członek rodziny) | `opieka_typ` | A1 ∋ opieka | rodzaj i limit dni (Poradnik) | 👤 📄 |
| T2 | Data urodzenia dziecka albo stopień pokrewieństwa | `podopieczny{}` | A1 ∋ opieka | progi 8, 14 i 18 lat; członek rodziny musi mieszkać we wspólnym gospodarstwie | 👤 |
| T3 | Czy jest domownik, który może zapewnić opiekę? | `inny_domownik` | A1 ∋ opieka | „tak” = brak zasiłku, chyba że chore dziecko ma mniej niż 2 lata; lista osób, które nie są takim domownikiem (Poradnik) | 👤 |
| T4 | Ile dni zasiłku opiekuńczego w tym roku pobrałeś(-aś) Ty, drugi rodzic lub małżonek, inny członek rodziny? | `dni_opiekuncze_rok{}` | A1 ∋ opieka | limity: 60 dni (dzieci do 14 lat) / 30 (chore dziecko z niepełnosprawnością 14–18) / 14 (pozostali), łącznie najwyżej 60 dni w roku (zał. 7 pkt 6) | 👤 🏛 |
| T5 | Okres opieki (e-ZLA albo oświadczenie) | `opieka_od_do` | A1 ∋ opieka | okres wypłaty | 🏛 📄 |
| T6 | Czy dziecko ma orzeczenie o znacznym stopniu niepełnosprawności (albo ze wskazaniami)? | `orzeczenie_niepelnosprawnosci` | T1 ∋ niepełnosprawność | wyższy limit wieku | 📄 |

Reguły: 80% podstawy; bez okresu wyczekiwania; dotyczy go zadłużenie z B8. W dostarczonym wyciągu ustawy brakuje art. 32–35, więc reguły pochodzą z Poradnika.

---

## Macierz: świadczenie → potrzebne pytania

| Świadczenie | Warunki prawa | Okres | Kwota |
|---|---|---|---|
| Zasiłek chorobowy w ciąży | A1, B1, B4–B6, B8, B10–B11, D1, D4–D6 | D1–D3, A4 | C1, O/P/Q (100%) |
| Świadczenie rehabilitacyjne | E1–E2, B10 | E3 | O/P/Q, E3–E4 |
| Zasiłek w wysokości zasiłku macierzyńskiego | F1–F4, B3 | F1 → G1/G2 | O (100%) |
| Urlop macierzyński | A2, B1 (umowa o pracę), G1–G3, G5 | J1, J4, I1–I3, K2–K5 | – |
| Zasiłek macierzyński za okres urlopu macierzyńskiego | A2, B4, B7, B8, F (wyjątki), K | G2, G3, J1, J4, G5, K7 | J2, O/P/Q, R1 |
| Zasiłek przy martwym urodzeniu lub zgonie dziecka | I1, B4, B7 | I1–I3, G2 | O/P/Q (100%) |
| Uzupełniający urlop macierzyński i zasiłek | H1–H5, B4 | H1–H3 | O/P/Q (100%) |
| Urlop rodzicielski i zasiłek | B1/B4, K1, A3 | G3, G4, L1–L4, J3 | J2, J3, L3, O/P/Q, R1 |
| Urlop ojcowski i zasiłek | A2, B4/B7, M2 | M1, M3, G2 | O/P/Q (100%) |
| Urlop na warunkach urlopu macierzyńskiego i zasiłek | N1–N3, B4, B7 | N4–N7 | J2, O/P/Q |
| Urlop rodzicielski przy przyjęciu dziecka | N1–N5 | N4, N6, N7, G4, L1–L4 | J2, O/P/Q |
| Zasiłek opiekuńczy | T1–T3, B4, B8 | T4–T5 | O/P/Q (80%) |

---

## Parametry do panelu administracyjnego (stałe, nie pytania)

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
| Okres wyczekiwania | 30 dni (obowiązkowe) / 90 dni (dobrowolne); wliczana przerwa do 30 dni |
| Okres zasiłkowy | 182 dni / 270 dni (ciąża); przerwa 60 dni; po ustaniu 91 dni (nie w ciąży) |
| Wynagrodzenie chorobowe | 33 dni / 14 dni (50+) |
| Świadczenie rehabilitacyjne | maks. 12 mies.; kwartalny wskaźnik waloryzacji |
| Składki odliczane od podstawy | 13,71% |
| Minimalne wynagrodzenie 2026 | 4 806 zł → minimalna podstawa 4 147,10 zł |
| Maks. podstawa przy dobrowolnym ubezpieczeniu 2026 | 23 550 zł → 20 321,30 zł |
| Próg zadłużenia | 1% minimalnego wynagrodzenia (48,06 zł); spłata w 6 mies. |
| Kwota świadczenia rodzicielskiego (podwyższenie) | 1 000 zł (z pisma ZUS w sprawie z 2025 r.); do potwierdzenia na 2026 |
| Duży płatnik | ponad 20 ubezpieczonych, stan na 30.11 poprzedniego roku |
| Przedawnienie | 6 mies. (3 lata przy błędzie płatnika lub ZUS) |
| Opiekuńczy – limity | 60 / 30 / 14 dni; łącznie 60 dni w roku |
| Zasiłek pogrzebowy (informacja) | 7 000 zł |
| Tydzień urlopu / miesiąc zasiłku | 7 dni kalendarzowych / 30 dni (stawka dzienna = 1/30) |

---

## Do wyjaśnienia z mentorami ZUS

1. **Art. 183 §3 i §4 pkt 3 KP:** kiedy dokładnie przysługuje 9 tyg. urlopu na warunkach urlopu macierzyńskiego i 38 tyg. rodzicielskiego przy przyjęciu dziecka? Czy wtedy, gdy limit wieku skróciłby urlop poniżej 9 tyg.?
2. **Kwota świadczenia rodzicielskiego w 2026 r.** i to, czy porównujemy z nią zasiłek brutto, czy po zaliczce na PIT (Poradnik mówi o kwocie po PIT).
3. **Tabela minimalnej podstawy 2026** jest pusta w załączniku ZUS; wyliczyliśmy 4 147,10 zł. Brakuje też najniższych podstaw dla działalności (standardowej i preferencyjnej) na 2026 r.
4. **Wariant 81,5% przy urlopie zaczętym przed porodem:** jak rozliczyć 100% wypłacone przed porodem?
5. **Zasiłek opiekuńczy:** wyciąg ustawy nie zawiera art. 32–35. Czy reguły z Poradnika wystarczą? Czy w ogóle oczekujecie go w kalkulatorze?
6. **Formularze ZUR, ZAO i Z-3b** zlikwidowano od 24.10.2026, ale występują w sprawach testowych. Aplikacja ma je tylko czytać, a nowe wnioski generować na ZAM?
7. **Art. 9 ust. 4 i art. 17 ust. 1d–1e** wchodzą w życie 1.01.2027. Uwzględniać datę wejścia w życie jako parametr?
