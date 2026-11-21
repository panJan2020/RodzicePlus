# Architektura i wyzwania

## Struktura repozytorium (monorepo)

```
rodzice/
├── README.md                 uruchomienie, wdrożenie, użycie AI
├── CLAUDE.md                 zasady dla agentów AI (czytać przed każdą zmianą!)
├── .gitignore                m.in. data/sprawy_zus, *.pdf, .env
├── docs/
│   ├── architektura.md       ten plik
│   ├── api.md                kontrakt REST – umowa front ↔ back
│   ├── wymagania.md          FR-01..FR-31
│   └── pytania_kalkulator.md pytania, pola, przepisy, parametry
├── data/sprawy_zus/          lokalnie PDF-y od ZUS (NIE w gicie)
├── backend/                  Python + FastAPI
│   ├── requirements.txt, .env.example
│   ├── app/
│   │   ├── main.py           aplikacja, CORS, rejestracja routerów
│   │   ├── config.py         zmienne środowiskowe
│   │   ├── api/              warstwa HTTP (cienka – tylko walidacja i wywołania)
│   │   │   ├── auth.py       mObywatel (symulacja)            FR-01
│   │   │   ├── zus.py        ubezpieczenie, e-ZLA, zadłużenie  FR-02, 04–06
│   │   │   ├── sprawy.py     sprawa, odpowiedzi, pytania, upload + zadania w tle  FR-03, 28
│   │   │   ├── kalkulator.py uprawnienia + kalkulator          FR-07..18, 20
│   │   │   ├── info.py       dokumenty, ryzyka, wsparcie, linki FR-19..24, 27
│   │   │   └── admin.py      parametry prawne                  FR-30
│   │   ├── domain/           modele: Sprawa → Osoba → pola (FieldValue ze źródłem), wyniki
│   │   ├── questions/        katalog.json (pytania + warunki) + silnik „następne pytania”
│   │   ├── rules/            prawo do świadczeń: TAK / NIE / BRAK_DANYCH + uzasadnienie
│   │   ├── calculator/       wymiary urlopów, podstawa wymiaru, kwoty, oś czasu
│   │   ├── params/           params_RRRR.json wersjonowane datą + store.py
│   │   ├── extraction/       Claude API: prompt, schemat narzędzia, wywołanie, scalanie
│   │   ├── storage/          magazyn w pamięci (podmienialny na bazę)
│   │   └── mocks/            fikcyjni użytkownicy „ZUS”
│   └── tests/                testy reguł + test przepływu API; golden/ = sprawy ZUS (lokalnie)
└── frontend/                 Flutter Web
    ├── pubspec.yaml
    └── lib/
        ├── main.dart, app.dart        providery, MaterialApp.router, język polski
        ├── core/                      config (API_URL), router (go_router), theme,
        │                              responsive (progi + AppShell), session
        ├── data/                      api_client, models, repositories
        ├── shared/widgets/            wspólne widżety (ładowanie/błąd, formatowanie kwot)
        └── features/<ekran>/          <ekran>_view.dart + <ekran>_viewmodel.dart
            login, start, kreator, dokumenty, kalkulator, wnioski, informacje, admin
```

## Kluczowe decyzje

1. **Jeden słownik pól dla wszystkich źródeł danych.** Kreator, mock ZUS i odczyt skanów zapisują do tego samego
   profilu `Sprawa → Osoba → pola`, a każda wartość ma źródło (`uzytkownik | zus | dokument`), dokument, stronę i pewność.
   Dzięki temu kreator pyta tylko o braki, UI pokazuje „skąd to wiemy”, a sprzeczności między dokumentami są wykrywane.
2. **Pytania i warunki w backendzie (`katalog.json`).** Flutter renderuje pytania dynamicznie według `typ`.
   Logika nie jest dublowana w Dart, a ten sam katalog generuje schemat odczytu dla Claude.
3. **AI tylko czyta, kod decyduje.** Claude zwraca dane przez wymuszone narzędzie (JSON wg schematu). Uprawnienia
   i kwoty liczą deterministyczne reguły z testami. To ważne dla oceny „poprawności wyliczeń” i dla zaufania.
4. **Parametry prawne poza kodem, wersjonowane datą.** Do wyliczeń bierzemy wersję obowiązującą w dniu powstania prawa.
   To spełnia wymaganie panelu admina i jest dobrym argumentem za „potencjałem wdrożeniowym”.
5. **Wynik ma 3 stany:** przysługuje / nie przysługuje / brak danych (z listą brakujących pól).
6. **Odczyt skanów jako zadanie w tle.** Upload zwraca `zadanie_id`, Flutter odpytuje co 3 s. Długie żądanie HTTP
   mogłoby zostać zerwane przez hosting albo przeglądarkę.

## Wyzwania i jak je obejść

### Odczyt skanów (Claude API)
| Wyzwanie | Rozwiązanie |
|---|---|
| Skany bez warstwy tekstowej, pismo odręczne, zamazane dane | PDF jako blok `document` (Claude widzi strony jako obrazy); pole `pewnosc`; wartości poniżej 0,6 oznaczone w UI do sprawdzenia |
| Jeden PDF = wiele dokumentów (np. 20 stron w sprawie Agaty) | Claude najpierw klasyfikuje każdą stronę (`strony[]`), potem wyciąga pola z numerem strony |
| 1. strona zestawu zawiera wynik sprawy | Osobne pole `oczekiwany_wynik` – nigdy jako dane wejściowe, tylko do testów |
| Czas odpowiedzi 30–90 s | Zadanie w tle + polling + komunikat „to może potrwać do 2 minut” |
| Koszt i limity API | Jeden request na plik; zapisywanie zużycia tokenów w zadaniu; podczas developmentu cache wyników (TODO) |
| Halucynacje | Instrukcja „tylko to, co widać”, schemat z `enum`, weryfikacja przez użytkownika, porównanie z oczekiwanym wynikiem |
| Bardzo duże PDF-y | Limit uploadu 30 MB; dzielenie na części, jeśli zestaw przekroczy limity API (sprawdźcie w dokumentacji Anthropic) |
| Prywatność (RODO) | Klucz i wywołania tylko w backendzie; brak logowania treści dokumentów; dane w pamięci; w produkcji: umowa powierzenia, retencja |

### Logika prawna
| Wyzwanie | Rozwiązanie |
|---|---|
| Dużo wyjątków (ojciec, wcześniak, adopcja, martwe urodzenie, łączenie z pracą) | Jedna reguła = jedna funkcja w `rules/`, rejestr `REGULY`; kolejność: najpierw zwykła ścieżka matki, potem wyjątki |
| Grosze w kwotach | `Decimal` + zaokrąglanie na końcu; porównanie ze sprawami ZUS co do grosza |
| Daty i tygodnie | Tydzień urlopu = 7 dni kalendarzowych; miesiąc zasiłku = 30 dni; testy na granicach (przestępny rok, koniec roku 6. urodzin) |
| Dwoje rodziców z różnymi podstawami | Każda osoba ma własny profil i podstawę; oś czasu łączy okresy obojga (TODO) |
| Niejasności w materiałach | Lista pytań do mentorów w `docs/pytania_kalkulator.md`; decyzje zapisujcie w README |

### Flutter Web na telefonie i komputerze
| Wyzwanie | Rozwiązanie |
|---|---|
| Różne szerokości ekranu | `core/responsive.dart`: dolny pasek nawigacji na telefonie, boczny panel na komputerze; `maxWidth` treści 1200 px, formularzy 640 px; `LayoutBuilder` dla siatek kart |
| Upload plików w przeglądarce | `file_picker` z `withData: true` (bajty), multipart z `MediaType('application','pdf')`; brak `dart:io` |
| CORS | `CORSMiddleware` z regexem dla localhost (dev) i listą domen produkcyjnych w `.env` |
| Długie pierwsze ładowanie Flutter Web (kilka MB) | `flutter build web --release`; ekran ładowania w `web/index.html`; nie dodawać zbędnych pakietów |
| Dostępność (ZUS = instytucja publiczna, WCAG) | `ensureSemantics()`, `semanticLabel` przy ikonach, kontrast z `ColorScheme`, duże pola dotyku |
| Klawiatura numeryczna na telefonie | `TextInputType.numberWithOptions(decimal: true)`, akceptowanie przecinka |
| Przycisk „wstecz” i linki w przeglądarce | `go_router` (prawdziwe adresy URL) |
| Polskie znaki, daty i kwoty | `utf8.decode(bodyBytes)` w ApiClient; `flutter_localizations` + `intl` (`pl`) |

### Zespół i wdrożenie
| Wyzwanie | Rozwiązanie |
|---|---|
| 3 osoby + agenci AI w jednym repo | `CLAUDE.md` z zasadami; podział: front (Janek) / backend + treści (koledzy); małe commity; kontrakt w `docs/api.md` |
| Rozjazd modeli Dart ↔ Python | Jeden plik modeli we Flutterze; zmiana API = zmiana `api.md` + `modele.dart` w tym samym commicie |
| Darmowy hosting usypia backend | Przed prezentacją wywołać `/health`; komunikat w UI „łączenie z serwerem…” z ponowieniem |
| Dokumenty ZUS nie mogą trafić do repo | `.gitignore` na `data/sprawy_zus/` i `*.pdf`; testy na sprawach tylko lokalnie |
| Dane w pamięci znikają po restarcie | Akceptowalne na demo; w opisie: produkcyjnie PostgreSQL (interfejs `storage/` gotowy do podmiany) |

## Kolejność prac (propozycja)
1. Backend: reguła i kalkulator dla najczęstszej sprawy (pracownica, 1 dziecko, 100/70 i 81,5%) + testy.
2. Odczyt skanu Agaty end-to-end (upload → Claude → profil → kalkulator) i porównanie z wynikiem ZUS.
3. Frontend: logowanie → kreator → kalkulator, sprawdzone na telefonie i komputerze.
4. Kolejne reguły: działalność (art. 48a, zadłużenie), ojciec, łączenie z pracą, adopcja, sytuacje szczególne.
5. Informacje (ryzyka, dokumenty, wsparcie), wnioski, panel admina.
6. Wdrożenie, film, prezentacja, zrzuty ekranu.
