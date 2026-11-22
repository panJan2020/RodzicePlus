# Kontrakt REST API

> Umowa między frontendem (Flutter) a backendem (FastAPI). Zmiana kształtu API = w tym samym commicie
> aktualizacja tego pliku **i** `frontend/lib/data/models/modele.dart`.
> Pełna, zawsze aktualna specyfikacja: `GET /docs` (Swagger) i `GET /openapi.json`.
> Funkcje i ekrany: `docs/opis_aplikacji.md` (w tabelach kolumna **Opis** = numer rozdziału).
> Model danych i przepływy: `docs/architektura.md`.

## 1. Konwencje

| Temat | Zasada |
|---|---|
| Adres bazowy | `http://localhost:8000` lokalnie; w produkcji z `--dart-define=API_URL=...` |
| Format | JSON, UTF-8, nazwy pól po polsku w `snake_case`, bez polskich znaków w kluczach |
| Daty | `RRRR-MM-DD` (ISO 8601); znaczniki czasu `RRRR-MM-DDTHH:MM:SSZ` |
| Kwoty | **tekst** z kropką i dwoma miejscami po przecinku, np. `"1234.56"` (backend liczy w `Decimal`; bez `float`) |
| Stawki | tekst, ułamek: `"1.00"`, `"0.70"`, `"0.815"` |
| Logowanie | nagłówek `Authorization: sim-<login>` (token z symulowanego logowania) |
| Admin | dodatkowo nagłówek `X-Admin-Token` |
| Błędy | `{"detail": "Komunikat po polsku dla użytkownika"}`; kody: `400` złe dane, `401` brak/zły token, `403` brak uprawnień, `404` nie ma zasobu, `409` konflikt wersji, `413` za duży plik, `422` walidacja |
| Teksty | wszystkie teksty dla użytkownika gotowe do wyświetlenia (Flutter niczego nie składa ani nie liczy) |
| Osoba | identyfikowana przez `osoba_id` (np. `"o1"`); rola w danych osoby. Parametr `osoba` pominięty = wnioskodawca (osoba zalogowana albo `o1`) |
| Liczby w wartościach pól | kwoty i ułamki (np. `etat`) jako tekst (`"0.50"`), liczby całkowite (dni, liczba dzieci) jako liczby; pola „na tytuł” jako słownik `{tytul: wartość}` |
| Stan wdrożenia | backend zwraca **podzbiór** pól opisanych niżej – pola, których jeszcze nie liczymy, dochodzą razem z regułami; nazwy i typy zawsze zgodne z tym plikiem |

---

## 2. Endpointy

### 2.1. Ogólne i logowanie

| Metoda | Ścieżka | Opis | Opis app |
|---|---|---|---|
| GET | `/health` | `{"status": "ok"}` – budzenie hostingu przed demo | – |
| GET | `/auth/mobywatel/konta` | konta testowe → `[{login, imie, nazwisko, opis}]` | 9 |
| POST | `/auth/mobywatel` | `{"login": "anna"}` → `Sesja`; `404` – brak konta | 9 |
| GET | `/auth/ja` | dane zalogowanej osoby → `Sesja`; `401` | 9 |

### 2.2. Sprawy i osoby

| Metoda | Ścieżka | Opis | Opis app |
|---|---|---|---|
| GET | `/sprawy` | sprawy zalogowanej osoby → `[SprawaSkrot]` | 2.1 |
| POST | `/sprawy` | `{"zdarzenie": "urodzenie" \| "przysposobienie" \| "rodzina_zastepcza", "nazwa": "..."}` → `Sprawa`; zalogowana osoba dodawana automatycznie | 2.1 |
| GET | `/sprawy/{id}` | `Sprawa` (osoby, liczniki konfliktów i braków, dokumenty – skrót) | 2.1 |
| POST | `/sprawy/{id}/osoby` | `{"rola": "ojciec" \| "drugi_rodzic" \| "dziecko", "imie": "..."}` → `Osoba` | 2.1 |
| DELETE | `/sprawy/{id}/osoby/{osoba_id}` | usuwa osobę (nie można usunąć zalogowanej) | 2.1 |

**Sprawy anonimowe są dozwolone.** `POST /sprawy` bez nagłówka `Authorization` tworzy sprawę z osobą `o1`
(`rola: matka`, `zalogowana: false`) – można wypełniać „Moje dane” i liczyć wyniki bez logowania. Z nagłówkiem
sprawa należy do zalogowanej osoby (`o1` = ona, `zalogowana: true`) i jest dostępna tylko z jej tokenem (`403` dla innych).
Przy `zdarzenie: "urodzenie"` od razu dodajemy osobę `o2` (`rola: dziecko`). Źródła symulowane (2.4) wymagają logowania.

### 2.3. Dane, kreator, wybór źródła

| Metoda | Ścieżka | Opis | Opis app |
|---|---|---|---|
| GET | `/sprawy/{id}/dane?osoba=o1` | `DaneOsoby` – wszystkie pytania w sekcjach, z wartościami ze wszystkich źródeł | 2, ekran 3 |
| GET | `/sprawy/{id}/pytania?osoba=o1` | kreator: pytania **aktywne bez aktywnej wartości** → `[Pytanie]` | 2.2 |
| POST | `/sprawy/{id}/odpowiedzi` | `[{"osoba": "o1", "pole": "pdp", "wartosc": "2026-12-20"}]` – dodaje/zmienia wartość **użytkownika**; `wartosc: null` usuwa tylko wartość użytkownika (wartości z innych źródeł zostają) → `ZmianaDanych`. Jeśli pole ma już wartość z innego źródła, odpowiedź użytkownika jest **świadomą edycją**: staje się aktywna z wyborem ręcznym (`wybor_aktywnej: uzytkownik`), a tamta wartość zostaje i konflikt jest widoczny. `400` – pole nieznane, nie dotyczy osoby albo jest tylko do podglądu; `422` – wartość nie pasuje do typu | 2.2, 4 |
| PUT | `/sprawy/{id}/osoby/{osoba_id}/pola/{pole}/aktywna` | `{"wartosc_id": "w2"}` – użytkownik wybiera źródło pola; `{"wartosc_id": null}` przywraca wybór automatyczny → `ZmianaDanych` | 4.1 |

### 2.4. Źródła danych

| Metoda | Ścieżka | Opis | Opis app |
|---|---|---|---|
| GET | `/zrodla` | lista źródeł → `[{kod, nazwa, wystawca, opis, symulacja: true}]` | 3 |
| POST | `/sprawy/{id}/zrodla/{kod}/pobierz` | `{"osoba": "o1"}` – pobiera dane ze źródła (`mobywatel`, `rsc`, `zus_konto`, `zus_platnik`, `zus_historia`, `ezla`, `pue`); **dodaje** wartości (ponowne pobranie aktualizuje wartość z tego źródła, nie dubluje jej), aktywną wybiera hierarchia → `ZmianaDanych`. Wymaga logowania (`401`); tylko dla osoby zalogowanej w tej sprawie (`403`); body opcjonalne (domyślnie osoba zalogowana) | 3 |

### 2.5. Konflikty i niespójności

| Metoda | Ścieżka | Opis | Opis app |
|---|---|---|---|
| GET | `/sprawy/{id}/konflikty` | `{"konflikty": [Konflikt], "niespojnosci": [Niespojnosc]}` | 4, ekran 4 |

Rozstrzygnięcie konfliktu = `PUT …/pola/{pole}/aktywna` (2.3).

### 2.6. Dokumenty (upload)

| Metoda | Ścieżka | Opis | Opis app |
|---|---|---|---|
| POST | `/sprawy/{id}/dokumenty` | multipart, pole `pliki` (1..n PDF/JPG/PNG, max 30 MB każdy) → `202 {"zadanie_id": "z1"}` | 6 |
| GET | `/zadania/{zadanie_id}` | `Zadanie` – stan odczytu; Flutter odpytuje co 3 s | 6 |
| GET | `/sprawy/{id}/dokumenty` | rozpoznane dokumenty → `[Dokument]` | 6, ekran 5 |
| DELETE | `/sprawy/{id}/dokumenty/{dokument_id}` | usuwa dokument **i wartości z niego odczytane** → `ZmianaDanych` | 6 |
| GET | `/sprawy/{id}/porownanie` | wynik aplikacji vs decyzja ZUS → `Porownanie`; `404`, gdy sprawa nie ma decyzji ZUS | 6 |

Odczytane pola do potwierdzenia = wartości z `kanal: "upload"` w `GET /sprawy/{id}/dane`. Poprawienie odczytu = `POST /odpowiedzi` (nowa wartość użytkownika) albo wybór innej wartości.

### 2.7. Ubezpieczenie, e-ZLA, zadłużenie

| Metoda | Ścieżka | Opis | Opis app |
|---|---|---|---|
| GET | `/sprawy/{id}/ubezpieczenie?osoba=o1&na_dzien=RRRR-MM-DD` | `DaneUbezpieczenia` (na podstawie aktywnej wartości pola `okresy_ubezpieczenia`; `na_dzien` domyślnie dziś); `404`, gdy sprawa nie ma jeszcze okresów ubezpieczenia (najpierw pobierz `zus_konto`) | 9, ekran 6 |
| GET | `/sprawy/{id}/ezla?osoba=o1` | `[ZwolnienieEzla]` | 9, ekran 6 |
| POST | `/sprawy/{id}/zaswiadczenie-zadluzenie` | `{"osoba": "o1", "na_dzien": "2026-12-30"}` → `ZaswiadczenieZadluzenie` | 9, ekran 6 |
| GET | `/sprawy/{id}/zaswiadczenie-zadluzenie/{zid}/pdf` | PDF zaświadczenia (symulacja) | 9 |

### 2.8. Świadczenia

| Metoda | Ścieżka | Opis | Opis app |
|---|---|---|---|
| GET | `/swiadczenia` | katalog wszystkich świadczeń → `[SwiadczenieKatalog]` | 5.1, ekran 8 |
| GET | `/swiadczenia/{kod}` | szczegóły: opis, wymagania, wymagane pola, przepisy | 5.1 |
| GET | `/sprawy/{id}/swiadczenia?scenariusz=s1` | wyniki dla wszystkich osób sprawy → `[WynikSwiadczenia]`; bez `scenariusz` – scenariusz domyślny | 5.2, ekran 7 |

### 2.9. Kalkulator i scenariusze

| Metoda | Ścieżka | Opis | Opis app |
|---|---|---|---|
| POST | `/kalkulator` | **bez logowania**: `{"fakty": {...}, "scenariusz": {...}}` (pola z katalogu pytań) → `WynikKalkulatora` | 7 |
| GET | `/sprawy/{id}/scenariusze` | `[Scenariusz]` (zawsze jest co najmniej domyślny) | 2.3 |
| POST | `/sprawy/{id}/scenariusze` | `{"nazwa": "...", "wybory": {...}}` → `Scenariusz` | 2.3 |
| PUT | `/sprawy/{id}/scenariusze/{sid}` | zmiana nazwy lub wyborów → `Scenariusz` | 2.3 |
| DELETE | `/sprawy/{id}/scenariusze/{sid}` | usuwa (nie domyślny) | 2.3 |
| GET | `/sprawy/{id}/kalkulator?scenariusz=s1` | `WynikKalkulatora` dla sprawy. Do czasu scenariuszy (etap 4) liczony jest tylko scenariusz domyślny (`scenariusz_id: "domyslny"`), budowany z faktów: `wniosek_81_5 = true`, gdy `wniosek_81_5_data` mieści się w terminie z parametru `wniosek_jednolita_dni` od porodu | 7 |
| GET | `/sprawy/{id}/kalkulator/porownanie?scenariusze=s1,s2` | `[WynikKalkulatora]` + `roznice` | 7 |

### 2.10. Informacje

| Metoda | Ścieżka | Opis | Opis app |
|---|---|---|---|
| GET | `/info/poradnik/{swiadczenie}?sprawa={id}&osoba=o1` | `Poradnik` – kroki dopasowane do sytuacji (kto wypłaca, status); bez `sprawa` – wersja ogólna | 8 |
| GET | `/info/ryzyka?sprawa={id}` | `[Ryzyko]`; z `sprawa` – z flagą `dotyczy_ciebie` | 8 |
| GET | `/info/ochrona` | szczególna ochrona z Kodeksu pracy → `TrescInformacyjna` | 8 |
| GET | `/info/wsparcie` | organizacje charytatywne → `[Organizacja]` | ekran 12 |
| GET | `/info/dokumenty` | lista przydatnych dokumentów i formularzy → `[DokumentInfo]` | ekran 11 |
| GET | `/info/linki` | zus.pl, gov.pl, PIP → `[Link]` | ekran 12 |

### 2.11. Wnioski (symulacja)

| Metoda | Ścieżka | Opis | Opis app |
|---|---|---|---|
| GET | `/wnioski/typy` | `[{kod, nazwa, adresat, opis}]`: `urlop_macierzynski`, `urlop_rodzicielski`, `urlop_ojcowski`, …, `zam`, `odpis_aktu_urodzenia` | 9 |
| POST | `/sprawy/{id}/wnioski` | `{"typ": "zam", "osoba": "o1", "scenariusz": "s1", "dane": {...}}` – wypełnia danymi ze sprawy → `Wniosek` (z listą brakujących pól) | 9, ekran 10 |
| GET | `/sprawy/{id}/wnioski` | `[Wniosek]` | ekran 10 |
| PUT | `/wnioski/{wid}` | uzupełnienie pól wniosku → `Wniosek` | 9 |
| GET | `/wnioski/{wid}/pdf` | podgląd PDF | 9 |
| POST | `/wnioski/{wid}/wyslij` | `{"adresat": "pracodawca" \| "zus" \| "usc"}` → `Wniosek` ze statusem `wyslany` i numerem potwierdzenia (symulacja) | 9 |

### 2.12. PUE / eZUS (symulacja)

| Metoda | Ścieżka | Opis | Opis app |
|---|---|---|---|
| GET | `/pue/konto` | podgląd danych z konta: tytuły ubezpieczenia, płatnicy, wnioski, pisma → `KontoPue` | 9, ekran 13 |
| GET | `/pue/pytania` | historia pytań → `[PytaniePue]` | 9 |
| POST | `/pue/pytania` | `{"temat": "...", "tresc": "...", "sprawa": "id?"}` → `PytaniePue` (z symulowaną odpowiedzią) | 9 |

### 2.13. Panel administracyjny (`X-Admin-Token`)

| Metoda | Ścieżka | Opis | Opis app |
|---|---|---|---|
| GET | `/admin/parametry` | wszystkie wersje → `[WersjaParametrow]` | 10 |
| GET | `/admin/parametry/obowiazujace?na_dzien=RRRR-MM-DD` | wersja obowiązująca w danym dniu | 10 |
| POST | `/admin/parametry` | nowa wersja `{"obowiazuje_od": "...", "parametry": {...}, "opis_zmiany": "..."}`; walidacja typów i zakresów | 10 |
| GET | `/admin/moduly` | `[{kod, nazwa, wlaczony}]` | 10 |
| PUT | `/admin/moduly/{kod}` | `{"wlaczony": false}` | 10 |
| GET | `/admin/tresci` | lista treści (poradniki, ryzyka, organizacje, linki) | 10 |
| PUT | `/admin/tresci/{klucz}` | `{"tresc": ..., "wersja": 3}`; `409` przy nieaktualnej wersji | 10 |
| GET | `/moduly` | **publiczne**: włączone moduły (Flutter ukrywa wyłączone ekrany) | 10 |

---

## 3. Kształty danych

### 3.1. Sesja, sprawa, osoba

```jsonc
// Sesja
{"token": "sim-anna", "login": "anna", "imie": "Anna", "nazwisko": "Testowa", "admin": false}

// SprawaSkrot
{"id": "sp1", "nazwa": "Ciąża 2026", "zdarzenie": "urodzenie", "utworzono": "2026-11-22T01:00:00Z"}

// Sprawa
{"id": "sp1", "nazwa": "Ciąża 2026", "zdarzenie": "urodzenie",
 "osoby": [{"id": "o1", "rola": "matka", "imie": "Anna", "zalogowana": true},
           {"id": "o2", "rola": "ojciec", "imie": "Tomasz", "zalogowana": false}],
 "liczniki": {"konflikty": 1, "niespojnosci": 0, "brakujace_pola": 4, "dokumenty": 6},
 "ma_decyzje_zus": true}
```

### 3.2. Wartości pól i dane osoby

```jsonc
// WartoscPola – jedna wartość z jednego źródła
{"id": "w2", "wartosc": "2026-12-30",
 "wystawca": "lekarz",            // zus | urzad | sad | pracodawca | lekarz | uzytkownik | wyliczone
 "kanal": "upload",               // mobywatel | rsc | zus_konto | zus_platnik | zus_historia | ezla | pue | upload | kreator | system
 "zrodlo_opis": "Zaświadczenie lekarskie, str. 1",   // gotowy tekst do „Skąd to wiemy”
 "dokument_id": "d3", "strona": 1, "pewnosc": 0.92,
 "do_sprawdzenia": false,         // true, gdy pewnosc < 0,6
 "aktywna": true, "utworzono": "2026-11-22T01:10:00Z"}

// Pytanie (element DaneOsoby i odpowiedź /pytania)
{"id": "G1", "sekcja": "G", "pole": "pdp",
 "tresc": "Kiedy planowany jest poród?",
 "typ": "data",                   // wybor | wielokrotny | tak_nie | liczba | kwota | data | okresy
 "opcje": [],                     // dla wybor / wielokrotny: [{"wartosc": "...", "etykieta": "..."}]
 "pomoc": "…", "gdzie_znalezc": "zaświadczenie lekarskie o przewidywanej dacie porodu",
 "rodzaj": "fakt",                // fakt | plan (plany tylko od użytkownika) | wyliczone
 "edytowalne": true,              // false: tylko podgląd (np. e-ZLA, okresy ubezpieczenia) albo brak kreatora w źródłach
 "na_tytul": false,               // true: wartość to słownik {tytul: odpowiedź}
 "klucze": [],                    // pola „na tytuł” (B4, C1): [{"wartosc": "umowa_o_prace", "etykieta": "Umowa o pracę"}] –
                                  // wartość pola to słownik {"umowa_o_prace": "ponad_20", ...}
 "status": "aktywne",             // aktywne | zablokowane (czeka_na) | wykluczone (wartość zostaje, reguły jej nie używają)
 "czeka_na": [],
 "wartosci": [ /* WartoscPola */ ],
 "aktywna_wartosc_id": "w2",
 "wybor_aktywnej": "automatyczny",  // automatyczny (hierarchia) | uzytkownik
 "konflikt": true}

// DaneOsoby – GET /sprawy/{id}/dane
{"osoba": {"id": "o1", "rola": "matka", "imie": "Anna"},
 "postep": {"odpowiedziane": 18, "aktywne": 25},
 "sekcje": [{"id": "A", "tytul": "Dziecko i poród", "postep": {"odpowiedziane": 2, "aktywne": 3},
             "pytania": [ /* Pytanie */ ]}]}

// ZmianaDanych – po każdej zmianie danych (Flutter odświeża liczniki i wyniki)
{"dodano": 3, "zmieniono_aktywne": ["pdp"], "nowe_konflikty": 1,
 "liczniki": {"konflikty": 1, "niespojnosci": 0, "brakujace_pola": 2},
 "wyniki_nieaktualne": true}
```

### 3.3. Konflikty i niespójności

```jsonc
// Konflikt
{"osoba_id": "o1", "osoba_imie": "Anna", "pole": "pdp",
 "pytanie": "Kiedy planowany jest poród?",
 "wartosci": [ /* WartoscPola */ ], "aktywna_wartosc_id": "w2",
 "wybor_aktywnej": "automatyczny",
 "uzasadnienie_wyboru": "Wybrano zaświadczenie lekarskie – ma pierwszeństwo przed danymi wpisanymi ręcznie.",
 "wplywa_na": ["zasilek_macierzynski"]}

// Niespojnosc
{"kod": "zwolnienie_przed_zatrudnieniem", "osoba_id": "o1",
 "pola": ["zatrudnienie_od", "ezla"],
 "komunikat": "Zwolnienie lekarskie zaczyna się przed datą zatrudnienia. Sprawdź obie daty.",
 "waga": "ostrzezenie"}           // ostrzezenie | informacja
```

### 3.4. Dokumenty i zadania

```jsonc
// Zadanie – GET /zadania/{id}
{"id": "z1", "status": "w_toku",  // w_toku | gotowe | blad
 "etap": "odczyt",                // przyjecie | klasyfikacja | podzial | odczyt | scalanie | wyniki
 "postep": 0.6, "komunikat": "Odczytujemy zaświadczenie Z-3 (2 z 4)…",
 "dokumenty": ["d1", "d2"],       // rozpoznane do tej pory
 "zmiana_danych": null,           // ZmianaDanych po zakończeniu
 "blad": null}

// Dokument
{"id": "d2", "plik": "sprawa.pdf", "typ": "Z-3", "typ_opis": "Zaświadczenie płatnika składek",
 "wariant": "pierwszorazowy",     // pierwszorazowy | w_kontynuacji | null
 "strony": [5, 12], "osoba_id": "o1",
 "wystawca": "pracodawca", "archiwalny": false,   // true dla ZUR, ZAO, Z-3b
 "rola": "dane",                  // dane | decyzja_zus | pismo_zus
 "liczba_pol": 14, "do_sprawdzenia": 1}

// Porownanie – GET /sprawy/{id}/porownanie
{"decyzja_zus": {"tekst": "W sprawie przyznano zasiłek chorobowy.", "dokument_id": "d7", "strona": 38,
                 "swiadczenie": "zasilek_chorobowy_ciaza", "rozstrzygniecie": "przyznano", "kwota": null},
 "wynik_aplikacji": {"swiadczenie": "zasilek_chorobowy_ciaza", "status": "przysluguje", "kwota": "…"},
 "zgodnosc": "zgodne",            // zgodne | rozne | nie_do_porownania
 "uwagi": []}
```

### 3.5. Ubezpieczenie, e-ZLA, zadłużenie

```jsonc
// DaneUbezpieczenia
{"stan_na": "2026-11-22", "ubezpieczony_chorobowo": true,
 "podsumowanie": "Podlegasz ubezpieczeniu chorobowemu (umowa o pracę).",
 "wyjasnienia": ["Ubezpieczenie chorobowe trwa nieprzerwanie od 01.10.2024."],
 "okresy": [{"tytul": "umowa_o_prace", "tytul_opis": "Umowa o pracę", "platnik": "Firma Przykładowa",
             "platnik_ponad_20": false, "od": "2024-10-01", "do": null, "wymiar_etatu": "0.25",
             "chorobowe": true, "chorobowe_dobrowolne": false, "aktywny": true,
             "zrodlo_opis": "Zrzut z systemu ZUS, str. 37"}],
 "okres_wyczekiwania": {"wymagany_dni": 30, "spelniony_od": "2024-10-31"},
 "kto_wyplaca": "zus", "kto_wyplaca_opis": "Pracodawca zgłasza do 20 osób – zasiłek wypłaci ZUS."}

// ZwolnienieEzla
{"od": "2025-02-18", "do": "2025-03-22", "kod_b": true, "kody": ["B"], "wystawiono": "2025-02-18",
 "zrodlo_opis": "e-ZLA (symulacja)"}

// ZaswiadczenieZadluzenie
{"id": "zz1", "na_dzien": "2026-12-30", "zadluzenie": "0.00", "prog": "…", "blokuje_wyplate": false,
 "komunikat": "Na dzień 30.12.2026 nie masz zadłużenia z tytułu składek.", "pdf": "/sprawy/sp1/zaswiadczenie-zadluzenie/zz1/pdf"}
```

### 3.6. Świadczenia

```jsonc
// SwiadczenieKatalog
{"kod": "zasilek_macierzynski_urlop_rodzicielski", "nazwa": "Zasiłek macierzyński za okres urlopu rodzicielskiego",
 "grupa": "macierzynski",         // ciaza | macierzynski | szczegolne
 "krotki_opis": "…", "dla_kogo": ["matka", "ojciec"], "przepisy": ["art. 31 ustawy zasiłkowej"]}

// WynikSwiadczenia
{"swiadczenie": "zasilek_macierzynski_urlop_macierzynski", "nazwa": "…",
 "osoba_id": "o1", "scenariusz_id": "s1",
 "status": "warunkowo",           // przysluguje | warunkowo | brak_danych | nie_przysluguje
 "podsumowanie": "Przysługuje Ci zasiłek za 20 tygodni, o ile w dniu porodu nadal będziesz ubezpieczona.",
 "okres": {"od": "2026-12-30", "do": "2027-05-18", "tygodnie": 20},
 "kwota": {"miesieczna": "…", "za_okres": "…", "stawka": "1.00", "podstawa_wymiaru": "…",
           "brutto": true},
 "kto_wyplaca": "zus",            // zus | platnik
 "kto_wyplaca_opis": "Zasiłek wypłaci ZUS (art. 61 ustawy zasiłkowej).",
 "gdzie_zlozyc": "ZUS (wniosek ZAM) – pracodawca przekaże Z-3",
 "uzasadnienie": ["Podlegasz ubezpieczeniu chorobowemu od 01.10.2024.", "…"],
 "powody": [],                    // przy nie_przysluguje: [{"pole": "...", "wartosc": "...", "komunikat": "..."}]
 "warunki": [{"opis": "Ubezpieczenie chorobowe w dniu porodu", "ryzyko": "brak_ubezpieczenia_w_dniu_porodu"}],
 "brakujace_pola": [],            // przy brak_danych: [{"pytanie_id": "B1", "tresc": "...", "gdzie_znalezc": "..."}]
 "co_zrobic": [],                 // przy nie_przysluguje / brak_danych: gotowe teksty
 "orientacyjny": true, "pola_do_potwierdzenia": ["miesiace"],
 "ryzyka": ["brak_ubezpieczenia_w_dniu_porodu"],
 "podstawa_prawna": ["art. 29 ustawy zasiłkowej"],
 "wersja_parametrow": "2026-10-24"}
```

### 3.7. Scenariusze i kalkulator

```jsonc
// Scenariusz – tylko wybory i plany, nigdy fakty
{"id": "s1", "nazwa": "Oboje po połowie", "domyslny": false,
 "wybory": {
   "wniosek_81_5": true,                       // wniosek o całość do 21 dni po porodzie
   "start_urlopu_macierzynskiego": "2026-12-30",
   "przejecie_macierzynskiego_przez": null,    // "o2" + "od"
   "podzial_rodzicielskiego": [
     {"osoba_id": "o1", "od": "2027-05-19", "tygodnie": 16, "praca_wymiar": null},
     {"osoba_id": "o2", "od": "2027-09-08", "tygodnie": 25, "praca_wymiar": "0.5"}],
   "urlop_ojcowski": [{"osoba_id": "o2", "od": "2027-01-10", "dni": 14}]}}

// WynikKalkulatora
{"scenariusz_id": "s1", "wersja_parametrow": "2026-10-24",
 "osoby": [{"osoba_id": "o1", "podstawa_wymiaru": "7075.78", "suma": "…", "powrot_do_pracy": "2027-09-08"},
           {"osoba_id": "o2", "podstawa_wymiaru": "6500.00", "suma": "…", "powrot_do_pracy": "2028-02-01"}],
 "okresy": [{"rodzaj": "macierzynski", "osoba_id": "o1", "od": "2026-12-30", "do": "2027-05-18",
             "tygodnie": 20, "stawka": "0.815", "kwota_miesieczna": "…", "kwota_za_okres": "…",
             "praca_wymiar": null, "uwagi": []}],
 "suma": "…",
 "ostrzezenia": ["Każdemu z rodziców przysługuje 9 tygodni urlopu rodzicielskiego, których nie można przenieść."],
 "bledy_wyborow": []}             // np. przekroczona pula, więcej niż 5 części

// Porównanie scenariuszy – GET /sprawy/{id}/kalkulator/porownanie
{"wyniki": [ /* WynikKalkulatora */ ],
 "roznice": [{"miara": "suma", "wartosci": {"s1": "…", "s2": "…"}},
             {"miara": "powrot_do_pracy_o1", "wartosci": {"s1": "2027-09-08", "s2": "2027-12-29"}}]}
```

### 3.8. Informacje

```jsonc
// Poradnik
{"swiadczenie": "zasilek_macierzynski_urlop_macierzynski", "status": "warunkowo",
 "kto_wyplaca": "zus",
 "ryzyka_na_poczatku": [ /* Ryzyko */ ],
 "kroki": [{"nr": 1, "tytul": "Poproś pracodawcę o zaświadczenie Z-3",
            "opis": "…", "termin": "po porodzie", "gdzie": "pracodawca",
            "dokumenty": [{"kod": "Z-3", "nazwa": "Zaświadczenie płatnika składek", "url": "https://www.zus.pl/…"}],
            "sposob": ["papierowo", "PUE/eZUS"]}]}

// Ryzyko
{"kod": "umowa_dla_pozoru", "tytul": "Umowa zawarta dla pozoru", "opis": "…",
 "skutek": "ZUS może uznać, że nie podlegasz ubezpieczeniu.", "dotyczy_ciebie": false, "dlaczego": null}

// Organizacja
{"nazwa": "…", "obszary": ["smierc_dziecka", "poronienie", "wczesniactwo", "ciezka_choroba_dziecka"],
 "opis": "…", "url": "https://…", "telefon": "…", "zweryfikowano": "2026-11-22"}

// DokumentInfo
{"kod": "ZAM", "nazwa": "Wniosek o zasiłek macierzyński", "kiedy": "…", "kto_sklada": "…",
 "url": "https://www.zus.pl/…", "archiwalny": false}

// Link / TrescInformacyjna
{"tytul": "…", "url": "https://…", "opis": "…"}
{"tytul": "…", "tresc_md": "…", "zrodla": ["Kodeks pracy, art. 177"]}
```

### 3.9. Wnioski i PUE

```jsonc
// Wniosek
{"id": "wn1", "typ": "zam", "nazwa": "Wniosek o zasiłek macierzyński (ZAM)",
 "osoba_id": "o1", "status": "szkic",   // szkic | gotowy | wyslany
 "pola": [{"klucz": "pesel", "etykieta": "PESEL", "wartosc": "…", "z_profilu": true}],
 "brakujace": ["numer_rachunku"],
 "adresat": "zus", "wyslano": null, "numer_potwierdzenia": null,
 "pdf": "/wnioski/wn1/pdf"}

// KontoPue
{"tytuly": [ /* okresy jak w DaneUbezpieczenia */ ], "platnicy": [{"nazwa": "…", "nip": "…"}],
 "wnioski": [{"typ": "ZAS-53", "zlozono": "2025-02-18", "status": "w_toku"}],
 "pisma": [{"data": "2025-03-01", "tytul": "Prośba o zaświadczenie Z-3"}]}

// PytaniePue
{"id": "p1", "temat": "…", "tresc": "…", "zadano": "…", "odpowiedz": "…(symulacja)", "status": "odpowiedziane"}
```

### 3.10. Admin

```jsonc
// WersjaParametrow
{"id": "2026-10-24", "obowiazuje_od": "2026-10-24", "opis_zmiany": "…",
 "parametry": {"stawka_macierzynski": "1.00", "stawka_rodzicielski": "0.70", "stawka_jednolita": "0.815",
               "urlop_macierzynski_tygodnie": {"1": 20, "2": 31, "3": 33, "4": 35, "5": 37},
               "urlop_rodzicielski_tygodnie": {"1": 41, "2+": 43}, "…": "…"}}
```
