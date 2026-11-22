# CLAUDE.md – Zasiłkowy Przewodnik Przyszłego Rodzica

> Ten plik czyta Claude na początku każdej sesji. Opisuje projekt, zasady i plan pracy.
> Jeśli coś tutaj jest nieaktualne, zaktualizuj ten plik w tym samym commicie co zmianę.

---

## 0. Dokumenty projektu – co czytać

| Plik | Odpowiada na pytanie | Kiedy czytać |
|---|---|---|
| `CLAUDE.md` (ten plik) | jak pracujemy, twarde zasady, plan etapów | zawsze |
| `docs/opis_aplikacji.md` | **CO** budujemy: funkcje, ekrany, pokrycie wymagań ZUS | przed każdym zadaniem – rozdział wskazany w prompcie |
| `docs/architektura.md` | **JAK** to jest zbudowane: moduły, model danych, przepływy, wyzwania | przed zmianą w backendzie lub modelu danych |
| `docs/api.md` | kontrakt REST front ↔ back, kształty JSON | przed każdą zmianą endpointu lub modelu Dart |
| `docs/pytania_kalkulator.md` | pola, pytania, przepisy, parametry prawne | przed dodaniem pola, reguły lub parametru |

**Realizuj tylko to, o co prosi prompt.** Opis aplikacji jest mapą całości, nie listą zadań na jedną sesję.
Jeśli dokumenty są ze sobą sprzeczne, zatrzymaj się i zapytaj, zamiast zgadywać.

---

## 1. O projekcie

**Wyzwanie:** „Zasiłkowy Przewodnik Przyszłego Rodzica” – Zakład Ubezpieczeń Społecznych, **HackNation 2026,
Bydgoszcz, 21–22 listopada 2026**. Czasu jest mało: liczy się **działające demo**, nie kompletność kodu.

**Cel aplikacji:** pomóc przyszłym rodzicom, kobietom w ciąży, rodzicom adopcyjnym i rodzinom zastępczym:
- sprawdzić, jakie świadczenia z ZUS im przysługują (albo nie i dlaczego),
- policzyć okres i wysokość zasiłku dla siebie i drugiego rodzica, porównać warianty podziału urlopu,
- dowiedzieć się, jakie dokumenty, gdzie i kiedy złożyć,
- uniknąć utraty lub obniżenia świadczeń,
- znaleźć wsparcie w trudnych sytuacjach.

**Kryteria oceny jury:** związek z wyzwaniem 25% · pomysł 20% · oryginalność 15% ·
**kompletność i UX 25%** · potencjał wdrożeniowy 15%.

**Jak jury testuje:** otwiera demo (stronę WWW), **wgrywa przykładowe sprawy PDF z zestawów ZUS**, sprawdza, czy
aplikacja poprawnie ustala ubezpieczenie i **czy wyliczenia są poprawne**. Przegląda też strukturę kodu w repo.
Dlatego ścieżka **upload → wynik → porównanie z decyzją ZUS** ma najwyższy priorytet.

**Zespół:** Janek (jedyny programista) + agenci AI. Kod musi być prosty, przewidywalny i dobrze opisany.

**Repozytorium:** https://github.com/panJan200/Rodzice

---

## 2. Jak pracujemy

1. **Jeden prompt = jeden etap albo jego część** (pionowy plaster: backend + API + ekran, który da się kliknąć).
2. **Najpierw plan.** Przed zmianą w więcej niż 2 plikach przedstaw plan: pliki, endpointy, modele, testy, sposób
   sprawdzenia. Kod dopiero po akceptacji.
3. **Nie rozszerzaj zakresu.** Jeśli zauważysz coś do zrobienia poza zadaniem, wpisz to w „Uwagi / ryzyka”.
4. **Sprawdź przed oddaniem:** `pytest` (backend), uruchomienie ekranu w 375 px i 1440 px (frontend).
5. **Commit po zakończonym etapie**, opis po polsku.

6. Tryb hackathonu: nowe testy tylko dla reguł prawnych, kwot i podziału/mapowania dokumentów.
   Nie pisz nowych testów widżetów Fluttera – UI sprawdzam ręcznie (375 px i 1440 px).
   pytest i commit raz na podetap, nie po każdym kroku planu.

### Raport po każdym prompcie, w którym zmieniono pliki (OBOWIĄZKOWY)

```
## Co zrobiłem
<1–3 zdania: co się zmieniło z punktu widzenia użytkownika aplikacji>

## Gdzie w architekturze
| Obszar | Pliki | Co się zmieniło |
|---|---|---|
| 🖥️ Frontend – Widok (View) | ... | ... |
| 🧠 Frontend – ViewModel | ... | ... |
| 🔌 Frontend – Repozytorium / API | ... | ... |
| 🌐 Backend – Endpoint REST | ... | ... |
| 🗂️ Backend – Model danych / scalanie (domain, merge) | ... | ... |
| 🔗 Backend – Źródła danych (sources) | ... | ... |
| ⚖️ Backend – Reguły prawne | ... | ... |
| 🧮 Backend – Kalkulator | ... | ... |
| ⚙️ Parametry prawne / treści | ... | ... |
| 📄 Odczyt skanów (Claude API) | ... | ... |
| ✅ Testy | ... | ... |
| 📚 Dokumentacja | ... | ... |
(tylko wiersze, których dotyczyła zmiana)

## Jak sprawdzić
<kroki: komenda albo „otwórz ekran X, kliknij Y, powinno być Z”; na telefonie i komputerze, jeśli dotyczy UI>

## Postęp
<etap z sekcji 12, np. „Etap 2: 🟡 – upload działa, brak porównania z decyzją ZUS”>

## Uwagi / ryzyka
<czego nie zrobiłem, co wymaga decyzji, znane ograniczenia; pomiń, jeśli brak>
```

Zasady raportu:
- Nie wklejaj całych plików. Opisuj **skutek**, nie każdą linijkę.
- Zmiana kontraktu API: napisz wprost „⚠️ Zmiana API – zaktualizowano docs/api.md i modele Dart”.
- Po zakończeniu etapu zaznacz go w sekcji 12 (`[ ]` → `[x]` + data) i zaktualizuj tabelę pokrycia
  w `docs/opis_aplikacji.md` (rozdział 14), jeśli zmieniło się pokrycie wymagań.

---

## 3. Architektura (skrót – szczegóły w `docs/architektura.md`)

```
Przeglądarka (telefon / komputer)
   │  Flutter Web – MVVM: View ──► ViewModel ──► Repository ──► ApiClient
   ▼                                                              │ REST / JSON
Backend – Python FastAPI                                          ▼
   api/          cienka warstwa HTTP
   sources/      adaptery źródeł danych (symulacje: mObywatel, RSC, ZUS, e-ZLA, PUE)
   extraction/   upload: klasyfikacja stron, podział na dokumenty, odczyt pól (Claude API – tylko odczyt!)
   merge/        scalanie wartości, wybór aktywnej wartości, konflikty, niespójności
   domain/       Sprawa → Osoby → Pola (+ dokumenty, scenariusze, wyniki)
   questions/    katalog pytań = słownik pól + warunki
   rules/        prawo do świadczeń: 4 statusy + uzasadnienie
   calculator/   okresy, podstawa wymiaru, kwoty, oś czasu, scenariusze
   params/       liczby z przepisów (JSON, wersjonowane datą)
   content/      poradniki, ryzyka, organizacje, linki, lista dokumentów
   forms/        wnioski (urlopy, ZAM, odpis aktu) + symulowana wysyłka
   storage/      magazyn spraw (w pamięci; podmienialny na bazę)
```

### Kluczowe decyzje (nie zmieniać bez uzgodnienia z Jankiem)
1. **Jeden słownik pól dla wszystkich źródeł.** Każde źródło zapisuje do `Sprawa → Osoby → Pola`.
   Reguły i kalkulator nie wiedzą, skąd przyszła dana – czytają tylko **aktywne** wartości.
2. **Wiele wartości na pole.** Pole przechowuje listę `WartoscPola` (wartość, `wystawca`, `kanal`, dokument, strona,
   `pewnosc`, `aktywna`). Żadna wartość nie przepada; użytkownik może wrócić do innego źródła.
3. **Aktywną wartość wybiera hierarchia wiarygodności** (`zus / urzad` > `sad` > `pracodawca / lekarz` >
   odczyt AI z pewnością < 0,6 > `uzytkownik`; pola typu „plan” – tylko użytkownik). Użytkownik może ten wybór
   zmienić. **Konflikt nigdy nie blokuje wyniku.**
4. **Osoby w sprawie:** matka, ojciec / drugi rodzic, dziecko (dzieci) – każda z własnymi polami.
5. **Fakty oddzielone od scenariuszy.** Wybory i plany (podział urlopu, praca w trakcie urlopu, wniosek z 81,5%)
   są w `Scenariusz` i nie nadpisują faktów. Wynik liczony jest dla pary (fakty, scenariusz).
6. **Cztery statusy wyniku:** `przysluguje` / `warunkowo` / `brak_danych` / `nie_przysluguje`. Każdy z okresem,
   kwotą (gdy dotyczy), kto wypłaca, uzasadnieniem, powodami lub brakującymi polami.
7. **AI tylko czyta dokumenty. Decyzje i kwoty liczy deterministyczny kod z testami.**
8. **Pytania i warunki w backendzie** (`questions/katalog.json`). Flutter renderuje je dynamicznie.
   Ten sam katalog generuje schemat odczytu dla Claude.
9. **Parametry prawne i treści poza kodem** (`params/`, `content/`), edytowalne w panelu admina.
   Do wyliczeń bierzemy wersję parametrów obowiązującą w dniu powstania prawa do świadczenia.

---

## 4. Twarde zasady (zawsze)

1. **Nigdy nie commituj dokumentów ZUS** (`data/sprawy_zus/`, `*.pdf`) ani danych z nich odczytanych.
   Regulamin wyzwania zabrania ich kopiowania i rozpowszechniania.
2. **Klucz Claude API tylko w `backend/.env`.** Nigdy w kodzie, w repo ani we Flutterze. Wywołania Claude tylko z backendu.
3. **Żadnych „magicznych liczb” z przepisów w kodzie** (20, 41, 0.815, 4806, 13.71…). Tylko `p["..."]` z parametrów.
4. **Logika prawna tylko w backendzie.** Flutter niczego nie liczy, tylko wyświetla wyniki z API.
5. **LLM nie decyduje o prawie do świadczenia i nie liczy kwot.**
6. Kwoty w backendzie w `Decimal`; zaokrąglenia do groszy w miejscach, w których robi to ZUS (podstawa wymiaru,
   stawka dzienna) – nigdzie indziej. W API kwoty jako **tekst** (`"1234.56"`).
7. Każda nowa reguła prawna = test w `backend/tests/` z numerem artykułu w nazwie, np. `test_urlop_macierzynski_art180`.
8. Nazwy pól = kolumna „Pole” w `docs/pytania_kalkulator.md`. Nowe pole dopisz do `questions/katalog.json`.
9. Zmiana kształtu API = w tym samym commicie aktualizacja `docs/api.md` **i** `frontend/lib/data/models/modele.dart`.
10. **Nie nadpisuj wartości z innego źródła.** Nowa informacja = nowa `WartoscPola`; o aktywnej decyduje `merge/`.
11. **Wynik ZUS ze sprawy testowej (`oczekiwany_wynik`) nigdy nie jest danymi wejściowymi** reguł ani kalkulatora.
12. Teksty dla użytkownika **po polsku**, prostym językiem, bez żargonu prawniczego. Przepis podawaj w nawiasie
    jako dodatkową informację, np. „(art. 29 ustawy zasiłkowej)”. Teksty składa backend – Flutter je wyświetla.
13. Nie zmieniaj plików poza zakresem zadania. Małe commity, opis po polsku.
14. Nie używaj logo ZUS ani gov.pl i nie udawaj oficjalnego serwisu. Styl ma być **inspirowany**, a w stopce
    ma być informacja „Prototyp HackNation 2026 – nie jest oficjalnym serwisem ZUS”.
15. **Parametry wybieramy po dacie prawa** (`params.store.parametry_na_dzien`), nigdy „najnowsze”. Gdy nie ma pliku na rok
    tej daty, **nie zmieniamy roku po cichu**: bierzemy najbliższą wersję i dopisujemy widoczne ostrzeżenie do `uwagi`
    wyniku (robi to `api/swiadczenia.py`). Wartości, których nie umiemy zweryfikować, oznaczamy `do_weryfikacji`
    w kluczu `_zrodla` pliku parametrów (podstawa prawna, źródło, status) i dopisujemy do sekcji Z w
    `docs/pytania_kalkulator.md`.

16. **Odmowa („nie przysługuje”) nigdy nie opiera się wyłącznie na wartości odczytanej z dokumentu z pewnością ≤ 0,6**
    (`rules.wspolne.zlagodz_odmowe`). Wtedy wynik to „warunkowo”, orientacyjny, z polem do potwierdzenia. Próg „niepewny
    odczyt” (< 0,6) w UI i w hierarchii zostaje bez zmian.

---

## 5. Frontend – Flutter Web, MVVM

**Warstwy:**
| Warstwa | Odpowiada za | Nie może |
|---|---|---|
| View (`*_view.dart`) | wygląd, układ, reakcje na kliknięcia → metody ViewModelu | wołać API, liczyć, trzymać logiki |
| ViewModel (`*_viewmodel.dart`, `ChangeNotifier`) | stan ekranu (dane, `laduje`, `blad`), wywołania repozytorium | importować widżetów ani `BuildContext` |
| Repository (`data/repositories/`) | jedyne źródło danych dla ViewModeli, zamiana JSON → modele | znać UI |
| ApiClient (`data/api_client.dart`) | HTTP, nagłówki, błędy, UTF-8, upload | znać logikę biznesową |

**Ekrany** (`features/<nazwa>/`): `login`, `start`, `moje_dane`, `konflikty`, `dokumenty`, `ubezpieczenie`,
`moje_swiadczenia`, `swiadczenia`, `kalkulator`, `wnioski`, `lista_dokumentow`, `wsparcie`, `pue`, `konto`, `admin`.
Opis każdego ekranu: `docs/opis_aplikacji.md`, rozdział 11.

**Zasady:**
- Pakiety: `provider` (ChangeNotifier), `go_router`, `http`, `file_picker`, `intl`. **Nie dodawaj** freezed, get_it,
  bloc, riverpod ani generatorów kodu bez zgody.
- ViewModel tylko dla ekranów ze stanem lub danymi z API. Ekrany statyczne mogą być samym widokiem.
- ViewModel tworzymy w widoku: `ChangeNotifierProvider(create: (c) => XViewModel(c.read(), c.read()))`.
- Każdy ekran z danymi ma 3 stany: ładowanie / błąd z „Spróbuj ponownie” / treść (`shared/widgets/stan_ladowania.dart`).
- Po każdej zmianie danych (`ZmianaDanych` z API) odśwież liczniki konfliktów i braków oraz wyniki świadczeń.
- Wspólne widżety: znacznik źródła („Skąd to wiemy”), znacznik statusu świadczenia, kwota, data.
- Nowy ekran: `features/<nazwa>/` + trasa w `core/router.dart` + (jeśli w menu) wpis w `core/responsive.dart`.
- Ekrany wyłączone w panelu admina (`GET /moduly`) są ukryte w menu.
- **Nie używaj `dart:io`**, bo nie działa w przeglądarce. Pliki obsługuj jako bajty (`withData: true`).
- Adres API tylko z `--dart-define=API_URL=...` (`core/config.dart`).

---

## 6. Responsywność – telefon i komputer

Aplikacja ma wyglądać dobrze **na telefonie (od 360 px) i na komputerze (do 1920 px)**.

- Progi tylko z `core/responsive.dart`: telefon < 600 px, tablet 600–1023 px, komputer ≥ 1024 px.
  Nie wpisuj liczb szerokości w widokach.
- **Nawigacja:** telefon → dolny `NavigationBar` z 5 pozycjami (Start, Moje dane, Świadczenia, Kalkulator, Więcej);
  pozostałe ekrany w „Więcej”. Tablet/komputer → boczny `NavigationRail` (rozwinięty na komputerze) ze wszystkimi pozycjami.
- **Szerokość treści:** całość max 960 px, wyśrodkowana; formularze i kreator max 640 px.
- **Siatki kafelków:** `LayoutBuilder` → 1 kolumna (telefon), 2 (tablet), 3 (komputer).
- **Kalkulator i wyniki:** komputer → dwie kolumny (świadczenia | okresy i kwoty); telefon → jedna pod drugą.
  Porównanie scenariuszy: komputer → kolumny obok siebie; telefon → zakładki.
- **Tabele** na telefonie zamieniaj na karty (wiersz tabeli = karta).
- Elementy klikalne min. 48×48 px. Pola liczbowe: `TextInputType.numberWithOptions(decimal: true)`, akceptuj przecinek.
- **Każdy ekran sprawdź** w Chrome DevTools (tryb urządzenia, 375 px i 1440 px) przed oznaczeniem zadania jako zrobione.

---

## 7. UI i UX – styl zus.pl + gov.pl, kolory bliższe zus.pl

**Charakter:** urzędowy, spokojny, czytelny, budzący zaufanie. Dużo bieli, wyraźna hierarchia, zero ozdobników.
Z **gov.pl** bierzemy układ (kafelki usług z ikoną, tytułem i jednym zdaniem opisu, prosty język, ścieżka kroków,
dostępność). Z **zus.pl** bierzemy kolorystykę (zieleń jako kolor wiodący, granat jako uzupełniający) i układ nagłówka.

### Paleta (jedno miejsce: `frontend/lib/core/theme.dart`)
Wartości startowe **inspirowane zus.pl**. Zweryfikuj je pipetą (DevTools → Inspect na zus.pl) i poprawiaj tylko w `theme.dart`.
| Rola | Kolor | Użycie |
|---|---|---|
| Primary (zieleń ZUS) | `#00843D` | przyciski główne, aktywna pozycja menu, linki akcji |
| Primary dark | `#006B31` | hover/pressed, nagłówek na kolorowym tle |
| Primary light (tło) | `#E6F3EC` | tło wyróżnionych sekcji, aktywny kafelek |
| Secondary (granat) | `#1B365D` | nagłówki sekcji, stopka, ikony informacyjne |
| Tło strony | `#F5F7F6` | tło pod kartami |
| Powierzchnia | `#FFFFFF` | karty, formularze |
| Tekst | `#1A1A1A` / drugorzędny `#4A4A4A` | |
| `nie_przysluguje` / błąd | `#C8102E` | |
| `brak_danych` / ostrzeżenie | `#9A4F00` na tle `#FFF4E5` (kontrast 5,5:1; pierwotne `#B35C00` dawało 4,3:1) | braki, ryzyka, wartości do sprawdzenia |
| `warunkowo` / konflikt | granat `#1B365D` na tle `#E8EEF5` | wynik zależny od przyszłego zdarzenia, pole z konfliktem |
| `przysluguje` / sukces | primary `#00843D` | |
Kontrast tekstu min. **4.5:1** (WCAG AA). Status nigdy tylko kolorem: zawsze też ikona i tekst.

### Typografia i komponenty
- Krój systemowy / Roboto albo Open Sans. Body 16 px, min. 14 px.
- Hierarchia: H1 (tytuł ekranu) → H2 (sekcja) → treść. Jeden H1 na ekran.
- Przyciski: główny wypełniony zielony, drugorzędny obrysowany, zaokrąglenie 4–8 px.
- Karty: białe, ramka `#DADDDC` lub cień 1 dp, odstępy 16/24 px.
- **Nagłówek:** nazwa aplikacji po lewej, po prawej „Zaloguj (mObywatel)” / imię użytkownika.
- **Stopka (granat):** linki do zus.pl, gov.pl/rodzina, PIP, informacja o prototypie, deklaracja dostępności (szkic).

### Wzorce UX
- **Kreator krok po kroku:** jedno pytanie (albo mała grupa) na ekran, pasek postępu, „Wstecz”, edycja odpowiedzi.
  Daty → kalendarz, wybór → duże karty do kliknięcia. Pyta tylko o pola bez aktywnej wartości.
- **Wynik zawsze z uzasadnieniem:** „Przysługuje Ci…, ponieważ…”, „Przysługuje, o ile…”, „Nie przysługuje,
  ponieważ… Co możesz zrobić: …”, „Brakuje: … – znajdziesz to w dokumencie Z-3 od pracodawcy”.
- **Wynik orientacyjny:** gdy opiera się tylko na deklaracjach lub niepewnym odczycie AI – wyraźna etykieta
  i lista pól do potwierdzenia.
- **Skąd to wiemy:** przy każdej wartości źródło („Z-3, str. 7”, „ZUS”, „wpisane przez Ciebie”); niepewne odczyty AI
  na pomarańczowym tle; pole z konfliktem z ikoną i rozwijaną listą źródeł.
- **Upload:** pasek postępu z etapem („Rozpoznajemy dokumenty…”, „Odczytujemy Z-3 (2 z 4)…”), potem lista
  rozpoznanych dokumentów, odczytane dane do potwierdzenia i porównanie z decyzją ZUS.
- **Oś czasu urlopów** (matka/ojciec, kolorowe segmenty, daty, kwoty, powrót do pracy) – najważniejszy element „wow”.
- Kwoty: `1 234,56 zł` (zawsze brutto, z dopiskiem); daty: `10.07.2026`.
- **Ton:** ciepły i spokojny, szczególnie w trudnych sytuacjach (martwe urodzenie, zgon dziecka, poronienie).
  Bez wykrzykników, bez „Gratulacje!” w ścieżkach strat.
- **Dostępność:** `ensureSemantics()`, `semanticLabel` przy ikonach, logiczna kolejność fokusu, opisy pól formularzy.

---

## 8. Backend – Python FastAPI (REST)

- Python 3.11+, FastAPI, Pydantic v2, `anthropic`, `pytest`. Uruchomienie: `uvicorn app.main:app --reload` w `backend/`.
- `api/` = cienka warstwa: walidacja, wywołanie modułów, zwrot modelu Pydantic. Żadnej logiki prawnej w `api/`.
- **Źródła:** każdy adapter w `sources/` implementuje `pobierz(sprawa, osoba) → {pole: WartoscPola}` i niczego nie
  zapisuje (zapis robi `merge.dodaj`). Dane fikcyjnych użytkowników w `sources/dane/*.json`.
- **Scalanie:** wszystkie zapisy wartości przechodzą przez `merge/` (wybór aktywnej, konflikty, niespójności).
- **Reguły:** jedna funkcja na świadczenie w `rules/`, rejestr `REGULY`. Każda reguła deklaruje wymagane pola.
  Funkcja **nie rzuca wyjątków przy brakach danych**, tylko zwraca `brak_danych` z listą pól.
  Kolejność implementacji: najpierw zwykła ścieżka matki-pracownicy, potem wyjątki.
- Błędy HTTP z polskim komunikatem w `detail` (Flutter wyświetla go użytkownikowi).
- CORS: `CORS_ORIGINS` w `.env` + regex dla localhost w trybie dev.
- Dokumentacja API: `/docs` (Swagger) jest źródłem prawdy obok `docs/api.md`.
- Grupy endpointów (szczegóły w `docs/api.md`): `/auth`, `/sprawy` (osoby, dane, pytania, odpowiedzi, wybór źródła),
  `/zrodla`, `/sprawy/{id}/konflikty`, `/sprawy/{id}/dokumenty` + `/zadania/{id}` + `/sprawy/{id}/porownanie`,
  `/sprawy/{id}/ubezpieczenie|ezla|zaswiadczenie-zadluzenie`, `/swiadczenia` + `/sprawy/{id}/swiadczenia`,
  `/kalkulator` + `/sprawy/{id}/scenariusze|kalkulator`, `/info`, `/wnioski`, `/pue`, `/admin`, `/moduly`, `/health`.

---

## 9. Odczyt skanów – Claude API

- Model z `.env`: `CLAUDE_MODEL` (domyślnie `claude-sonnet-5-5`). Klucz: `ANTHROPIC_API_KEY`.
- PDF wysyłamy jako blok `document` (base64). Zestawy ZUS to **skany** (bez warstwy tekstowej, częściowo odręczne,
  częściowo zamazane, niektóre strony obrócone), a Claude widzi strony jako obrazy. Klasyfikacja zwraca kąt `obrot`;
  dokument z obróconą stroną czytamy z wyprostowanych obrazów PNG 200 DPI (`extraction/pdf.renderuj`), nie z surowego PDF.
- Odpowiedź w **wymuszonym schemacie JSON** (structured outputs: `output_config.format` = `json_schema`;
  wymuszone narzędzie `tool_choice` daje 400 na nowych modelach). `fallbacks: "default"` – przy odmowie API ponawia
  na innym modelu; logujemy, który model odpowiedział. Schematy per typ dokumentu generowane z `questions/katalog.json`
  (pola z `z_dokumentow: true` i `upload:<typ>` w `zrodla`). Każde pole ma: wartość, osobę, numer strony, pewność 0–1.
- Dwa przebiegi: **jedno** wywołanie klasyfikacji na cały PDF + **jedno** wywołanie odczytu na dokument (tylko jego
  strony, wycięte z PDF). Podział na dokumenty robi kod (`extraction/podzial.py`). Kod: `extraction/pipeline.py`.
- **Limity schematu API:** max 16 parametrów typu union (nullable/anyOf) i ograniczona złożoność gramatyki (liczba obiektów w tablicach). Dlatego schemat odczytu jest płaski: `pola[]` (wartość jako tekst, typ sprawdza kod w `mapowanie.py`) + osobne tablice tylko dla tabel (`miesiace`, `ezla`, `okresy_ubezpieczenia`). Zmieniając schemat, uruchom test `test_schematy_mieszcza_sie_w_limicie_unii_api` i sprawdź go na API.
- Tytuł ubezpieczenia czytamy z **kodu tytułu** (0110, 0411, 0510, 0570 → `schema.KODY_TYTULU`), a nie z kontekstu.
- Na razie przyjmujemy tylko PDF (inne formaty → 415). Test ręczny: `python -m scripts.odczyt_sprawy <plik.pdf>`.
- Przebieg (zadanie w tle):
  1. **klasyfikacja stron** (ZAM, ZAS-53, ZUR, ZAO, Z-3, Z-3a, Z-3b, ZAS-12, akt urodzenia, zaświadczenie lekarskie,
     wniosek o urlop, pismo ZUS, poświadczenie ubezpieczenia, zrzut systemu ZUS, decyzja / wynik sprawy…),
  2. **podział na dokumenty** – jeden PDF może zawierać kilka egzemplarzy tego samego formularza
     (stopka „Strona x z 8”, „pierwszorazowy” / „w kontynuacji”),
  3. **odczyt pól**, 4. **mapowanie na `WartoscPola`** (wystawca wg typu: Z-3 → `pracodawca`,
     zrzut systemu / poświadczenie ZUS → `zus`), 5. **merge**, 6. **reguły i kalkulator**, 7. **porównanie z decyzją ZUS**.
- **Strona z wynikiem sprawy ZUS** jest rozpoznawana **po treści**, nie po pozycji (np. w sprawie Anny jest na
  ostatniej stronie). Trafia tylko do `oczekiwany_wynik`.
- **Pismo ZUS o brakach** (np. „brakuje Z-3”) to informacja dla użytkownika, nie dane osoby.
- Endpointy: `POST /sprawy/{id}/dokumenty` → `202 {zadanie_id}` → Flutter odpytuje `GET /zadania/{id}` co 3 s.
- Wartości z pewnością < 0,6 oznaczone w UI do sprawdzenia; użytkownik może poprawić każdą wartość
  (poprawka = nowa wartość użytkownika, odczyt AI zostaje).
- Cache wyników odczytu po hashu pliku w `data/cache/` (poza repo; `CACHE_ODCZYTU=0` wyłącza).
- Nie loguj treści dokumentów ani danych osobowych. Loguj tylko zużycie tokenów i czas.
- Prompty i schematy: `backend/app/extraction/{prompts,schema}.py`. Zmieniając prompt, sprawdź wynik na min. 2 sprawach.
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
  ZAS-53 składają osoby niebędące pracownikami; u pracownika małego płatnika ZUS potrzebuje Z-3 od pracodawcy.
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
  pozostałe uzupełniane, min. przy pełnym etacie; przy niepełnym – parametr `art45_niepelny_etat`, domyślnie proporcjonalnie, do potwierdzenia); zleceniobiorca/działalność – średnia podstawa składek minus 13,71%
  (limit 20 321,30 zł; wzór art. 48a przy ubezpieczeniu < 12 mies.). Przerwa między zasiłkami < 1 miesiąca → ta sama podstawa.
- **Ryzyka (ostrzegać):** umowa lub działalność „dla pozoru”, podwyższenie podstawy w ciąży, brak ubezpieczenia
  w dniu porodu (koniec umowy, wyrejestrowanie, zawieszenie działalności), zadłużenie składkowe.
- Niejasności do wyjaśnienia z mentorami ZUS: lista na końcu `docs/pytania_kalkulator.md` i `docs/opis_aplikacji.md` (rozdz. 15).

---

## 11. Testy i sprawy ZUS

- `cd backend && pytest` przed każdym commitem zmieniającym backend.
- Testy jednostkowe: reguły (z numerem artykułu w nazwie), kalkulator (granice dat, grosze), `merge/` (hierarchia,
  konflikty, przełączanie źródła), adaptery źródeł.
- Sprawy ZUS (PDF) tylko w `data/sprawy_zus/` (lokalnie). Obok: `<nazwa>.oczekiwane.json` z wynikiem ze strony decyzji.
- Skrypt `tests/golden/run` przepuszcza sprawy przez odczyt → merge → reguły → kalkulator i drukuje **tabelę zgodności**
  (sprawa | świadczenie | wynik aplikacji | decyzja ZUS | zgodne?). Tabela to argument na prezentację.
- Frontend: ręcznie w Chrome (375 px i 1440 px) według sekcji „Jak sprawdzić” z raportu.

---

## 12. Plan prac – etapy (pionowe plastry)

Realizujemy **w podanej kolejności**. Po zakończeniu zaznacz `[x]` i dopisz datę.
Mapowanie na wymagania ZUS: `docs/opis_aplikacji.md`, rozdział 14.

### Zrobione wcześniej (stary model danych)
- [x] Symulowane logowanie przez mObywatela _(21.11.2026)_
- [x] Symulowane pobranie z ZUS danych o ubezpieczeniu → profil sprawy _(21.11.2026)_
- [x] Drzewo pytań w backendzie (`/sprawy/{id}/dane`, statusy aktywne/zablokowane/wykluczone) + zakładka „Moje dane” _(21.11.2026)_
  (przeniesione na nowy model w etapie 1)

### Etap 1 – Model danych i najczęstsza ścieżka
- [x] Migracja na nowy model: `WartoscPola` (lista wartości + aktywna), osoby w sprawie, `merge/` z hierarchią
  i konfliktami; adaptery `sources/` zamiast mocków; ścieżki API wg `docs/api.md`; `modele.dart`. _(22.11.2026)_
- [x] Reguła i kalkulator zasiłku macierzyńskiego (pracownica, 1 dziecko, 100% / 70% / 81,5%, liczba dzieci,
  „Za życiem”) z parametrów + 4 statusy wyniku + kto wypłaca. _(22.11.2026)_
  (B7 wyliczane z okresów ubezpieczenia i art. 177 KP, podstawa z Z-3 / art. 43 / tryb uproszczony,
  ekran „Świadczenia”; bez drugiego rodzica, art. 30, art. 37, art. 40 i zlecenia – kolejne etapy)
- **Gotowe, gdy:** testy przechodzą, „Moje dane” działa na nowym modelu.

### Etap 2 – Upload end-to-end (najważniejsze dla jury)
- [ ] Upload wielu plików, zadanie w tle, klasyfikacja, podział na egzemplarze, odczyt, merge, wyniki.
  (2a: pipeline odczytu gotowy _(22.11.2026)_; zostają ekrany – etap 3 – i wyniki po uploadzie w UI)
- [x] Reguła zasiłku chorobowego w ciąży (kod B, okres wyczekiwania, 33/14 dni, 270 dni, kto wypłaca). _(22.11.2026)_
  (2b: status, okres, stawka i kto wypłaca; `kwota: null` – złotówki w 2c; sprawa Anny: przysługuje od 23.03.2025, ZUS)
- [ ] Indywidualna podstawa wymiaru: pracownik (z miesięcy z Z-3), zleceniobiorca, działalność (art. 48a).
  (2c _(22.11.2026)_: pracownik z Z-3 i kwota zasiłku chorobowego gotowe, parametry 2024–2025, działalność tylko w prostym
  przypadku (12 miesięcy, próg 60%); art. 48a – bez kwoty z ostrzeżeniem; zleceniobiorca (Z-3a) – do zrobienia)
- [ ] Porównanie z decyzją ZUS + `tests/golden/run` z tabelą zgodności.
  (2d minimalne _(22.11.2026)_: `GET /sprawy/{id}/porownanie` i skrypt – tylko status; sprawa Anny: zgodne. Zostaje tabela
  zgodności ze złotymi wzorcami i porównanie kwot)
- **Gotowe, gdy:** sprawa Anny daje „przysługuje”, zgodnie z decyzją ZUS.

### Etap 3 – Ekrany ścieżki jury
- [ ] Logowanie → Start → Dokumenty (upload, odczytane dane, porównanie) → Moje świadczenia (wynik z uzasadnieniem).
  (3.1 _(22.11.2026)_: ekran Dokumenty – upload, postęp, lista dokumentów, odczytane pola, porównanie z decyzją ZUS;
  3.2 _(22.11.2026)_: Moje świadczenia (karta z uzasadnieniem, brakami, „Skąd te dane?”), Start, logowanie jednym przyciskiem,
  routing z „Wstecz”, sesja i id sprawy w sessionStorage; backend: filtr karty zasiłku chorobowego i `zrodla_danych`.
  Zostaje 3.3: dopracowanie i ręczny przegląd 375/1440 px)
- [ ] **Karta „zasiłek chorobowy – brak danych” nie może się wyświetlać każdej matce.** `GET /swiadczenia` zwraca dziś
  wynik zasiłku chorobowego w ciąży także wtedy, gdy matka nie ma zwolnień (status `brak_danych`). Ekran „Moje świadczenia”
  pokazuje kartę świadczenia tylko, gdy jest po co: są zwolnienia (`ezla`) albo użytkownik wskazał sytuację z niezdolnością
  do pracy w ciąży; w innym razie świadczenie jest w katalogu „Co jeszcze może Ci przysługiwać”, a nie jako karta z brakiem
  danych. Zdecyduj, czy filtruje backend (pole `dotyczy` w wyniku), czy widok.
- **Gotowe, gdy:** jury może wgrać PDF i zobaczyć wynik na telefonie i komputerze.
- [x] Etap 3 zrobiony _(22.11.2026)_: przejście w prawdziwej przeglądarce (Chrome, 375 i 1440 px, bez poziomego przewijania) dla
  obu spraw ZUS; zrzuty w `docs/screenshots/`. Anna: zasiłek chorobowy od 23.03.2025, 1 771,44 zł brutto (orientacyjnie),
  „zgodne z decyzją ZUS”. Działalność: „brak danych” z prośbą o wgranie zwolnienia (nie do porównania z decyzją ZUS).
  Po odczycie dokumentów ekran pyta raz o sytuację (A1 – czy ciąża), bo tego nie widać w dokumentach.

### Znane błędy i ograniczenia (stan po etapie 3)
- **Sprawa dzialalnosc_chorobowy_ciaza:** wynik „brak danych” – w PDF nie ma zwolnienia (e-ZLA), a Z-3b, zrzut systemu i dwie strony
  „inne” dają 0 odczytanych pól. Decyzja ZUS to „przyznano”, więc porównanie = „nie do porównania”. Działalność (art. 48a) bez kwoty.
- **Karty macierzyńskie przy sprawie chorobowej:** pytają o przewidywaną datę porodu (i zadłużenie przy działalności) – prawdziwe braki,
  ale mogą mylić jury; są na dole listy, pod wynikami ustalonymi.
- **Konflikt `ezla` ZAS-53 vs Z-3** (etap 5): „Moje dane” pokażą go jako konflikt, choć okresy się nie wykluczają.
- **Niepełne `Odczytane dane`:** pokazujemy tylko aktywne wartości (bez duplikatów z kolejnych Z-3); pozostałe są w „Moje dane”.
- **Logowanie po wgraniu dokumentów:** zalogowanie zakłada nową sprawę, więc dokumenty wgrane anonimowo znikają.
- **Przeglądarki mobilne:** wybór pliku i wynik sprawdzone w emulacji Chrome (viewport + dotyk); nie testowano na prawdziwym iOS
  Safari i Android Chrome – do sprawdzenia ręcznie przed prezentacją.
- **Ikony „Material” w buildzie release:** `flutter build web --release` bez wcześniejszego `rm -rf build/web` potrafi zostawić
  pusty katalog `assets/fonts` i brak `favicon.png` (ikony jako kwadraty). Zawsze buduj na czysto.
- Teksty ostrzeżeń z backendu (np. art. 45) są długie i szczegółowe – do skrócenia dla użytkownika.

### Etap 4 – Kalkulator zintegrowany
- [ ] Oboje rodzice, scenariusze i ich porównanie, oś czasu z powrotem do pracy, łączenie pracy z urlopem
  rodzicielskim, przejęcie urlopu przez ojca, urlop ojcowski; kalkulator bez logowania (`POST /kalkulator`).
- **Gotowe, gdy:** na ekranie widać porównanie dwóch wariantów.

### Etap 5 – Moje dane, konflikty, kreator
- [ ] Przełączanie źródła pola, zakładka konfliktów z niespójnościami, kreator krok po kroku (tylko braki),
  wynik orientacyjny z polami do potwierdzenia.
- **Gotowe, gdy:** zmiana źródła pola przelicza wyniki świadczeń.
- **Znana niedoskonałość UI (do etapu 5):** pole `ezla` ze ZAS-53 (użytkownik, cały okres) i ze scalonych Z-3 (pracodawca,
  tylko część okresu) to dwie różne wartości, więc „Moje dane” pokażą konflikt, choć nic sobie nie przeczy. Konflikt nie
  blokuje wyniku (reguła bierze początek niezdolności także z okresu wynagrodzenia chorobowego z Z-3). Rozwiązanie:
  w etapie 5 traktować okresy jako sumę wszystkich źródeł albo nie zgłaszać konfliktu, gdy jeden okres zawiera drugi.

### Etap 6 – Pozostałe świadczenia i sytuacje
- [ ] Świadczenie rehabilitacyjne, zasiłek w wysokości zasiłku macierzyńskiego, działalność + zadłużenie,
  urlop uzupełniający, martwe urodzenie / zgon dziecka, adopcja, rodzina zastępcza niezawodowa, status `warunkowo`.
- **Gotowe, gdy:** testy + tabela zgodności na wszystkich dostępnych sprawach ZUS.

### Etap 7 – Informacje
- [ ] Poradnik krok po kroku dopasowany do sytuacji (kto wypłaca, status), ryzyka (z „dotyczy Ciebie”), ochrona
  z Kodeksu pracy, organizacje charytatywne (każdą zweryfikować ręcznie), lista dokumentów, linki zus.pl / gov.pl / PIP.
- **Gotowe, gdy:** każde świadczenie ma poradnik.

### Etap 8 – Symulacje i panel admina
- [ ] e-ZLA, zaświadczenie o zadłużeniu, PUE (konto + „zadaj pytanie”), wnioski o urlopy (do zaprojektowania wg
  rozporządzenia z 2025 r.), ZAM, odpis aktu urodzenia, symulowana wysyłka.
- [ ] Panel admina: parametry z datą obowiązywania, moduły, treści.
- **Gotowe, gdy:** każdy ekran działa na danych testowych.

### Etap 9 – Oddanie
- [ ] Wdrożenie demo (link działa z telefonu), README (uruchomienie, wdrożenie, użycie AI).
- [ ] Tytuł i szczegółowy opis projektu, prezentacja (max 10 slajdów), film (max 3 min, otwarte repozytorium),
  zrzuty ekranu (telefon + komputer), materiały graficzne, lista funkcji wspieranych przez AI.
- [ ] Repozytorium publiczne, bez PDF-ów ZUS i kluczy.

### Wymagania niefunkcjonalne (przez cały czas)
- Aplikacja webowa, w pełni responsywna (sekcja 6) · REST API · dostępność WCAG AA ·
  potencjał wdrożeniowy: czysta struktura, parametry i treści poza kodem, testy, dokumentacja.

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
flutter pub get
flutter run -d chrome --dart-define=API_URL=http://localhost:8000
rm -rf build/web && flutter build web --release   # adres API względny; osobny host: --dart-define=API_URL=https://rodziceplus-production.up.railway.app
cp -r build/web ../backend/static                     # backend serwuje frontend z backend/static (katalog w .gitignore)
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
| Sprawa | jedna sytuacja życiowa (np. ciąża i urodzenie) z osobami, dokumentami, scenariuszami i wynikami |
| WartoscPola | jedna wartość pola z jednego źródła (wystawca, kanał, pewność, aktywna) |
| Wystawca / kanał | kto ręczy za informację (np. pracodawca) / którędy dotarła (np. upload) |
| Aktywna wartość | wartość pola używana do wyliczeń; domyślnie wg hierarchii, użytkownik może zmienić |
| Konflikt | to samo pole tej samej osoby ma różne wartości z różnych źródeł |
| Niespójność | sprzeczność między różnymi polami (np. zwolnienie przed datą zatrudnienia) |
| Scenariusz | zestaw wyborów i planów (podział urlopu, praca w trakcie urlopu) liczony na tych samych faktach |
| Wynik orientacyjny | wynik oparty tylko na deklaracjach użytkownika lub niepewnym odczycie AI |
| `oczekiwany_wynik` | decyzja ZUS ze sprawy testowej – tylko do porównania, nigdy dane wejściowe |
