# Zasiłkowy Przewodnik Przyszłego Rodzica – opis aplikacji

> Prototyp na HackNation 2026 (wyzwanie ZUS). Nie jest oficjalnym serwisem ZUS.

## 1. Cel i odbiorcy

Aplikacja webowa (RWD: telefon i komputer), która ustala **indywidualnie** dla zalogowanej osoby:

- **czy** przysługuje jej dane świadczenie z ubezpieczenia chorobowego związane z ciążą i rodzicielstwem,
- **za jaki okres** i **w jakiej wysokości**,
- **kto je wypłaca** (pracodawca czy ZUS) i **gdzie, kiedy i z jakimi dokumentami** trzeba wystąpić,
- **co grozi** utratą albo obniżeniem świadczenia,
- **gdzie szukać wsparcia** w trudnych sytuacjach.

Odbiorcy: osoby planujące rodzicielstwo, kobiety w ciąży, rodzice (matka i ojciec), rodzice adopcyjni, niezawodowe rodziny zastępcze.

---

## 2. Model danych

### 2.1. Sprawa → Osoby → Pola

- **Sprawa** to jedna sytuacja życiowa, np. „ciąża i urodzenie dziecka”, „przyjęcie dziecka na wychowanie”. Zawiera osoby, dokumenty, scenariusze i wyniki.
- **Osoba** to każdy, kogo sprawa dotyczy: **matka, ojciec / drugi rodzic, dziecko (dzieci)**. Każda ma własne pola, bo każde z rodziców ma inną umowę, inną podstawę wymiaru i inne prawa. Drugi rodzic nie musi być zalogowany: jego dane można wpisać albo wgrać.
- **Pole** to pojedynczy fakt (odpowiedź na pytanie z katalogu pytań), np. `etat`, `data_porodu`, `ezla` (nazwy z `docs/pytania_kalkulator.md`).

Każda wartość pola zapisuje swoje pochodzenie:

| Atrybut | Znaczenie |
|---|---|
| `wartosc` | np. `0,25` |
| `wystawca` | kto ręczy za tę informację: ZUS, urząd, pracodawca, lekarz, sąd, użytkownik, wyliczenie |
| `kanal` | skąd przyszła do aplikacji: mObywatel, RSC, konto ZUS, e-ZLA, PUE, upload, kreator |
| `dokument`, `strona` | np. „Z-3, str. 7” (dla uploadu) |
| `pewnosc` | 0–1 (dla odczytu AI) |
| `aktywna` | czy to ta wartość jest używana do wyliczeń (patrz konflikty) |

Pole może mieć **kilka wartości z różnych źródeł**. Żadna z nich nie przepada.

### 2.2. Katalog pytań – dane są wyczerpujące

Wszystkie możliwe pola tworzą jeden **katalog pytań** (z warunkami: o co pytać, zależnie od wcześniejszych odpowiedzi). Katalog jest **wyczerpujący**: jeżeli wszystkie pola wymagane przez dane świadczenie są uzupełnione, można jednoznacznie ustalić prawo do niego, jego okres i wysokość.

Każde świadczenie deklaruje, **których pól potrzebuje**. Dzięki temu aplikacja:
- pyta tylko o to, czego brakuje,
- przy braku danych mówi, **jakich pól brakuje i w jakim dokumencie je znaleźć** (np. „wynagrodzenie z ostatnich 12 miesięcy – zaświadczenie Z-3 od pracodawcy”).

### 2.3. Fakty i scenariusze

| | **Fakty** („Moje dane”) | **Scenariusze** (kalkulator) |
|---|---|---|
| Co to | stan rzeczy | wybory i plany do porównania |
| Przykłady | rodzaj umowy, wynagrodzenie, data porodu, liczba dzieci, „Za życiem” | podział urlopu rodzicielskiego między rodziców, praca w trakcie urlopu (wymiar), wniosek o całość urlopu do 21 dni po porodzie (81,5%), termin rozpoczęcia urlopu, przejęcie urlopu przez ojca |
| Ile wersji | jedna aktywna wartość pola | wiele wariantów obok siebie |

Scenariusz **nie nadpisuje faktów**. Użytkownik może porównać np. „wariant A: matka cały rodzicielski” i „wariant B: oboje po połowie, ojciec wraca na ½ etatu”.

---

## 3. Źródła danych

Źródłem jest **wystawca** informacji. **Kanał** to tylko droga, którą informacja dotarła (np. Z-3 od pracodawcy może przyjść przez upload albo z PUE). Wszystkie połączenia z systemami zewnętrznymi są **symulowane**.

| # | Źródło (kanał) | Przykładowe dane |
|---|---|---|
| 1 | **mObywatel / rejestr PESEL** | PESEL, imię, nazwisko, data urodzenia, płeć, adres |
| 2 | **Rejestr stanu cywilnego** (akt urodzenia) | data urodzenia dziecka, liczba dzieci z jednego porodu, rodzice; martwe urodzenie, zgon dziecka |
| 3 | **ZUS – konto ubezpieczonego** (zgłoszenia, raporty RCA) | tytuły ubezpieczenia z datami od–do, chorobowe obowiązkowe / dobrowolne, miesięczne podstawy wymiaru składek, ubezpieczenie w danym dniu |
| 4 | **ZUS – dane płatnika** | NIP, liczba zgłoszonych do ubezpieczenia chorobowego (do / powyżej 20 osób → kto wypłaca), **zadłużenie składkowe** (działalność) |
| 5 | **ZUS – historia świadczeń** | wcześniejsze zasiłki i ich podstawy, wykorzystane dni okresu zasiłkowego, przerwy między zasiłkami |
| 6 | **e-ZLA** | okresy niezdolności do pracy, **kod B** (ciąża), data wystawienia |
| 7 | **PUE / eZUS** | złożone wnioski, status spraw, pisma i decyzje ZUS |
| 8 | **Pracodawca / płatnik** (Z-3, Z-3a, ZAS-12) | wymiar etatu, wynagrodzenia z miesięcy i dni nieprzepracowane, wypłacone wynagrodzenie chorobowe (33/14 dni), udzielone urlopy, data złożenia wniosku o urlop, praca w trakcie urlopu rodzicielskiego |
| 9 | **Upload dokumentów** (kanał dla dokumentów od pracodawcy, lekarza, szpitala, sądu, ZUS) | wnioski ZAM / ZAS-53 / (ZUR, ZAO – archiwalne), zaświadczenie o przewidywanej dacie porodu, „Za życiem”, karta szpitala (wcześniak, hospitalizacja), orzeczenie o niezdolności do samodzielnej egzystencji, postanowienie o przysposobieniu / rodzinie zastępczej, wyrok sądu, akt zgonu |
| 10 | **Użytkownik (kreator)** | wszystko, czego nie ma w innych źródłach, oraz **plany i zamiary** (planowana data porodu, planowane zmiany umowy, zakończenie działalności) |
| 11 | **Wyliczone** | wiek (z daty urodzenia), spełnienie okresu wyczekiwania (30 / 90 dni), przerwy między zasiłkami, kto wypłaca, liczba dni ubezpieczenia |

---

## 4. Wiarygodność danych i konflikty

> Dane wpisane przez użytkownika mogą być niepoprawne. Aplikacja zakłada to od początku.

### 4.1. Konflikty tego samego pola
Konflikt powstaje, gdy jedno pole jednej osoby ma **różne wartości z różnych źródeł** (np. użytkownik wpisał planowaną datę porodu 20.12.2026, a zaświadczenie lekarza wskazuje 30.12.2026).

- Aplikacja **od razu wybiera domyślną wartość** według hierarchii wiarygodności, żeby wynik nie był zablokowany:
  **rejestr ZUS / urzędowy > dokument urzędowy (akt, wyrok, orzeczenie) > dokument pracodawcy lub lekarza > odczyt AI o niskiej pewności > deklaracja użytkownika.**
  Wyjątek: plany i zamiary – tylko użytkownik.
- Zakładka **„Konflikty w danych”** wypisuje wszystkie konflikty. Przy każdym widać wartości, źródła i która jest teraz aktywna. Użytkownik może wybrać inne źródło.
- Niewybrana wartość **nie przepada**. W „Moich danych” po kliknięciu pola rozwija się lista źródeł i można w każdej chwili przełączyć, skąd pole bierze wartość.

### 4.2. Niespójności między polami
Poza konfliktami tego samego pola działają **reguły spójności** między różnymi polami, np.:
- niezdolność do pracy zaczyna się przed datą zatrudnienia,
- wynagrodzenie jest niższe, niż wynika z etatu i płacy minimalnej,
- urlop macierzyński zaczyna się wcześniej niż 6 tygodni przed przewidywaną datą porodu.

Niespójności też trafiają do zakładki konfliktów, jako ostrzeżenia.

### 4.3. Oznaczanie pewności wyniku
Jeżeli wynik opiera się na polach **tylko z deklaracji użytkownika** albo z **niepewnego odczytu AI**, jest oznaczony jako *orientacyjny*, z listą pól, które warto potwierdzić dokumentem.

---

## 5. Świadczenia i wyniki

### 5.1. Obsługiwane świadczenia

**W czasie ciąży**
- zasiłek chorobowy (e-ZLA z kodem B, 100%, okres zasiłkowy 270 dni, okres wyczekiwania, wynagrodzenie chorobowe od pracodawcy),
- świadczenie rehabilitacyjne,
- zasiłek w wysokości zasiłku macierzyńskiego (upadłość, likwidacja, śmierć pracodawcy; naruszenie przepisów potwierdzone wyrokiem).

**Zasiłek macierzyński za okres urlopu**
- macierzyńskiego (w tym przejęcie przez ojca – po 14 tygodniach albo wcześniej w sytuacjach szczególnych),
- uzupełniającego macierzyńskiego (wcześniak, hospitalizacja dziecka),
- rodzicielskiego (pula, 9 tygodni nieprzenoszalnych dla każdego rodzica, do 5 części, „Za życiem”, łączenie z pracą),
- ojcowskiego,
- na warunkach urlopu macierzyńskiego (adopcja, rodzina zastępcza niezawodowa).

**Sytuacje szczególne:** urodzenie martwego dziecka, zgon dziecka, choroba lub śmierć matki, kilkoro dzieci z jednego porodu.

### 5.2. Wynik dla świadczenia

Każde świadczenie ma **zestaw wymagań** (reguły) i zwraca:

| Status | Co widzi użytkownik |
|---|---|
| ✅ **Przysługuje** | okres od–do, kwota (brutto), stawka %, podstawa wymiaru, **kto wypłaca**, uzasadnienie z przepisem |
| 🟡 **Przysługuje pod warunkiem** | np. „o ile w dniu porodu nadal będziesz objęta ubezpieczeniem chorobowym” + powiązane ryzyko |
| ⚠️ **Brak danych** | lista brakujących pól + w jakim dokumencie je znaleźć / jak je uzupełnić |
| ❌ **Nie przysługuje** | **powód**: które dane o tym decydują (np. „brak ubezpieczenia chorobowego w dniu porodu”), przepis, oraz **co można zrobić** |

Uprawnienia i kwoty liczy **deterministyczny kod z testami**. Wszystkie liczby z przepisów (stawki, wymiary, progi, kwoty) są **parametrami** edytowanymi w panelu admina, z datą obowiązywania.

---

## 6. Upload wniosków i spraw

Upload to **kanał danych**, który zasila ten sam profil co pozostałe źródła. Ma też dwie dodatkowe role:

1. **Dla jury i demo:** wgranie przykładowej sprawy ZUS (np. ZAS-53 + kilka Z-3 + pisma i zrzuty ZUS) wystarcza do ustalenia **ubezpieczenia, prawa do świadczenia, okresu i kwoty**. Kreator dopytuje tylko o pojedyncze braki.
2. **Dla użytkownika:** zamiast przepisywać Z-3 czy akt urodzenia, wgrywa skan.

### Przebieg
1. **Przyjęcie pliku** (PDF, skan; wiele plików na sprawę) jako zadanie w tle, z paskiem postępu.
2. **Klasyfikacja stron i podział na dokumenty** – typ (ZAM, ZAS-53, ZUR, ZAO, Z-3, Z-3a, Z-3b, ZAS-12, pismo ZUS, poświadczenie ubezpieczenia, zrzut systemu ZUS, akt urodzenia, zaświadczenie lekarskie…), zakres stron, wariant („pierwszorazowy” / „w kontynuacji”). Jeden PDF może zawierać kilka egzemplarzy tego samego formularza.
3. **Odczyt pól** dla każdego typu dokumentu (AI: Claude API), z numerem strony i pewnością.
4. **Weryfikacja przez użytkownika** – widok „co odczytaliśmy” z podświetleniem niepewnych wartości; każdą można poprawić.
5. **Scalenie z profilem** – wykrycie konfliktów i niespójności.
6. **Kontrola kompletności** – jak u urzędnika ZUS: „do ustalenia prawa brakuje Z-3 od pracodawcy”.
7. **Reguły i kalkulator** – wynik świadczeń.
8. **Porównanie z decyzją ZUS** (tryb demo) – strona z wynikiem sprawy jest rozpoznawana **po treści** (nie po pozycji w pliku), nigdy nie jest używana jako dane wejściowe, tylko do zestawienia „aplikacja vs ZUS”.

Strony wewnętrzne ZUS z zestawów (poświadczenie ubezpieczenia, zrzuty systemu) są traktowane jak dane z systemów ZUS (źródło 3–5). Tak symulowane „pobranie z ZUS” opiera się na prawdziwej sprawie.

---

## 7. Kalkulator zintegrowany

Jeden kalkulator z opcjami (zgodnie z rekomendacją ZUS). Działa:
- **po zalogowaniu** – wypełniony danymi z profilu,
- **bez logowania** – dla osób dopiero planujących rodzicielstwo; dane wpisuje się wprost.

Opcje:
- zdarzenie: **urodzenie / adopcja / rodzina zastępcza niezawodowa** (wiek dziecka),
- liczba dzieci, „Za życiem”, wcześniak / hospitalizacja, martwe urodzenie / zgon dziecka,
- **oboje rodzice**: osobne podstawy wymiaru, podział urlopu rodzicielskiego, przejęcie urlopu macierzyńskiego, urlop ojcowski,
- **łączenie pracy z urlopem rodzicielskim** (wymiar etatu → wydłużenie urlopu i zmniejszenie zasiłku),
- wniosek o całość urlopu do 21 dni po porodzie (81,5%) albo osobno (100% / 70%),
- **indywidualna podstawa wymiaru**: z wynagrodzeń (Z-3), ze zlecenia, z działalności – albo z konkretnej wgranej sprawy.

Wynik:
- **oś czasu** urlopów obojga rodziców (kolorowe segmenty, daty, kwoty miesięczne) z **datą powrotu do pracy** każdego z rodziców,
- tabela okresów i kwot,
- **porównanie scenariuszy** obok siebie (np. łączna kwota, czas opieki każdego z rodziców).

---

## 8. Poradnik krok po kroku, ryzyka i ochrona

Po kliknięciu świadczenia w „Moich świadczeniach” / „Wszystkich świadczeniach” → **„Kroki do otrzymania”**: poradnik step-by-step, **dopasowany do sytuacji**:

- **gdzie złożyć**: do pracodawcy (płatnik zgłaszający powyżej 20 osób do ubezpieczenia chorobowego) czy do ZUS (mniejszy płatnik, zlecenie u niewypłacającego płatnika, działalność, po ustaniu ubezpieczenia),
- **jakie dokumenty**, z linkami do aktualnych wzorów na zus.pl (ZAM, ZAS-53, Z-3, Z-3a, ZAS-12; informacja, że ZUR, ZAO i Z-3b zlikwidowano od 24.10.2026),
- **terminy** (np. 21 dni po porodzie na wniosek z 81,5%, terminy złożenia wniosków o urlopy),
- **jak złożyć**: papierowo, przez PUE/eZUS, przez pracodawcę.

Poradnik jest dostępny także przy statusach:
- **brak danych** – jaki dokument zdobyć i od kogo,
- **nie przysługuje** – co można zrobić (np. zgłoszenie do dobrowolnego ubezpieczenia chorobowego przed porodem).

**Ryzyka** (na początku poradnika i w osobnej sekcji):
- umowa albo działalność zawarta **dla pozoru** → decyzja o niepodleganiu ubezpieczeniu,
- **podwyższenie podstawy wymiaru składek w ciąży** → ustalenie niższej podstawy,
- **brak ubezpieczenia chorobowego w dniu porodu** (niezgłoszenie do dobrowolnego, rozwiązanie umowy, zakończenie zlecenia lub działalności),
- **zadłużenie składkowe** przy działalności,
- zmiany warunków zatrudnienia w ciąży, które wpływają na prawo i wysokość zasiłku.

Ryzyka, które dotyczą zalogowanej osoby, są **podświetlone** na podstawie jej danych (np. umowa zawarta krótko przed niezdolnością do pracy, zmiana podstawy w ciąży).

**Szczególna ochrona z Kodeksu pracy**: zakaz wypowiedzenia w ciąży i w czasie urlopów, przedłużenie umowy na czas określony do dnia porodu; informacja, że ochrona nie dotyczy osób niebędących pracownikami.

**Ton**: spokojny i ciepły, szczególnie w ścieżkach strat (martwe urodzenie, zgon dziecka, poronienie).

---

## 9. Symulacje usług zewnętrznych

| Funkcja | Działanie w prototypie |
|---|---|
| Logowanie przez mObywatela | konta testowe, bez prawdziwej integracji |
| Pobranie danych z ZUS o ubezpieczeniu lub jego braku | mock ZUS (albo dane z wgranej sprawy) |
| **Zaświadczenie o zadłużeniu składkowym** na dzień powstania prawa | wygenerowane zaświadczenie z kwotą zadłużenia i informacją o skutkach |
| **Podgląd e-ZLA** | lista zwolnień z okresami i kodami |
| **PUE / eZUS** | podgląd danych z konta + **„Zadaj pytanie ZUS”** (formularz, symulowana odpowiedź) |
| **Wnioski o urlopy** (zaprojektowane przez nas, wg rozporządzenia z 2025 r.) i **wnioski o świadczenia** (ZAM) | wypełniane danymi ze sprawy, podgląd PDF, **symulowana wysyłka** do pracodawcy lub ZUS |
| **Wniosek o odpis aktu urodzenia** (zupełny / skrócony) | symulacja wniosku do rejestru stanu cywilnego |

---

## 10. Panel administracyjny

- **Parametry prawne** z datą obowiązywania: stawki (100 / 70 / 81,5%), wymiary urlopów, okresy (270 dni, 33/14 dni, 30/90 dni), progi (20 ubezpieczonych, 1% minimalnego wynagrodzenia), kwoty (minimalne wynagrodzenie, świadczenie rodzicielskie, limit podstawy). Do wyliczeń brana jest wersja obowiązująca w dniu powstania prawa.
- **Moduły** – włączanie / wyłączanie funkcji, dodawanie nowych.
- **Treści** – edycja tekstów informacyjnych, ryzyk, listy organizacji i linków.

---

## 11. Ekrany

| # | Ekran | Zawartość |
|---|---|---|
| 1 | **Logowanie** | symulacja mObywatela; wejście do kalkulatora bez logowania |
| 2 | **Start** | podsumowanie: status ubezpieczenia, świadczenia (z kolorowymi statusami), liczba konfliktów i braków, następny krok |
| 3 | **Moje dane** | pola osób w sprawie (ja, drugi rodzic, dziecko), źródło przy każdym polu, przełączanie źródła, uzupełnianie braków (kreator) |
| 4 | **Konflikty w danych** | konflikty pól i niespójności, wybór źródła |
| 5 | **Dokumenty / Wgraj** | upload plików, lista rozpoznanych dokumentów, odczytane dane do potwierdzenia, porównanie z decyzją ZUS |
| 6 | **Ubezpieczenie** | tytuły ubezpieczenia i okresy (z ZUS), e-ZLA, zaświadczenie o zadłużeniu |
| 7 | **Moje świadczenia** | świadczenia dotyczące użytkownika ze statusem, okresem, kwotą, powodem; „Kroki do otrzymania” |
| 8 | **Wszystkie świadczenia** | katalog świadczeń z opisem i wymaganiami |
| 9 | **Kalkulator** | kalkulator zintegrowany, oś czasu, scenariusze |
| 10 | **Wnioski** | wnioski o urlopy, ZAM, odpis aktu urodzenia; symulowana wysyłka; historia |
| 11 | **Lista dokumentów** | dokumenty przydatne w czasie ciąży i rodzicielstwa, z linkami do zus.pl |
| 12 | **Wsparcie i informacje** | ryzyka, ochrona z Kodeksu pracy, **organizacje wyłącznie charytatywne** (śmierć dziecka, poronienie, wcześniactwo, ciężka choroba dziecka), linki: zus.pl, gov.pl/web/rodzina/urlop-rodzicielski, pip.gov.pl |
| 13 | **PUE / Zadaj pytanie** | symulacja połączenia z eZUS |
| 14 | **Moje konto** | dane logowania, drugi rodzic (zaproszenie / dane ręczne), ustawienia |
| 15 | **Panel administratora** | parametry, moduły, treści (osobna rola) |

---

## 12. Wygląd, dostępność, technologia

- Układ wzorowany na **gov.pl** (kafelki usług, prosty język, ścieżki kroków), kolorystyka bliższa **zus.pl** (zieleń wiodąca, granat uzupełniający). Bez logo ZUS i gov.pl; w stopce: „Prototyp HackNation 2026 – nie jest oficjalnym serwisem ZUS”.
- **RWD**: telefon (od 360 px) i komputer (do 1920 px).
- **Dostępność** (WCAG AA): kontrast, semantyka, obsługa klawiaturą; status nigdy tylko kolorem.
- **Technologia**: frontend Flutter Web (MVVM), backend Python FastAPI, **REST API**. ZUS preferuje React/Next.js na froncie, ale wybór technologii jest dowolny.
- **Potencjał wdrożeniowy**: parametry poza kodem, testy reguł na sprawach ZUS, wymienny magazyn danych, dokumentacja API.

## 13. Gdzie używamy AI

| Funkcja | AI? |
|---|---|
| Klasyfikacja stron i odczyt danych ze skanów | ✅ Claude API |
| Ustalanie prawa do świadczeń, wyliczenia okresów i kwot | ❌ deterministyczny kod z testami |
| Treści, ryzyka, poradniki | ❌ przygotowane i zweryfikowane ręcznie |

---

## 14. Pokrycie wymagań z treści zadania

### Oczekiwany rezultat (pkt 3)

| Wymaganie | Gdzie w opisie |
|---|---|
| Uprawnienia ustalane indywidualnie; dane z ZUS i wpisywane przez użytkownika | 2, 3, 5 |
| a) świadczenia w ciąży (chorobowy, rehabilitacyjne, w wysokości macierzyńskiego), także brak uprawnień | 5.1, 5.2 |
| b) kalkulator macierzyńskiego dla obojga rodziców (liczba dzieci, wiek, „Za życiem”) | 7 |
| c) łączenie pracy z urlopem rodzicielskim | 2.3, 7 |
| d) symulacja dla obojga rodziców | 2.1, 2.3, 7 |
| e) / j) adopcja, rodzina zastępcza niezawodowa | 5.1, 7 |
| f) indywidualna podstawa wymiaru, konkretna sprawa z zestawów | 6, 7 |
| g) dokumenty, terminy, sposób złożenia; płatnik czy ZUS | 8 |
| h) zagrożenia utraty / zmiany świadczeń | 5.2 (warunkowo), 8 |
| i) organizacje charytatywne | 11 (ekran 12) |
| Kalkulatory jako jeden zintegrowany kalkulator | 7 |
| Planowanie powrotu do pracy i dzielenia się opieką (pkt 2 wyzwania) | 7 (oś czasu, scenariusze) |
| Trudne sytuacje: martwe urodzenie, wcześniak, choroba lub śmierć matki (pkt 2) | 5.1, 8 (ton), ekran 12 |

### Narzędzie powinno zapewnić możliwość (pkt 3)

| Wymaganie | Gdzie w opisie |
|---|---|
| Logowanie przez mObywatela (symulacja) | 9, ekran 1 |
| Pobranie danych z ZUS o ubezpieczeniu / wprowadzenie danych samemu | 3, 9, ekrany 3 i 6 |
| Zaświadczenie o zadłużeniu składkowym | 9, ekran 6 |
| Podgląd e-ZLA | 9, ekran 6 |
| PUE/eZUS: pytanie, dane z konta | 9, ekran 13 |
| Wypełnienie wniosków o urlopy (do zaprojektowania) i świadczenia + wysyłka | 9, ekran 10 |
| Wniosek o odpis aktu urodzenia | 9, ekran 10 |
| Informacje o podmiotach wsparcia | ekran 12 |
| Przekierowania: zus.pl, gov.pl, PIP | 8, ekran 12 |
| Panel administracyjny parametrów | 10, ekran 15 |

### Wymagania formalne, techniczne i testowe (pkt 4–6)

| Wymaganie | Status |
|---|---|
| Demo WWW z testowaniem przykładowych PDF (upload / wybór), weryfikacja ubezpieczenia, kalkulator | 6, ekran 5 |
| Poprawność wyliczeń na przykładowych wnioskach | 5.2, 6 (porównanie z decyzją ZUS) |
| RWD | 12 |
| REST API, potencjał produkcyjny | 12 |
| Wskazanie funkcji z AI | 13 |
| Opis, prezentacja (max 10 slajdów), film (max 3 min), repozytorium, zrzuty ekranu, materiały graficzne | poza aplikacją – do przygotowania |

---

## 15. Pytania do mentorów ZUS

1. Czy w publicznym demo wolno udostępnić **wybór** przykładowych spraw (hostowanie PDF-ów lub odczytanych danych), czy tylko upload?
2. Czy porównanie z wynikiem ZUS ma obejmować **kwotę** zasiłku, czy wystarczy rozstrzygnięcie (przyznano / odmówiono)?
3. Jak szczegółowo mają wyglądać **wnioski o urlopy** – jeden wniosek łączony (macierzyński + rodzicielski) czy osobne?
