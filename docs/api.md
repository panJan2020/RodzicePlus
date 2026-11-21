# Kontrakt REST API

Bazowy adres: `http://localhost:8000` (lokalnie). Pełna, zawsze aktualna specyfikacja: `GET /docs` (Swagger) i `GET /openapi.json`.
Nagłówek `Authorization: sim-<login>` – token z symulowanego logowania.

| Metoda | Ścieżka | Opis | FR |
|---|---|---|---|
| GET | `/health` | czy serwer żyje (budzenie hostingu przed demo) | – |
| GET | `/auth/mobywatel/konta` | konta testowe → `[{login, imie, nazwisko, opis}]` | FR-01 |
| POST | `/auth/mobywatel` | `{uzytkownik}` → `Sesja` (`404` – brak konta) | FR-01 |
| GET | `/auth/ja` | dane zalogowanej osoby → `Sesja` (`401` – zły/brak tokenu) | FR-01 |
| GET | `/zus/ubezpieczenie?na_dzien=RRRR-MM-DD` | `DaneUbezpieczenia` – czy podlega ubezpieczeniu chorobowemu, okresy, tytuły (mock; `na_dzien` opcjonalnie, domyślnie dziś) | FR-02 |
| GET | `/zus/zadluzenie` | zadłużenie składkowe (mock) | FR-04 |
| GET | `/zus/ezla` | zwolnienia lekarskie (mock) | FR-05 |
| POST | `/zus/pobierz-do-sprawy/{id}` | kopiuje dane z „ZUS” do profilu sprawy (`zrodlo=zus`, nie nadpisuje odpowiedzi użytkownika) → `{uzupelniono[], pominieto[], ubezpieczenie: DaneUbezpieczenia}` | FR-02 |
| POST | `/sprawy` | nowa sprawa → `Sprawa` | FR-03 |
| GET | `/sprawy/{id}` | profil sprawy: osoby → pola (`FieldValue` ze źródłem) | – |
| POST | `/sprawy/{id}/odpowiedzi` | `[{pole, wartosc, osoba}]` – odpowiedzi z kreatora | FR-03 |
| GET | `/sprawy/{id}/pytania` | następne pytania (warunki liczone w backendzie) | FR-03 |
| POST | `/sprawy/{id}/dokumenty` | upload PDF (multipart, pole `plik`) → `202 {zadanie_id}` | FR-28 |
| GET | `/sprawy/zadania/{zadanie_id}` | `{status: w_toku|gotowe|blad, strony, uwagi, blad}` | FR-28 |
| GET | `/sprawy/{id}/uprawnienia` | `[WynikUprawnienia]` – status, uzasadnienie, brakujące pola, kto wypłaca | FR-07..10, 20 |
| GET | `/sprawy/{id}/kalkulator` | `WynikKalkulatora` – podstawa, okresy, kwoty | FR-11..18 |
| GET | `/info/linki`, `/info/wsparcie` | treści informacyjne | FR-24, 27 |
| GET | `/admin/parametry` | aktualne parametry prawne | FR-30 |
| PUT | `/admin/parametry` | nowa wersja parametrów (nagłówek `X-Admin-Token`) | FR-30 |

## Kształty danych

```jsonc
// Sesja – wynik logowania (token wysyłamy potem w nagłówku Authorization)
{"token": "sim-anna", "login": "anna", "imie": "Anna", "nazwisko": "Testowa"}

// DaneUbezpieczenia – GET /zus/ubezpieczenie (teksty gotowe do pokazania)
{"stan_na": "2026-11-21", "ubezpieczony_chorobowo": true,
 "podsumowanie": "Podlegasz ubezpieczeniu chorobowemu (umowa o pracę).",
 "wyjasnienia": ["Ubezpieczenie chorobowe trwa nieprzerwanie od 01.03.2021.", "..."],
 "okresy": [{"tytul": "umowa_o_prace", "tytul_opis": "Umowa o pracę", "platnik": "Hurtownia Przykładowa S.A.",
             "platnik_ponad_20": "ponad_20", "od": "2021-03-01", "do": null, "chorobowe": true,
             "chorobowe_dobrowolne": false, "aktywny": true}],
 "tytuly": ["umowa_o_prace"], "chorobowe_od": "2021-03-01", "chorobowe_dobrowolne": false, "platnik_ponad_20": "ponad_20"}

// FieldValue – każda wartość w sprawie
{"wartosc": "2026-07-10", "zrodlo": "dokument", "dokument": "ZAM", "strona": 7, "pewnosc": 0.92, "potwierdzone": false}

// WynikUprawnienia
{"swiadczenie": "zasilek_macierzynski", "status": "przysluguje",
 "uzasadnienie": ["..."], "podstawa_prawna": ["art. 29 ustawy zasiłkowej"],
 "brakujace_pola": [], "ostrzezenia": [], "kto_wyplaca": "ZUS"}

// WynikKalkulatora
{"podstawa_wymiaru": 7075.78, "suma": 61234.56, "wersja_parametrow": "params_2026.json", "ostrzezenia": [],
 "okresy": [{"rodzaj": "macierzynski", "osoba": "matka", "od": "2026-07-10", "do": "2026-11-26",
             "stawka": 1.0, "kwota_miesieczna": 7075.78, "kwota_za_okres": 33018.20, "uwagi": []}]}
```
