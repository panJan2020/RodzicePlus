// Fałszywy backend do testów widżetów (bez sieci). Kształty odpowiedzi = docs/api.md.
import 'dart:convert';

import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:rodziceplus/app.dart';
import 'package:rodziceplus/data/api_client.dart';

http.Response _json(Object? o, [int kod = 200]) =>
    http.Response.bytes(utf8.encode(jsonEncode(o)), kod, headers: {'content-type': 'application/json'});

const _konta = {
  'anna': {'imie': 'Anna', 'nazwisko': 'Testowa', 'opis': 'Pracownica na etacie.'},
  'kasia': {'imie': 'Katarzyna', 'nazwisko': 'Przykładowa', 'opis': 'Umowa o dzieło.'},
};

Map<String, Object?> _sesja(String login) => {
      'token': 'sim-$login', 'login': login, 'imie': _konta[login]!['imie'],
      'nazwisko': _konta[login]!['nazwisko'], 'admin': false,
    };

Map<String, Object?> _ubezpieczenie(String login) => login == 'anna'
    ? {
        'stan_na': '2026-11-21',
        'ubezpieczony_chorobowo': true,
        'podsumowanie': 'Podlegasz ubezpieczeniu chorobowemu (umowa o pracę).',
        'wyjasnienia': ['Ubezpieczenie chorobowe trwa nieprzerwanie od 01.03.2021.'],
        'okresy': [
          {
            'tytul': 'umowa_o_prace', 'tytul_opis': 'Umowa o pracę', 'platnik': 'Hurtownia Przykładowa S.A.',
            'platnik_ponad_20': true, 'od': '2021-03-01', 'do': null, 'wymiar_etatu': '1.00', 'chorobowe': true,
            'chorobowe_dobrowolne': false, 'aktywny': true, 'zrodlo_opis': 'Konto w ZUS',
          },
        ],
      }
    : {
        'stan_na': '2026-11-21',
        'ubezpieczony_chorobowo': false,
        'podsumowanie': 'Obecnie nie podlegasz ubezpieczeniu chorobowemu.',
        'wyjasnienia': ['Ostatnie ubezpieczenie chorobowe skończyło się 31.08.2026.'],
        'okresy': [
          {
            'tytul': 'umowa_o_prace', 'tytul_opis': 'Umowa o pracę', 'platnik': 'Sklep Testowy sp. z o.o.',
            'platnik_ponad_20': true, 'od': '2022-01-01', 'do': '2026-08-31', 'wymiar_etatu': null, 'chorobowe': true,
            'chorobowe_dobrowolne': false, 'aktywny': false, 'zrodlo_opis': 'Konto w ZUS',
          },
        ],
      };

/// Ile razy wywołano dany endpoint (do sprawdzeń w testach).
final wywolania = <String, int>{};

/// Odpowiedzi zapisane przez POST /sprawy/sprawa1/odpowiedzi (pole → wartość).
final odpowiedzi = <String, Object?>{};

/// Czy pobrano już dane z ZUS do sprawy (wtedy /ubezpieczenie zwraca dane zamiast 404).
var _pobranoZus = false;

const _liczniki = {'konflikty': 0, 'niespojnosci': 0, 'brakujace_pola': 2};

Map<String, Object?> _zmiana({int dodano = 1}) => {
      'dodano': dodano, 'zmieniono_aktywne': ['sytuacja'], 'nowe_konflikty': 0, 'liczniki': _liczniki,
      'wyniki_nieaktualne': true,
    };

Map<String, Object?> _sprawa() => {
      'id': 'sprawa1', 'nazwa': 'Moja sprawa', 'zdarzenie': 'urodzenie', 'utworzono': '2026-11-22T01:00:00Z',
      'osoby': [
        {'id': 'o1', 'rola': 'matka', 'imie': null, 'zalogowana': false},
        {'id': 'o2', 'rola': 'dziecko', 'imie': 'Dziecko', 'zalogowana': false},
      ],
      'liczniki': {..._liczniki, 'dokumenty': 0},
      'ma_decyzje_zus': false,
    };

Map<String, Object?> _wartosc(String id, Object? v,
        {String wystawca = 'uzytkownik', String kanal = 'kreator', String opis = 'Twoja odpowiedź',
        double pewnosc = 1, bool doSprawdzenia = false}) =>
    {
      'id': id, 'wartosc': v, 'wystawca': wystawca, 'kanal': kanal, 'zrodlo_opis': opis, 'dokument_id': null,
      'strona': null, 'pewnosc': pewnosc, 'do_sprawdzenia': doSprawdzenia, 'aktywna': true,
      'utworzono': '2026-11-22T01:10:00Z',
    };

Map<String, Object?> _pytanie(String id, String sekcja, String pole, String tresc, String typ,
        {String status = 'aktywne', List<String> czekaNa = const [], Map<String, Object?>? wartosc,
        List<Map<String, String>> opcje = const []}) =>
    {
      'id': id, 'sekcja': sekcja, 'pole': pole, 'tresc': tresc, 'typ': typ, 'opcje': opcje,
      'pomoc': null, 'gdzie_znalezc': null, 'rodzaj': 'fakt', 'edytowalne': true, 'na_tytul': false, 'klucze': [],
      'status': status, 'czeka_na': czekaNa, 'wartosci': [?wartosc], 'aktywna_wartosc_id': wartosc?['id'],
      'wybor_aktywnej': 'automatyczny', 'konflikt': false,
    };

/// Uproszczone drzewo: A1 → G2 (zablokowane, dopóki brak A1), B1 z niepewnego odczytu Z-3,
/// Q1s zawsze wykluczone. Warunki liczy prawdziwy backend – tu tylko stałe stany do testów UI.
Map<String, Object?> _drzewo() {
  final a1 = odpowiedzi['sytuacja'];
  return {
    'osoba': {'id': 'o1', 'rola': 'matka', 'imie': null},
    'postep': {'odpowiedziane': a1 == null ? 1 : 2, 'aktywne': a1 == null ? 2 : 3},
    'sekcje': [
      {'id': 'A', 'tytul': 'Sytuacja i rola', 'postep': {'odpowiedziane': a1 == null ? 0 : 1, 'aktywne': 1},
       'pytania': [
         _pytanie('A1', 'A', 'sytuacja', 'Jaka jest Twoja sytuacja?', 'wielokrotny',
             opcje: [{'wartosc': 'ciaza', 'etykieta': 'Jestem w ciąży'}, {'wartosc': 'urodzenie', 'etykieta': 'Dziecko się urodziło'}],
             wartosc: a1 == null ? null : _wartosc('w1', a1)),
       ]},
      {'id': 'B', 'tytul': 'Ubezpieczenie', 'postep': {'odpowiedziane': 1, 'aktywne': 1},
       'pytania': [
         _pytanie('B1', 'B', 'tytuly', 'Na jakiej podstawie pracujesz?', 'wielokrotny',
             opcje: [{'wartosc': 'umowa_o_prace', 'etykieta': 'Umowa o pracę'}],
             wartosc: _wartosc('w2', ['umowa_o_prace'], wystawca: 'pracodawca', kanal: 'upload', opis: 'Z-3, str. 2',
                 pewnosc: 0.4, doSprawdzenia: true)),
       ]},
      {'id': 'G', 'tytul': 'Poród i dziecko', 'postep': {'odpowiedziane': 0, 'aktywne': a1 == null ? 0 : 1},
       'pytania': [
         _pytanie('G2', 'G', 'data_porodu', 'Data porodu', 'data',
             status: a1 == null ? 'zablokowane' : 'aktywne', czekaNa: a1 == null ? ['A1'] : []),
       ]},
      {'id': 'Q', 'tytul': 'Składki – działalność gospodarcza', 'postep': {'odpowiedziane': 0, 'aktywne': 0},
       'pytania': [
         _pytanie('Q1s', 'Q', 'podstawa_deklarowana_srednia', 'Średnia podstawa składki', 'kwota', status: 'wykluczone'),
       ]},
    ],
  };
}

/// Drzewo dziecka: tylko „Za życiem”.
Map<String, Object?> _drzewoDziecka() => {
      'osoba': {'id': 'o2', 'rola': 'dziecko', 'imie': 'Dziecko'},
      'postep': {'odpowiedziane': 0, 'aktywne': 1},
      'sekcje': [
        {'id': 'G', 'tytul': 'Poród i dziecko', 'postep': {'odpowiedziane': 0, 'aktywne': 1},
         'pytania': [_pytanie('G4', 'G', 'za_zyciem', 'Czy dziecko ma zaświadczenie „Za życiem”?', 'tak_nie')]},
      ],
    };

final fakeSerwer = MockClient((r) async {
  final p = r.url.path;
  wywolania[p] = (wywolania[p] ?? 0) + 1;
  final login = r.headers['Authorization']?.replaceFirst('sim-', '');
  final zalogowany = login != null && _konta.containsKey(login);
  if (p == '/auth/mobywatel/konta') {
    return _json([
      for (final e in _konta.entries) {'login': e.key, ...e.value},
    ]);
  }
  if (p == '/auth/mobywatel') {
    final l = (jsonDecode(r.body) as Map)['login'] as String;
    return _konta.containsKey(l) ? _json(_sesja(l)) : _json({'detail': 'Nie ma takiego konta testowego.'}, 404);
  }
  if (!zalogowany && (p == '/auth/ja' || p.contains('/zrodla/'))) {
    return _json({'detail': 'Sesja wygasła.'}, 401);
  }
  if (p == '/auth/ja') return _json(_sesja(login!));
  if (p == '/sprawy' && r.method == 'POST') return _json(_sprawa());
  if (p == '/sprawy/sprawa1') return _json(_sprawa());
  if (p == '/sprawy/sprawa1/dane') {
    return _json(r.url.queryParameters['osoba'] == 'o2' ? _drzewoDziecka() : _drzewo());
  }
  if (p == '/sprawy/sprawa1/odpowiedzi') {
    for (final o in jsonDecode(r.body) as List) {
      odpowiedzi[(o as Map)['pole'] as String] = o['wartosc'];
    }
    return _json(_zmiana());
  }
  if (p.startsWith('/sprawy/sprawa1/zrodla/') && p.endsWith('/pobierz')) {
    _pobranoZus = true;
    return _json(_zmiana(dodano: 3));
  }
  if (p == '/sprawy/sprawa1/ubezpieczenie') {
    return _pobranoZus
        ? _json(_ubezpieczenie(login ?? 'anna'))
        : _json({'detail': 'Nie mamy jeszcze danych o Twoim ubezpieczeniu. Pobierz je z ZUS.'}, 404);
  }
  if (p == '/sprawy/sprawa1/swiadczenia') {
    return _json([
      {
        'swiadczenie': 'zasilek_macierzynski', 'nazwa': 'Zasiłek macierzyński', 'osoba_id': 'o1',
        'status': 'brak_danych', 'uzasadnienie': ['Uzupełnij dane, aby ustalić prawo do zasiłku.'], 'powody': [],
        'brakujace_pola': [{'pytanie_id': 'B1', 'tresc': 'Na jakiej podstawie pracujesz?', 'gdzie_znalezc': null}],
        'kto_wyplaca': null, 'kto_wyplaca_opis': null, 'podstawa_prawna': ['art. 29 ustawy zasiłkowej'],
        'wersja_parametrow': '2026-01-01',
      },
    ]);
  }
  if (p == '/sprawy/sprawa1/kalkulator') {
    return _json({'detail': 'Aby policzyć zasiłek, podaj datę porodu (pytania G1, G2).'}, 422);
  }
  return _json({'detail': 'Nie znaleziono'}, 404);
});

Future<void> uruchomAplikacje(WidgetTester tester, Size rozmiar) async {
  wywolania.clear();
  odpowiedzi.clear();
  _pobranoZus = false;
  tester.view.physicalSize = rozmiar;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(App(api: (s) => ApiClient(s, klient: fakeSerwer, bazowyUrl: 'http://test')));
  await tester.pumpAndSettle();
}

Future<void> zalogujJako(WidgetTester tester, String imieINazwisko) async {
  await tester.ensureVisible(find.text(imieINazwisko));
  await tester.pumpAndSettle();
  await tester.tap(find.text(imieINazwisko));
  await tester.pumpAndSettle();
}
