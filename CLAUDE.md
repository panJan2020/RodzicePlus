# CLAUDE.md – Zasiłkowy Przewodnik Przyszłego Rodzica

> Ten plik czyta Claude na początku każdej sesji. Opisuje projekt, architekturę, zasady i plan pracy.
> Jeśli coś tutaj jest nieaktualne, zaktualizuj ten plik w tym samym commicie co zmianę.

---

## 1. O projekcie

**Wyzwanie:** „Zasiłkowy Przewodnik Przyszłego Rodzica” – Zakład Ubezpieczeń Społecznych, **HackNation 2026,
Bydgoszcz, 21–22 listopada 2026**. Czasu jest mało: liczy się **działające demo**, nie kompletność kodu.

**Cel aplikacji:** pomóc przyszłym rodzicom, kobietom w ciąży, rodzicom adopcyjnym i rodzinom zastępczym:
- sprawdzić, jakie świadczenia z ZUS im przysługują (albo nie i dlaczego),
- policzyć okres i wysokość zasiłku dla siebie i drugiego rodzica,
- dowiedzieć się, jakie dokumenty, gdzie i kiedy złożyć,
- uniknąć utraty lub obniżenia świadczeń,
- znaleźć wsparcie w trudnych sytuacjach.

**Kryteria oceny jury:** związek z wyzwaniem 25% · pomysł 20% · oryginalność 15% ·
**kompletność i UX 25%** · potencjał wdrożeniowy 15%.

**Jak jury testuje:** otwiera demo (stronę WWW), wgrywa lub wybiera **przykładowe wnioski PDF z zestawów ZUS**,
sprawdza, czy aplikacja poprawnie ustala ubezpieczenie i **czy wyliczenia są poprawne**. Przegląda też strukturę kodu w repo.

**Zespół:** Janek (programista, głównie frontend Flutter) + dwie osoby nieprogramujące, pracujące z agentami AI
(głównie backend, treści, testy na sprawach ZUS). Kod musi być prosty, przewidywalny i dobrze opisany.

**Repozytorium:** https://github.com/panJan200/Rodzice

---

## 2. Jak Claude raportuje zmiany (OBOWIĄZKOWE po każdym prompcie, w którym zmieniono pliki)

Po wykonaniu zadania zakończ odpowiedź raportem w tym formacie, **prostym językiem** (czytają go też osoby
nieprogramujące):

```
## Co zrobiłem
<1–3 zdania: co się zmieniło z punktu widzenia użytkownika aplikacji lub zespołu>

## Gdzie w architekturze
| Obszar | Pliki | Co się zmieniło |
|---|---|---|
| 🖥️ Frontend – Widok (View) | ... | ... |
| 🧠 Frontend – ViewModel | ... | ... |
| 🔌 Frontend – Repozytorium / API | ... | ... |
| 🌐 Backend – Endpoint REST | ... | ... |
| ⚖️ Backend – Reguły prawne | ... | ... |
| 🧮 Backend – Kalkulator | ... | ... |
| ⚙️ Parametry prawne | ... | ... |
| 📄 Odczyt skanów (Claude API) | ... | ... |
| ✅ Testy | ... | ... |
| 📚 Dokumentacja | ... | ... |
(tylko wiersze, których dotyczyła zmiana)

## Jak sprawdzić
<kroki: komenda albo „otwórz ekran X, kliknij Y, powinno być Z”; na telefonie i komputerze, jeśli dotyczy UI>

## Postęp wymagań
<np. „FR-12: ✅ zrobione” / „FR-15: 🟡 częściowo – brakuje art. 48a”>

## Uwagi / ryzyka
<czego nie zrobiłem, co wymaga decyzji, znane ograniczenia; pomiń, jeśli brak>
```

Zasady raportu:
- Nie wklejaj całych plików do raportu. Opisuj **skutek**, nie każdą linijkę.
- Jeśli zmiana dotyka kontraktu API, napisz to wprost: „⚠️ Zmiana API – zaktualizowano docs/api.md i modele Dart”.
- Po zakończeniu wymagania zaznacz je w sekcji 12 tego pliku (`[ ]` → `[x]`).

---

## 3. Architektura

```
Przeglądarka (telefon / komputer)
   │  Flutter Web – MVVM
   │  View ──► ViewModel ──► Repository ──► ApiClient
   ▼                                           │ REST / JSON
Backend – Python FastAPI                       ▼
   api/ (cienka warstwa HTTP)
     ├─► questions/  katalog pytań + warunki („co zapytać dalej”)
     ├─► rules/      prawo do świadczeń: PRZYSŁUGUJE / NIE / BRAK DANYCH + uzasadnienie
     ├─► calculator/ wymiary urlopów, podstawa wymiaru, kwoty, oś czasu
     ├─► params/     liczby z przepisów (JSON, wersjonowane datą)
     ├─► extraction/ Claude API – odczyt skanów do JSON (tylko odczyt!)
     ├─► storage/    dane spraw (w pamięci; podmienialne na bazę)
     └─► mocks/      symulacja mObywatel, ZUS, e-ZLA, PUE
```

### Struktura repozytorium
```
rodzice/
├── CLAUDE.md                ten plik
├── README.md                uruchomienie, wdrożenie, użycie AI
├── docs/
│   ├── architektura.md      decyzje i wyzwania
│   ├── api.md               kontrakt REST (umowa front ↔ back)
│   ├── wymagania.md         FR-01..FR-31 (szczegóły)
│   └── pytania_kalkulator.md  pytania, pola, przepisy, parametry prawne
├── data/sprawy_zus/         PDF-y od ZUS – TYLKO lokalnie, w .gitignore
├── backend/
│   ├── app/{api,domain,questions,rules,calculator,params,extraction,storage,mocks}/
│   ├── app/main.py, app/config.py
│   ├── tests/               pytest; tests/golden = sprawy ZUS (lokalnie)
│   ├── requirements.txt, .env.example
└── frontend/
    ├── pubspec.yaml
    └── lib/
        ├── main.dart, app.dart
        ├── core/            config, router, theme, responsive, session
        ├── data/            api_client.dart, models/, repositories/
        ├── shared/widgets/  wspólne komponenty UI
        └── features/<ekran>/<ekran>_view.dart + <ekran>_viewmodel.dart
```

### Kluczowe decyzje (nie zmieniać bez uzgodnienia z zespołem)
1. **Jeden profil sprawy dla wszystkich źródeł danych.** Kreator, mock ZUS i odczyt skanów zapisują do
   `Sprawa → Osoba → pola`. Każda wartość to `FieldValue` ze źródłem (`uzytkownik | zus | dokument | wyliczone`),
   dokumentem, stroną, pewnością i flagą `potwierdzone`. Kreator pyta tylko o brakujące pola.
2. **Sprawa = wiele dokumentów.** Jeden dokument ma tylko część informacji. Dane z kolejnych PDF-ów są scalane,
   a sprzeczności zapisywane jako `Konflikt` do rozstrzygnięcia przez użytkownika.
3. **Trzy stany wyniku:** `przysluguje` / `nie_przysluguje` / `brak_danych` (z listą brakujących pól i podpowiedzią,
   jaki dokument je zawiera).
4. **AI tylko czyta dokumenty. Decyzje i kwoty liczy deterministyczny kod z testami.**
5. **Pytania i warunki w backendzie** (`questions/katalog.json`). Flutter renderuje je dynamicznie.
   Ten sam katalog generuje schemat odczytu dla Claude.
6. **Parametry prawne poza kodem**, w `params/params_*.json` z polem `obowiazuje_od`. Do wyliczeń bierzemy
   wersję obowiązującą w dniu powstania prawa do świadczenia. Edycja w panelu admina.

---

## 4. Twarde zasady (zawsze)

1. **Nigdy nie commituj dokumentów ZUS** (`data/sprawy_zus/`, `*.pdf`) ani danych z nich odczytanych.
   Regulamin wyzwania zabrania ich kopiowania i rozpowszechniania.
2. **Klucz Claude API tylko w `backend/.env`.** Nigdy w kodzie, w repo ani we Flutterze. Wywołania Claude tylko z backendu.
3. **Żadnych „magicznych liczb” z przepisów w kodzie** (20, 41, 0.815, 4806, 13.71…). Tylko `p["..."]` z parametrów.
4. **Logika prawna tylko w backendzie.** Flutter niczego nie liczy, tylko wyświetla wyniki z API.
5. **LLM nie decyduje o prawie do świadczenia i nie liczy kwot.**
6. Kwoty w backendzie w `Decimal`, zaokrąglenie do groszy na końcu (`calculator/podstawa.zl`).
7. Każda nowa reguła prawna = test w `backend/tests/` z numerem artykułu w nazwie, np. `test_urlop_macierzynski_art180`.
8. Nazwy pól = kolumna „Pole” w `docs/pytania_kalkulator.md`. Nowe pole dopisz do `questions/katalog.json`.
9. Zmiana kształtu API = w tym samym commicie aktualizacja `docs/api.md` **i** `frontend/lib/data/models/modele.dart`.
10. Teksty dla użytkownika **po polsku**, prostym językiem, bez żargonu prawniczego. Przepis podawaj w nawiasie
    jako dodatkową informację, np. „(art. 29 ustawy zasiłkowej)”.
11. Nie zmieniaj plików poza zakresem zadania. Małe commity, opis po polsku.
12. Nie używaj logo ZUS ani gov.pl i nie udawaj oficjalnego serwisu. Styl ma być **inspirowany**, a w stopce
    ma być informacja „Prototyp HackNation 2026 – nie jest oficjalnym serwisem ZUS”.

---

## 5. Frontend – Flutter Web, MVVM

**Warstwy:**
| Warstwa | Odpowiada za | Nie może |
|---|---|---|
| View (`*_view.dart`) | wygląd, układ, reakcje na kliknięcia → metody ViewModelu | wołać API, liczyć, trzymać logiki |
| ViewModel (`*_viewmodel.dart`, `ChangeNotifier`) | stan ekranu (dane, `laduje`, `blad`), wywołania repozytorium | importować widżetów ani `BuildContext` |
| Repository (`data/repositories/`) | jedyne źródło danych dla ViewModeli, zamiana JSON → modele | znać UI |
| ApiClient (`data/api_client.dart`) | HTTP, nagłówki, błędy, UTF-8, upload | znać logikę biznesową |

**Zasady:**
- Pakiety: `provider` (ChangeNotifier), `go_router`, `http`, `file_picker`, `intl`. **Nie dodawaj** freezed, get_it,
  bloc, riverpod ani generatorów kodu bez zgody zespołu.
- ViewModel tylko dla ekranów ze stanem lub danymi z API. Ekrany statyczne mogą być samym widokiem.
- ViewModel tworzymy w widoku: `ChangeNotifierProvider(create: (c) => XViewModel(c.read(), c.read()))`.
- Każdy ekran z danymi ma 3 stany: ładowanie / błąd z „Spróbuj ponownie” / treść (`shared/widgets/stan_ladowania.dart`).
- Nowy ekran: `features/<nazwa>/` + trasa w `core/router.dart` + (jeśli w menu) wpis w `core/responsive.dart`.
- **Nie używaj `dart:io`**, bo nie działa w przeglądarce. Pliki obsługuj jako bajty (`withData: true`).
- Adres API tylko z `--dart-define=API_URL=...` (`core/config.dart`).

---

## 6. Responsywność – telefon i komputer

Aplikacja ma wyglądać dobrze **na telefonie (od 360 px) i na komputerze (do 1920 px)**.

- Progi tylko z `core/responsive.dart`: telefon < 600 px, tablet 600–1023 px, komputer ≥ 1024 px.
  Nie wpisuj liczb szerokości w widokach.
- **Nawigacja:** telefon → dolny `NavigationBar` i `AppBar`; tablet/komputer → boczny `NavigationRail` (rozwinięty na komputerze).
- **Szerokość treści:** całość max 1200 px, wyśrodkowana; formularze i kreator max 640 px.
- **Siatki kafelków:** `LayoutBuilder` → 1 kolumna (telefon), 2 (tablet), 3 (komputer).
- **Kalkulator i wyniki:** komputer → dwie kolumny (uprawnienia | okresy i kwoty); telefon → jedna pod drugą.
- **Tabele** na telefonie zamieniaj na karty (wiersz tabeli = karta).
- Elementy klikalne min. 48×48 px. Pola liczbowe: `TextInputType.numberWithOptions(decimal: true)`, akceptuj przecinek.
- **Każdy ekran sprawdź** w Chrome DevTools (tryb urządzenia, 375 px i 1440 px) przed oznaczeniem zadania jako zrobione.

---

## 7. UI i UX – styl zus.pl + gov.pl, kolory bliższe zus.pl

**Charakter:** urzędowy, spokojny, czytelny, budzący zaufanie. Dużo bieli, wyraźna hierarchia, zero ozdobników.
Z **gov.pl** bierzemy układ (kafelki usług z ikoną, tytułem i jednym zdaniem opisu, prosty język, ścieżka kroków,
dostępność). Z **zus.pl** bierzemy kolorystykę (zieleń jako kolor wiodący, granat jako uzupełniający) i układ nagłówka
(pasek narzędzi, logo/nazwa, menu sekcji).

### Paleta (jedno miejsce: `frontend/lib/core/theme.dart`)
Wartości startowe **inspirowane zus.pl**. Zweryfikujcie je pipetą (DevTools → Inspect na zus.pl) i poprawcie tylko w `theme.dart`.
| Rola | Kolor | Użycie |
|---|---|---|
| Primary (zieleń ZUS) | `#00843D` | przyciski główne, aktywna pozycja menu, linki akcji |
| Primary dark | `#006B31` | hover/pressed, nagłówek na kolorowym tle |
| Primary light (tło) | `#E6F3EC` | tło wyróżnionych sekcji, aktywny kafelek |
| Secondary (granat) | `#1B365D` | nagłówki sekcji, stopka, ikony informacyjne |
| Tło strony | `#F5F7F6` | tło pod kartami |
| Powierzchnia | `#FFFFFF` | karty, formularze |
| Tekst | `#1A1A1A` / drugorzędny `#4A4A4A` | |
| Błąd / „nie przysługuje” | `#C8102E` | |
| Ostrzeżenie / „brak danych” | `#B35C00` na tle `#FFF4E5` | ryzyka, wartości do sprawdzenia |
| Sukces / „przysługuje” | primary `#00843D` | |
Kontrast tekstu min. **4.5:1** (WCAG AA). Status nigdy tylko kolorem: zawsze też ikona i tekst.

### Typografia i komponenty
- Krój systemowy / Roboto (domyślny Flutter Web) albo Open Sans (podobny do serwisów publicznych). Body 16 px, min. 14 px.
- Hierarchia: H1 (tytuł ekranu) → H2 (sekcja) → treść. Jeden H1 na ekran.
- Przyciski: główny wypełniony zielony, drugorzędny obrysowany, zaokrąglenie małe (4–8 px), jak na stronach urzędowych.
- Karty: białe, delikatna ramka `#DADDDC` lub cień 1 dp, odstępy 16/24 px.
- **Nagłówek:** nazwa aplikacji po lewej, po prawej „Zaloguj (mObywatel)” / imię użytkownika; na telefonie menu dolne.
- **Stopka (granat):** linki do zus.pl, gov.pl/rodzina, PIP, informacja o prototypie, deklaracja dostępności (szkic).

### Wzorce UX
- **Kreator krok po kroku:** jedno pytanie (albo mała grupa) na ekran, pasek postępu, „Wstecz”, możliwość edycji
  odpowiedzi. Pytania o daty → kalendarz, wybór → duże karty do kliknięcia.
- **Wynik zawsze z uzasadnieniem:** „Przysługuje Ci…, ponieważ…”, „Nie przysługuje, ponieważ…”, „Brakuje: … –
  znajdziesz to w dokumencie Z-3 od pracodawcy”.
- **Skąd to wiemy:** przy danych z dokumentów pokazuj źródło („ZAM, str. 7”) i oznaczaj niepewne odczyty AI (pomarańczowe tło).
- **Oś czasu urlopów** (matka/ojciec, kolorowe segmenty, daty, kwoty) – najważniejszy element „wow” kalkulatora.
- Kwoty: `1 234,56 zł` (zawsze brutto, z dopiskiem); daty: `10.07.2026`.
- **Ton:** ciepły i spokojny, szczególnie w trudnych sytuacjach (martwe urodzenie, zgon dziecka). Bez wykrzykników,
  bez „Gratulacje!” w ścieżkach strat.
- **Dostępność:** `ensureSemantics()`, `semanticLabel` przy ikonach, logiczna kolejność fokusu, opisy pól formularzy.

---

## 8. Backend – Python FastAPI (REST)

- Python 3.11+, FastAPI, Pydantic v2, `anthropic`, `pytest`. Uruchomienie: `uvicorn app.main:app --reload` w `backend/`.
- `api/` = cienka warstwa: walidacja, wywołanie `rules/` / `calculator/` / `extraction/`, zwrot modelu Pydantic.
- Reguły: jedna funkcja na świadczenie w `rules/eligibility.py` (albo osobny plik), rejestr `REGULY`. Funkcja **nie rzuca
  wyjątków przy brakach danych**, tylko zwraca `BRAK_DANYCH` z listą pól.
- Błędy HTTP z polskim komunikatem w `detail` (Flutter wyświetla go użytkownikowi).
- CORS: `CORS_ORIGINS` w `.env` + regex dla localhost w trybie dev.
- Dokumentacja API: `/docs` (Swagger) jest źródłem prawdy obok `docs/api.md`.
- Endpointy: `/auth`, `/zus` (mocki), `/sprawy` (profil, odpowiedzi, pytania, dokumenty, zadania),
  `/sprawy/{id}/uprawnienia`, `/sprawy/{id}/kalkulator`, `/info`, `/admin/parametry`, `/health`.

---

## 9. Odczyt skanów – Claude API

- Model z `.env`: `CLAUDE_MODEL` (domyślnie `claude-sonnet-5-5`). Klucz: `ANTHROPIC_API_KEY`.
- PDF wysyłamy jako blok `document` (base64). Zestawy ZUS to **skany** (bez warstwy tekstowej, częściowo odręczne,
  częściowo zamazane), a Claude widzi strony jako obrazy.
- Odpowiedź **wymuszona narzędziem** `zapisz_dane_sprawy` (`tool_choice`). Schemat generowany z `questions/katalog.json`
  (pola z `z_dokumentow: true`). Każde pole ma: wartość, osobę, typ dokumentu, numer strony, pewność 0–1.
- Claude najpierw **klasyfikuje strony** (ZAM, Z-3, Z-3a, Z-3b, ZAS-12, ZAS-53, akt urodzenia, wniosek o urlop, POG,
  pismo ZUS, zrzut systemu…), potem wyciąga pola.
- **Pierwsza strona zestawu ZUS = opis wyniku sprawy.** Trafia do `oczekiwany_wynik` i służy **tylko do testów**,
  nigdy jako dane wejściowe kalkulatora.
- Odczyt trwa 30–90 s → **zadanie w tle**: `POST /sprawy/{id}/dokumenty` → `zadanie_id` → Flutter odpytuje
  `GET /sprawy/zadania/{id}` co 3 s.
- Wartości z pewnością < 0,6 oznaczone w UI do sprawdzenia; użytkownik może poprawić każdą wartość.
- Nie loguj treści dokumentów ani danych osobowych. Loguj tylko zużycie tokenów i czas.
- Prompty i schemat: `backend/app/extraction/{prompts,schema}.py`. Zmieniając prompt, sprawdź wynik na min. 2 sprawach.
- Formularze ZUR, ZAO i Z-3b zlikwidowano od 24.10.2026, ale **występują w sprawach testowych**, więc trzeba je rozpoznawać.
- W opisie projektu (wymóg formalny) wskaż: AI używane do odczytu dokumentów; decyzje i wyliczenia bez AI.

---

## 10. Wiedza dziedzinowa (skrót – szczegóły w `docs/pytania_kalkulator.md`)

Źródła: treść wyzwania (`tresc.pdf`), ustawa zasiłkowa, Kodeks pracy, rozporządzenie z 27.09.2026 (informacje
i dokumenty), rozporządzenie o wnioskach o urlopy (2025), Poradnik ZUS dla rodziców 2026, załącznik ZUS z tabelami.

- **Płatnik vs ubezpieczony vs świadczeniobiorca.** Zasiłek wypłaca pracodawca, gdy zgłasza **ponad 20** ubezpieczonych
  (stan na 30.11 poprzedniego roku). W innym razie, przy działalności i po ustaniu ubezpieczenia – ZUS.
- **Zasiłek chorobowy w ciąży:** e-ZLA z kodem „B” → 100% podstawy; okres zasiłkowy 270 dni; okres wyczekiwania 30 dni
  (ubezpieczenie obowiązkowe) albo 90 dni (dobrowolne); pierwsze 33 dni (14 po 50. r.ż.) płaci pracodawca.
- **Zasiłek macierzyński:** warunek – ubezpieczenie chorobowe w dniu porodu/przyjęcia dziecka (wyjątki: upadłość,
  likwidacja, śmierć pracodawcy, wyrok sądu, umowa przedłużona do porodu). Przy działalności: zadłużenie > 1% minimalnego
  wynagrodzenia blokuje wypłatę do spłaty.
- **Wymiary (tygodnie):** macierzyński 20/31/33/35/37 (1–5+ dzieci); rodzicielski 41/43 („Za życiem” 65/67), w tym
  9 tyg. nieprzenoszalnych dla każdego rodzica, max 5 części, do końca roku 6. urodzin; ojcowski 2 tyg. (1–2 części,
  do 12. miesiąca życia); uzupełniający do 8 albo 15 tyg. (wcześniak, masa, hospitalizacja); martwe urodzenie 8 tyg.
  (min. 7 dni od zgonu); łączenie z pracą max ½ etatu, wydłużenie proporcjonalne do 82/86 tyg.
- **Stawki:** 100% (macierzyński, na warunkach, uzupełniający, ojcowski) · 70% (rodzicielski) · 81,5% za całość przy wniosku
  do 21 dni po porodzie (9 tyg. drugiego rodzica zawsze 70%) · podwyższenie do kwoty świadczenia rodzicielskiego.
- **Podstawa wymiaru:** pracownik – średnie wynagrodzenie z 12 mies. minus 13,71% (miesiące < ½ czasu pracy pomijane,
  pozostałe uzupełniane, min. przy pełnym etacie); zleceniobiorca/działalność – średnia podstawa składek minus 13,71%
  (limit 20 321,30 zł; wzór art. 48a przy ubezpieczeniu < 12 mies.). Przerwa między zasiłkami < 1 miesiąca → ta sama podstawa.
- **Ryzyka (ostrzegać):** umowa lub działalność „dla pozoru”, podwyższenie podstawy w ciąży, brak ubezpieczenia
  w dniu porodu (koniec umowy, wyrejestrowanie, zawieszenie działalności).
- Niejasności do wyjaśnienia z mentorami ZUS: lista na końcu `docs/pytania_kalkulator.md`.

---

## 11. Testy i sprawy ZUS

- `cd backend && pytest` przed każdym commitem zmieniającym backend.
- Sprawy ZUS (PDF) tylko w `data/sprawy_zus/` (lokalnie). Obok: `<nazwa>.oczekiwane.json` z wynikiem z 1. strony i decyzji.
- Skrypt `tests/golden/run` (do zrobienia) przepuszcza sprawy przez odczyt → reguły → kalkulator i drukuje tabelę zgodności.
  Tabela zgodności to argument na prezentację.
- Frontend: ręcznie w Chrome (375 px i 1440 px) według sekcji „Jak sprawdzić” z raportu.

---

## 12. Wymagania funkcjonalne – plan krok po kroku

Na podstawie `tresc.pdf` (sekcja 3 „Oczekiwany rezultat”, sekcja 4–6). Litery w nawiasach = punkty z treści.
Realizujemy **etapami, w podanej kolejności**. Po zakończeniu zaznacz `[x]` i dopisz datę.
Szczegóły i pola danych: `docs/wymagania.md`, `docs/pytania_kalkulator.md`.

### Etap 1 – Fundament i najczęstsza ścieżka (pracownica, 1 dziecko)
- [x] **FR-01** Symulowane logowanie przez mObywatela (konta testowe, bez prawdziwej integracji). _(21.11.2026)_
- [x] **FR-02** Symulowane pobranie z ZUS danych o ubezpieczeniu albo jego braku → profil sprawy (`zrodlo=zus`). _(21.11.2026)_
- [ ] **FR-03** Ręczne wprowadzanie danych w kreatorze (data porodu, rodzaj umowy, data ustania stosunku pracy…); pyta tylko o braki.
- [ ] **FR-11** Kalkulator zasiłku macierzyńskiego: okres i wysokość, liczba dzieci, „Za życiem” (b).
- [ ] **FR-16** Stawki 100% / 70% / 81,5% (wniosek do 21 dni) + 9 tyg. drugiego rodzica po 70% + podwyższenie do świadczenia rodzicielskiego.
- [ ] **FR-18** Wymiary urlopów zgodne z tabelą z załącznika ZUS (z parametrów).
- [ ] **FR-10** Jasny komunikat, gdy świadczenie nie przysługuje – z powodem i przepisem.
- [ ] **FR-20** Wskazanie, kto wypłaca i gdzie złożyć dokumenty (płatnik > 20 osób / ZUS / działalność).

### Etap 2 – Sprawy ZUS i skany (kluczowe przy ocenie)
- [ ] **FR-28** Upload (i/lub wybór) przykładowego wniosku PDF; obsługa wielu plików w jednej sprawie.
- [ ] **FR-29** Odczyt skanu przez Claude API → weryfikacja danych przez użytkownika → sprawdzenie ubezpieczenia → przeliczenie kalkulatora.
- [ ] **FR-15** Indywidualna podstawa wymiaru: pełny tryb z miesięcy (Z-3 pkt 16), zleceniobiorca, działalność (art. 48a) (f).
- [ ] Tabela zgodności wyników aplikacji z decyzjami ZUS na sprawach testowych.

### Etap 3 – Świadczenia w ciąży (a)
- [ ] **FR-05** Symulowany podgląd zwolnień e-ZLA.
- [ ] **FR-07** Zasiłek chorobowy w ciąży: kod B, 100%, okres wyczekiwania, 33/14 dni wynagrodzenia chorobowego, 270 dni, po ustaniu ubezpieczenia.
- [ ] **FR-08** Świadczenie rehabilitacyjne (informacja + wyliczenie 100% w ciąży / 90%→75%).
- [ ] **FR-09** Zasiłek w wysokości zasiłku macierzyńskiego (upadłość, likwidacja, śmierć pracodawcy; wyrok sądu).
- [ ] **FR-04** Symulacja zaświadczenia o zadłużeniu składkowym (ważne dla działalności).

### Etap 4 – Oboje rodzice i elastyczność (c, d)
- [ ] **FR-13** Podział urlopu rodzicielskiego między rodziców: pula, 9 tyg. nieprzenoszalnych, max 5 części, do końca roku 6. urodzin; oś czasu obojga (d).
- [ ] **FR-12** Łączenie pracy z urlopem rodzicielskim: max ½ etatu, proporcjonalne wydłużenie i zmniejszenie zasiłku (c).
- [ ] **FR-17** Sytuacje szczególne: martwe urodzenie / zgon dziecka, urlop uzupełniający (wcześniak, hospitalizacja), przejęcie urlopu przez ojca (po 14 tyg. albo wcześniej), urlop ojcowski.

### Etap 5 – Przyjęcie dziecka na wychowanie (e, j)
- [ ] **FR-14** Kalkulator dla rodziców adopcyjnych i rodzin zastępczych niezawodowych: urlop na warunkach urlopu macierzyńskiego (do 7/10/14 lat), rodzicielski, ojcowski przy przysposobieniu.

### Etap 6 – Informacje, ryzyka i wsparcie (g, h, i)
- [ ] **FR-19** Lista dokumentów, terminów i sposobu złożenia wniosków – dopasowana do sytuacji użytkownika (g).
- [ ] **FR-21** Aktualne formularze (ZAM, Z-3, Z-3a, ZAS-53, ZAS-12; ZUR/ZAO/Z-3b zlikwidowane od 24.10.2026) z linkami do zus.pl.
- [ ] **FR-22** Ostrzeżenia o ryzykach utraty/obniżenia świadczeń: pozorna umowa, podwyższenie podstawy w ciąży, brak ubezpieczenia w dniu porodu (h).
- [ ] **FR-23** Informacja o szczególnej ochronie z Kodeksu pracy (zakaz wypowiedzenia, przedłużenie umowy do porodu).
- [ ] **FR-24** Organizacje wyłącznie charytatywne wspierające przy śmierci dziecka, poronieniu, wcześniactwie, ciężkiej chorobie dziecka (i) – każdą pozycję zweryfikować ręcznie.
- [ ] **FR-27** Przekierowania: zus.pl, gov.pl/web/rodzina/urlop-rodzicielski, pip.gov.pl (rodzicielstwo).

### Etap 7 – Wnioski i PUE (symulacja)
- [ ] **FR-25** Wypełnianie wniosków o urlopy (do zaprojektowania wg rozporządzenia z 2025 r.) i o świadczenia (ZAM) danymi ze sprawy + symulowana wysyłka do pracodawcy/ZUS.
- [ ] **FR-26** Symulacja wniosku o odpis aktu urodzenia (rejestr stanu cywilnego).
- [ ] **FR-06** Symulacja połączenia z PUE/eZUS: zadanie pytania, podgląd danych z konta.

### Etap 8 – Panel administracyjny
- [ ] **FR-30** Edycja parametrów prawnych (stawki, wymiary, kwoty, progi) z datą obowiązywania, bez zmiany kodu.
- [ ] **FR-31** Modułowa konfiguracja (włączanie/wyłączanie modułów, edycja treści informacyjnych).

### Wymagania niefunkcjonalne (przez cały czas)
- [ ] Aplikacja webowa, w pełni responsywna (telefon i komputer) – sekcja 6.
- [ ] REST API między frontendem a backendem.
- [ ] Potencjał wdrożenia produkcyjnego: czysta struktura, parametry poza kodem, testy, dokumentacja.
- [ ] Dostępność (WCAG AA – kontrast, semantyka, klawiatura).
- [ ] Wskazanie funkcji opartych na AI (README + prezentacja).

### Do oddania (wymagania formalne)
- [ ] Tytuł i szczegółowy opis projektu
- [ ] Prezentacja – max 10 slajdów
- [ ] Film – max 3 minuty, w otwartym repozytorium (link)
- [ ] Repozytorium kodu (publiczne, README, bez PDF-ów ZUS i kluczy)
- [ ] Zrzuty ekranu (telefon + komputer)
- [ ] Link do działającego demo z możliwością przetestowania przykładowych wniosków PDF i kalkulatora
- [ ] Materiały graficzne
- [ ] Lista funkcji wspieranych przez AI

---

## 13. Komendy

```bash
# Backend
cd backend
python -m venv .venv && .venv\Scripts\activate      # Windows
pip install -r requirements.txt
copy .env.example .env                               # uzupełnij ANTHROPIC_API_KEY
uvicorn app.main:app --reload                        # http://localhost:8000/docs
pytest

# Frontend
cd frontend
flutter create . --platforms web --project-name rodzice   # tylko za pierwszym razem
flutter pub get
flutter run -d chrome --dart-define=API_URL=http://localhost:8000
flutter build web --release --dart-define=API_URL=https://<backend>
```

Wdrożenie demo: backend → Render/Railway (`uvicorn app.main:app --host 0.0.0.0 --port $PORT`);
frontend → Firebase Hosting / Netlify / GitHub Pages. Przed prezentacją wywołaj `/health` (darmowy hosting usypia serwer).

---

## 14. Słowniczek

| Termin | Znaczenie |
|---|---|
| Płatnik (składek) | pracodawca/zleceniodawca, który zgłasza do ubezpieczenia i (gdy > 20 osób) wypłaca zasiłki |
| Ubezpieczony | osoba, za którą opłacane są składki |
| Świadczeniobiorca | osoba pobierająca świadczenie z ZUS |
| Podstawa wymiaru | kwota, od której liczy się zasiłek (średnie wynagrodzenie/przychód minus 13,71%) |
| Okres wyczekiwania | minimalny czas ubezpieczenia przed prawem do zasiłku chorobowego (30/90 dni) |
| Okres zasiłkowy | maksymalny czas pobierania zasiłku chorobowego (182 dni, w ciąży 270) |
| e-ZLA | elektroniczne zwolnienie lekarskie; kod „B” = ciąża |
| ZAM | wniosek o zasiłek macierzyński (od 24.10.2026 łączy ZUR i ZAO) |
| Z-3 / Z-3a / Z-3b | zaświadczenie płatnika: pracownik / zleceniobiorca / działalność (Z-3b zlikwidowany) |
| ZAS-53 | wniosek o zasiłek chorobowy (osoby niebędące pracownikami) |
| ZAS-12 | zaświadczenie płatnika – zasiłek chorobowy/opiekuńczy za dalszy okres |
| „Za życiem” | zaświadczenie o ciężkiej chorobie/upośledzeniu dziecka → dłuższy urlop rodzicielski |
| PUE / eZUS | Platforma Usług Elektronicznych ZUS |
