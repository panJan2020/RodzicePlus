# Architektura i wyzwania

> Opis funkcji i ekranów: `docs/opis_aplikacji.md`. Ten plik opisuje, **jak** to jest zbudowane.
> Zasady pracy z agentami AI: `CLAUDE.md`.

## 1. Przegląd

```
Przeglądarka (telefon / komputer)
   │  Flutter Web – MVVM
   │  View ──► ViewModel ──► Repository ──► ApiClient
   ▼                                           │ REST / JSON
Backend – Python FastAPI                       ▼
   api/            cienka warstwa HTTP
     │
     ├─► sources/      adaptery źródeł danych (symulacje: mObywatel, RSC, ZUS, e-ZLA, PUE)
     ├─► extraction/   upload: klasyfikacja stron, podział na dokumenty, odczyt pól (Claude API)
     │        │
     │        ▼
     ├─► merge/        scalanie wartości w profil, wybór aktywnej wartości, konflikty, spójność
     │        │
     │        ▼
     ├─► domain/       Sprawa → Osoby → Pola (+ dokumenty, scenariusze, wyniki)
     │        │
     │        ▼
     ├─► questions/    katalog pytań = słownik pól + warunki „co zapytać dalej”
     ├─► rules/        prawo do świadczeń → 4 statusy + uzasadnienie
     ├─► calculator/   okresy, podstawa wymiaru, kwoty, oś czasu, scenariusze
     ├─► params/       liczby z przepisów (JSON, wersjonowane datą)
     ├─► content/      poradniki krok po kroku, ryzyka, organizacje, linki, lista dokumentów
     ├─► forms/        wnioski o urlopy, ZAM, odpis aktu (wypełnianie + symulowana wysyłka)
     └─► storage/      magazyn spraw (w pamięci; podmienialny na bazę)
```

**Przepływ danych:** źródło (adapter albo upload) → wartości pól z metadanymi → `merge/` wybiera aktywne wartości
i wykrywa konflikty → `rules/` + `calculator/` liczą wyniki **na aktywnych wartościach faktów + wybranym scenariuszu**
→ API → Flutter wyświetla.

---

## 2. Struktura repozytorium (monorepo)

```
rodzice/
├── README.md                    uruchomienie, wdrożenie, użycie AI
├── CLAUDE.md                    zasady dla agentów AI (czytać przed każdą zmianą!)
├── .gitignore                   m.in. data/sprawy_zus, *.pdf, .env
├── docs/
│   ├── opis_aplikacji.md        CO budujemy: funkcje, ekrany, pokrycie wymagań
│   ├── architektura.md          JAK budujemy: ten plik
│   ├── api.md                   kontrakt REST – umowa front ↔ back
│   └── pytania_kalkulator.md    pytania, pola, przepisy, parametry
├── data/sprawy_zus/             lokalnie PDF-y od ZUS (NIE w gicie)
├── backend/                     Python + FastAPI
│   ├── requirements.txt, .env.example
│   ├── app/
│   │   ├── main.py              aplikacja, CORS, rejestracja routerów
│   │   ├── config.py            zmienne środowiskowe
│   │   ├── api/                 warstwa HTTP (tylko walidacja i wywołania)
│   │   │   ├── auth.py          logowanie mObywatel (symulacja)
│   │   │   ├── sprawy.py        sprawa, osoby, pola, wybór źródła, kreator (następne pytania)
│   │   │   ├── konflikty.py     lista konfliktów i niespójności, rozstrzygnięcie
│   │   │   ├── dokumenty.py     upload, zadania w tle, odczytane dane, porównanie z decyzją ZUS
│   │   │   ├── ubezpieczenie.py tytuły ubezpieczenia, e-ZLA, zaświadczenie o zadłużeniu
│   │   │   ├── swiadczenia.py   wyniki świadczeń dla sprawy, katalog wszystkich świadczeń
│   │   │   ├── kalkulator.py    kalkulator zintegrowany, scenariusze, oś czasu
│   │   │   ├── wnioski.py       wnioski o urlopy, ZAM, odpis aktu, symulowana wysyłka
│   │   │   ├── info.py          poradniki, ryzyka, wsparcie, lista dokumentów, linki
│   │   │   ├── pue.py           podgląd konta, „zadaj pytanie” (symulacja)
│   │   │   └── admin.py         parametry, moduły, treści
│   │   ├── domain/              modele: Sprawa, Osoba, WartoscPola, Konflikt, Dokument, Scenariusz, Wynik
│   │   ├── sources/             adaptery źródeł (wspólny interfejs) + dane fikcyjnych użytkowników
│   │   ├── extraction/          prompt, schematy per typ dokumentu, wywołanie Claude, mapowanie na pola
│   │   ├── merge/               hierarchia wiarygodności, wybór aktywnej wartości, konflikty, reguły spójności
│   │   ├── questions/           katalog.json (pola + pytania + warunki) + silnik „następne pytania”
│   │   ├── rules/               jedna funkcja na świadczenie, rejestr REGULY
│   │   ├── calculator/          wymiary urlopów, podstawa wymiaru, kwoty, oś czasu
│   │   ├── params/              params_RRRR.json z polem obowiazuje_od + store.py
│   │   ├── content/             treści w JSON/Markdown (edytowalne w panelu admina)
│   │   ├── forms/               szablony wniosków + generowanie PDF
│   │   └── storage/             magazyn w pamięci (interfejs gotowy do podmiany na bazę)
│   └── tests/                   testy reguł i kalkulatora + test przepływu API; golden/ = sprawy ZUS (lokalnie)
└── frontend/                    Flutter Web
    ├── pubspec.yaml
    └── lib/
        ├── main.dart, app.dart  providery, MaterialApp.router, język polski
        ├── core/                config (API_URL), router (go_router), theme, responsive, session
        ├── data/                api_client, models/modele.dart, repositories/
        ├── shared/widgets/      ładowanie/błąd, kwoty i daty, znacznik źródła, znacznik statusu
        └── features/<ekran>/    <ekran>_view.dart + <ekran>_viewmodel.dart
            login, start, moje_dane, konflikty, dokumenty, ubezpieczenie,
            moje_swiadczenia, swiadczenia, kalkulator, wnioski, lista_dokumentow,
            wsparcie, pue, konto, admin
```

---

## 3. Model danych

```
Sprawa
├── zdarzenie: urodzenie | przysposobienie | rodzina_zastepcza
├── osoby[]
│   ├── rola: matka | ojciec | drugi_rodzic | dziecko
│   ├── zalogowana: bool
│   └── pola: { nazwa_pola → [WartoscPola, ...] }      ← kilka wartości z różnych źródeł
├── dokumenty[]        typ, wariant (pierwszorazowy / w kontynuacji), strony, osoba
├── konflikty[]        pole, osoba, wartości, aktywna, rozstrzygnięte_przez (system | użytkownik)
├── niespojnosci[]     reguła, pola, komunikat
├── scenariusze[]      nazwa + wybory (podział urlopu, praca w trakcie urlopu, 81,5%, start urlopu…)
├── oczekiwany_wynik   (tylko sprawy ZUS – do porównania, nigdy jako dane wejściowe)
└── wyniki[]           świadczenie, osoba, scenariusz, status, okres, kwota, kto_wypłaca, uzasadnienie, brakujące_pola
```

**WartoscPola**

| Atrybut | Opis |
|---|---|
| `wartosc` | wartość w typie pola (data, liczba `Decimal`, enum, tekst) |
| `wystawca` | `zus`, `urzad`, `pracodawca`, `lekarz`, `sad`, `uzytkownik`, `wyliczone` |
| `kanal` | `mobywatel`, `rsc`, `zus_konto`, `zus_platnik`, `zus_historia`, `ezla`, `pue`, `upload`, `kreator`, `system` |
| `dokument_id`, `strona` | dla uploadu |
| `pewnosc` | 0–1 (odczyt AI); dla pozostałych 1 |
| `aktywna` | czy ta wartość idzie do wyliczeń |
| `utworzono` | znacznik czasu |

**Fakty vs scenariusze.** Pola osób opisują fakty. Wybory i plany (podział urlopu, łączenie z pracą, wniosek do 21 dni
po porodzie) są w `Scenariusz` i nie nadpisują faktów. Wyniki liczone są dla pary (fakty, scenariusz), więc da się
porównać warianty obok siebie.

**Katalog pytań** (`questions/katalog.json`) jest jedynym słownikiem pól. Każde pole ma: nazwę, typ, osobę (rolę),
pytanie dla kreatora, warunek wyświetlenia, informację, w jakim dokumencie je znaleźć, oraz flagę `z_dokumentow`
(z niej generowany jest schemat odczytu dla Claude). Każda reguła świadczenia deklaruje listę wymaganych pól.

Pytanie ma status zależny od innych odpowiedzi: `aktywne` (pokazujemy), `zablokowane` (wyszarzone, czeka na
odpowiedź na pytanie nadrzędne) albo `wykluczone` (ukryte; wartość zostaje w profilu, ale reguły jej nie używają).

---

## 4. Źródła danych

Wszystkie źródła implementują ten sam interfejs `Zrodlo.pobierz(sprawa, osoba) → list[WartoscPola]`.

| Adapter | Wystawca | Kanał | Dane |
|---|---|---|---|
| `mobywatel` | urząd | mObywatel | PESEL, imię, nazwisko, data urodzenia, płeć, adres |
| `rsc` | urząd | RSC | dziecko: data urodzenia, liczba dzieci, rodzice, martwe urodzenie / zgon |
| `zus_konto` | ZUS | konto ubezpieczonego | tytuły ubezpieczenia od–do, chorobowe obowiązkowe/dobrowolne, podstawy składek z RCA |
| `zus_platnik` | ZUS | dane płatnika | NIP, liczba ubezpieczonych chorobowo (do / powyżej 20), zadłużenie składkowe |
| `zus_historia` | ZUS | historia świadczeń | wcześniejsze zasiłki, podstawy, wykorzystane dni okresu zasiłkowego |
| `ezla` | lekarz | e-ZLA | okresy niezdolności, kod B, data wystawienia |
| `pue` | ZUS | PUE/eZUS | złożone wnioski, status spraw, pisma i decyzje |
| `upload` | zależnie od dokumentu | upload | patrz rozdział 5 |
| `kreator` | użytkownik | kreator | braki + plany i zamiary |
| `wyliczone` | system | system | wiek, okres wyczekiwania, przerwy między zasiłkami, kto wypłaca |

Wszystkie adaptery poza `upload` i `kreator` są **symulacjami** na danych fikcyjnych użytkowników
(`sources/dane/*.json`). W produkcji podmienia się implementację adaptera, reszta aplikacji się nie zmienia.

---

## 5. Upload – przebieg

```
POST /sprawy/{id}/dokumenty (PDF, wiele plików)
  → zadanie_id (zadanie w tle; Flutter odpytuje GET /zadania/{id} co 3 s)
     1. klasyfikacja stron         typ dokumentu dla każdej strony
     2. podział na dokumenty       egzemplarze formularzy (stopka „Strona x z 8”, pierwszorazowy / w kontynuacji)
     3. odczyt pól                 schemat per typ dokumentu, wartość + strona + pewność
     4. mapowanie na WartoscPola   wystawca wg typu dokumentu (Z-3 → pracodawca, zrzut systemu ZUS → zus)
     5. merge                      aktywne wartości, konflikty, niespójności
     6. rules + calculator         wyniki
     7. porównanie                 wynik aplikacji vs oczekiwany_wynik (sprawy ZUS)
```

- **Strona z decyzją ZUS** jest rozpoznawana **po treści** (np. „W sprawie przyznano zasiłek chorobowy”), nie po
  pozycji w pliku. W sprawie Anny jest na ostatniej stronie. Trafia tylko do `oczekiwany_wynik`.
- **Strony wewnętrzne ZUS** (poświadczenie ubezpieczenia, zrzuty systemu) dostają `wystawca = zus`. W trybie demo
  zastępują odpowiedź z systemów ZUS.
- **Pismo ZUS o brakach** (np. „brakuje Z-3”) jest odczytywane jako informacja, nie jako dane osoby.
- Formularze ZUR, ZAO i Z-3b zlikwidowano od 24.10.2026, ale występują w sprawach testowych, więc trzeba je rozpoznawać.

---

## 6. Scalanie, konflikty, spójność (`merge/`)

1. **Hierarchia wiarygodności** (domyślny wybór aktywnej wartości):
   `zus / urzad` > `sad` > `pracodawca / lekarz` > odczyt AI z `pewnosc < 0,6` > `uzytkownik`.
   Wyjątek: pola typu „plan / zamiar” – tylko `uzytkownik`; pola „wybór” nie trafiają do osób (scenariusz).
   - Odczyt AI z `pewnosc ≥ 0,6` ma rangę swojego wystawcy (np. Z-3 → `pracodawca`). Odczyt poniżej progu
     spada na poziom „niepewny odczyt AI”, ale nigdy nie awansuje ponad swojego wystawcę. Próg: parametr `prog_pewnosci_ai`.
   - **Remis** (ta sama ranga): wyższa `pewnosc`, potem nowsza wartość (`utworzono`).
   - **Wyjątek przy wystawcy `uzytkownik`:** wartość z dokumentu (`kanal: upload`, np. ZAM) wygrywa z kreatorem,
     bo to ona trafiła do ZUS.
   - To samo źródło (ten sam kanał i dokument) podające nową wartość aktualizuje **swoją** wartość, nie dodaje kolejnej.
   - Kod: `backend/app/merge/hierarchia.py` (kolejność), `merge/scalanie.py` (zapis, wybór aktywnej, konflikty).
2. **Konflikt** = to samo pole tej samej osoby ma różne wartości. System od razu wybiera aktywną według hierarchii,
   więc wynik nie jest blokowany. Użytkownik może zmienić wybór w „Konfliktach” albo w „Moich danych”.
   Niewybrane wartości zostają zapisane.
3. **Niespójności** = reguły między polami (np. zwolnienie przed datą zatrudnienia). Nie blokują wyniku,
   ale są pokazywane jako ostrzeżenia.
4. **Wynik orientacyjny**: jeśli reguła użyła pól tylko z `uzytkownik` albo z niepewnego odczytu AI,
   wynik dostaje flagę `orientacyjny` i listę pól do potwierdzenia.

---

## 7. Reguły i kalkulator

**Statusy wyniku:**

| Status | Kiedy |
|---|---|
| `przysluguje` | wszystkie warunki spełnione |
| `warunkowo` | spełnione, ale zależne od przyszłego zdarzenia (np. ubezpieczenie w dniu porodu) – z odniesieniem do ryzyka |
| `brak_danych` | brakuje wymaganych pól – lista pól + gdzie je znaleźć |
| `nie_przysluguje` | warunek niespełniony – powód (które pola), przepis, co można zrobić |

**Zasady:**
- Jedna reguła = jedna funkcja w `rules/`, rejestr `REGULY`. Funkcja **nie rzuca wyjątków** przy brakach.
- Kolejność implementacji: najpierw zwykła ścieżka matki-pracownicy, potem wyjątki.
- Kalkulator liczy dla każdej osoby osobno (własna podstawa), oś czasu łączy okresy obojga rodziców.
- Kwoty w `Decimal`, zaokrąglenie do groszy na końcu.
- **Żadnych liczb z przepisów w kodzie** – tylko parametry z `params/`, wersja obowiązująca w dniu powstania prawa.

---

## 8. API (skrót – szczegóły w `docs/api.md`)

| Obszar | Endpointy |
|---|---|
| Logowanie | `GET /auth/mobywatel/konta`, `POST /auth/mobywatel`, `GET /auth/ja` |
| Sprawa i osoby | `GET/POST /sprawy`, `GET /sprawy/{id}`, `POST/DELETE /sprawy/{id}/osoby` |
| Dane i kreator | `GET /sprawy/{id}/dane`, `GET /sprawy/{id}/pytania`, `POST /sprawy/{id}/odpowiedzi`, `PUT /sprawy/{id}/osoby/{osoba}/pola/{pole}/aktywna` (wybór źródła) |
| Źródła | `GET /zrodla`, `POST /sprawy/{id}/zrodla/{kod}/pobierz` |
| Konflikty | `GET /sprawy/{id}/konflikty` |
| Dokumenty | `POST /sprawy/{id}/dokumenty`, `GET /zadania/{id}`, `GET/DELETE /sprawy/{id}/dokumenty`, `GET /sprawy/{id}/porownanie` |
| Ubezpieczenie | `GET /sprawy/{id}/ubezpieczenie`, `GET …/ezla`, `POST …/zaswiadczenie-zadluzenie` |
| Świadczenia | `GET /swiadczenia`, `GET /swiadczenia/{kod}`, `GET /sprawy/{id}/swiadczenia?scenariusz=` |
| Kalkulator | `POST /kalkulator` (bez logowania), `/sprawy/{id}/scenariusze` (CRUD), `GET /sprawy/{id}/kalkulator`, `GET …/kalkulator/porownanie` |
| Informacje | `GET /info/poradnik/{swiadczenie}`, `/info/ryzyka`, `/info/ochrona`, `/info/wsparcie`, `/info/dokumenty`, `/info/linki` |
| Wnioski | `GET /wnioski/typy`, `POST/GET /sprawy/{id}/wnioski`, `PUT /wnioski/{id}`, `GET /wnioski/{id}/pdf`, `POST /wnioski/{id}/wyslij` |
| PUE | `GET /pue/konto`, `GET/POST /pue/pytania` |
| Admin | `/admin/parametry`, `/admin/moduly`, `/admin/tresci`; publicznie `GET /moduly` |
| Inne | `GET /health` |

---

## 9. Kluczowe decyzje

1. **Jeden słownik pól dla wszystkich źródeł.** Każde źródło zapisuje do `Sprawa → Osoby → Pola`, wartość zawsze
   z wystawcą, kanałem i pewnością. Reguły nie wiedzą, skąd przyszła dana.
2. **Wiele wartości na pole + aktywna wartość.** Konflikty się nie gubią, użytkownik może wrócić do innego źródła.
3. **Domyślny wybór według hierarchii wiarygodności.** Konflikt nigdy nie blokuje wyniku.
4. **Fakty oddzielone od scenariuszy.** Kalkulatory c i d z treści zadania to porównanie scenariuszy na tych samych faktach.
5. **AI tylko czyta, kod decyduje.** Claude zwraca dane przez wymuszone narzędzie (JSON wg schematu). Prawo do
   świadczeń i kwoty liczy deterministyczny kod z testami.
6. **Parametry prawne poza kodem, wersjonowane datą.** Edycja w panelu admina.
7. **Treści poza kodem** (`content/`). Poradniki, ryzyka, organizacje i linki można poprawiać bez programisty.
8. **Pytania i warunki w backendzie.** Flutter renderuje pytania dynamicznie według typu pola.
9. **Odczyt skanów jako zadanie w tle.** Długie żądanie HTTP mogłoby zostać zerwane.

---

## 10. Wyzwania i jak je obejść

### Odczyt skanów (Claude API)
| Wyzwanie | Rozwiązanie |
|---|---|
| Skany bez warstwy tekstowej, pismo odręczne, zamazane dane | PDF jako blok `document` (Claude widzi strony jako obrazy); `pewnosc`; wartości < 0,6 oznaczone w UI |
| Jeden PDF = wiele dokumentów, w tym kilka egzemplarzy tego samego formularza | Najpierw klasyfikacja stron, potem podział na egzemplarze, dopiero potem odczyt pól |
| Wynik sprawy w różnych miejscach pliku | Rozpoznawanie strony wyniku po treści; `oczekiwany_wynik` nigdy jako dane wejściowe |
| Strony obrócone (np. zrzut systemu ZUS) | Prompt: „strona może być obrócona”; w razie problemów obracanie przed wysłaniem |
| Czas odpowiedzi 30–90 s | Zadanie w tle + polling + komunikat „to może potrwać do 2 minut” |
| Koszt i limity API | Jeden przebieg na plik; zapisywanie zużycia tokenów; cache wyników po hashu pliku |
| Halucynacje | „Tylko to, co widać”, schemat z `enum`, weryfikacja przez użytkownika, porównanie z decyzją ZUS |
| Bardzo duże PDF-y | Limit uploadu 30 MB; dzielenie na części, jeśli plik przekroczy limity API |
| Prywatność (RODO) | Klucz i wywołania tylko w backendzie; brak logowania treści dokumentów; dane w pamięci; w produkcji: umowa powierzenia, retencja |

### Logika prawna
| Wyzwanie | Rozwiązanie |
|---|---|
| Dużo wyjątków (ojciec, wcześniak, adopcja, martwe urodzenie, łączenie z pracą) | Jedna reguła = jedna funkcja; najpierw zwykła ścieżka, potem wyjątki |
| Wynik zależny od przyszłych zdarzeń | Status `warunkowo` + powiązane ryzyko |
| Grosze w kwotach | `Decimal` + zaokrąglanie na końcu; porównanie ze sprawami ZUS co do grosza |
| Daty i tygodnie | Tydzień urlopu = 7 dni kalendarzowych; testy na granicach (rok przestępny, koniec roku 6. urodzin) |
| Dwoje rodziców z różnymi podstawami | Osobne osoby, osobne podstawy, wspólna oś czasu |
| Niejasności w materiałach | Lista pytań do mentorów w `docs/pytania_kalkulator.md`; decyzje zapisywać w README |

### Flutter Web na telefonie i komputerze
| Wyzwanie | Rozwiązanie |
|---|---|
| Różne szerokości ekranu | `core/responsive.dart`: dolny pasek na telefonie, boczny panel na komputerze; `maxWidth` treści 1200 px, formularzy 640 px; `LayoutBuilder` dla siatek |
| 15 ekranów a mało miejsca w nawigacji | Na telefonie 5 głównych pozycji (Start, Moje dane, Świadczenia, Kalkulator, Więcej); reszta w „Więcej” |
| Upload plików w przeglądarce | `file_picker` z `withData: true`, multipart; bez `dart:io` |
| CORS | `CORSMiddleware` z regexem dla localhost i listą domen produkcyjnych w `.env` |
| Długie pierwsze ładowanie | `flutter build web --release`; ekran ładowania w `web/index.html`; bez zbędnych pakietów |
| Dostępność (WCAG AA) | `ensureSemantics()`, `semanticLabel`, kontrast, pola dotyku min. 48 px, status nie tylko kolorem |
| Klawiatura numeryczna | `TextInputType.numberWithOptions(decimal: true)`, akceptowanie przecinka |
| Przycisk „wstecz” i linki | `go_router` (prawdziwe adresy URL) |
| Polskie znaki, daty i kwoty | `utf8.decode(bodyBytes)`; `flutter_localizations` + `intl` (`pl`) |

### Praca i wdrożenie
| Wyzwanie | Rozwiązanie |
|---|---|
| Jedna osoba + agenci AI | `CLAUDE.md` z zasadami; praca etapami (pionowe plastry), plan przed kodem, commit po każdym etapie |
| Rozjazd modeli Dart ↔ Python | Zmiana API = zmiana `api.md` + `modele.dart` w tym samym commicie |
| Darmowy hosting usypia backend | Przed prezentacją wywołać `/health`; komunikat „łączenie z serwerem…” z ponowieniem |
| Dokumenty ZUS nie mogą trafić do repo | `.gitignore` na `data/sprawy_zus/` i `*.pdf`; testy na sprawach tylko lokalnie |
| Dane w pamięci znikają po restarcie | Akceptowalne na demo; produkcyjnie PostgreSQL (interfejs `storage/` gotowy) |

---

## 11. Kolejność prac (pionowe plastry)

| Etap | Zakres | Gotowe, gdy |
|---|---|---|
| 1 | `domain/` + `merge/` (podstawowe) + reguła i kalkulator zasiłku macierzyńskiego (pracownica, 1 dziecko, 100/70/81,5%) | testy przechodzą |
| 2 | Upload end-to-end + reguła zasiłku chorobowego w ciąży | sprawa Anny daje „przysługuje”, zgodnie z decyzją ZUS |
| 3 | Frontend: logowanie → Start → Moje świadczenia → Dokumenty (upload) | jury może wgrać PDF i zobaczyć wynik, na telefonie i komputerze |
| 4 | Kalkulator: oboje rodzice, scenariusze, oś czasu, łączenie z pracą | porównanie dwóch wariantów na ekranie |
| 5 | Moje dane + Konflikty + niespójności | zmiana źródła pola przelicza wyniki |
| 6 | Pozostałe reguły: działalność, zadłużenie, ojciec, adopcja, rodzina zastępcza, sytuacje szczególne | testy + tabela zgodności ze sprawami ZUS |
| 7 | Poradniki, ryzyka, wsparcie, lista dokumentów, linki | treści dla każdego świadczenia |
| 8 | Symulacje: e-ZLA, zadłużenie, PUE, wnioski, odpis aktu + panel admina | każdy ekran działa na danych testowych |
| 9 | Wdrożenie, zrzuty ekranu, film, prezentacja | link do demo działa z telefonu |
