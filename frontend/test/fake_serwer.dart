// Fałszywy backend do testów widżetów (bez sieci). Kształty odpowiedzi = docs/api.md.
import 'dart:convert';

import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:rodziceplus/app.dart';
import 'package:rodziceplus/data/api_client.dart';

http.Response _json(Object o, [int kod = 200]) =>
    http.Response.bytes(utf8.encode(jsonEncode(o)), kod, headers: {'content-type': 'application/json'});

const _konta = {
  'anna': {'imie': 'Anna', 'nazwisko': 'Testowa', 'opis': 'Pracownica na etacie.'},
  'kasia': {'imie': 'Katarzyna', 'nazwisko': 'Przykładowa', 'opis': 'Umowa o dzieło.'},
};

Map<String, Object?> _sesja(String login) =>
    {'token': 'sim-$login', 'login': login, 'imie': _konta[login]!['imie'], 'nazwisko': _konta[login]!['nazwisko']};

Map<String, Object?> _ubezpieczenie(String login) => login == 'anna'
    ? {
        'stan_na': '2026-11-21',
        'ubezpieczony_chorobowo': true,
        'podsumowanie': 'Podlegasz ubezpieczeniu chorobowemu (umowa o pracę).',
        'wyjasnienia': ['Ubezpieczenie chorobowe trwa nieprzerwanie od 01.03.2021.'],
        'okresy': [
          {
            'tytul': 'umowa_o_prace', 'tytul_opis': 'Umowa o pracę', 'platnik': 'Hurtownia Przykładowa S.A.',
            'platnik_ponad_20': 'ponad_20', 'od': '2021-03-01', 'do': null, 'chorobowe': true,
            'chorobowe_dobrowolne': false, 'aktywny': true,
          },
        ],
        'tytuly': ['umowa_o_prace'],
        'chorobowe_od': '2021-03-01',
        'chorobowe_dobrowolne': false,
        'platnik_ponad_20': 'ponad_20',
      }
    : {
        'stan_na': '2026-11-21',
        'ubezpieczony_chorobowo': false,
        'podsumowanie': 'Obecnie nie podlegasz ubezpieczeniu chorobowemu.',
        'wyjasnienia': ['Ostatnie ubezpieczenie chorobowe skończyło się 31.08.2026.'],
        'okresy': [
          {
            'tytul': 'umowa_o_prace', 'tytul_opis': 'Umowa o pracę', 'platnik': 'Sklep Testowy sp. z o.o.',
            'od': '2022-01-01', 'do': '2026-08-31', 'chorobowe': true, 'chorobowe_dobrowolne': false,
            'aktywny': false,
          },
        ],
        'tytuly': ['dzielo'],
        'chorobowe_od': null,
        'chorobowe_dobrowolne': null,
        'platnik_ponad_20': null,
      };

/// Ile razy wywołano dany endpoint (do sprawdzeń w testach).
final wywolania = <String, int>{};

/// Odpowiedzi zapisane przez POST /sprawy/sprawa1/odpowiedzi (pole → wartość).
final odpowiedzi = <String, Object?>{};

Map<String, Object?> _pytanie(String id, String sekcja, String pole, String tresc, String typ,
        {String status = 'aktywne', List<String> czekaNa = const [], Map<String, Object?>? wartosc,
        List<Map<String, String>> opcje = const [], bool doSprawdzenia = false}) =>
    {
      'id': id, 'sekcja': sekcja, 'pole': pole, 'tresc': tresc, 'typ': typ, 'opcje': opcje,
      'pomoc': null, 'gdzie_znalezc': null, 'status': status, 'czeka_na': czekaNa, 'wartosc': wartosc,
      'odpowiedziane': wartosc != null, 'do_sprawdzenia': doSprawdzenia,
    };

/// Uproszczone drzewo: A1 → G2 (zablokowane, dopóki brak A1), B1 z niepewnego odczytu Z-3,
/// Q1s zawsze wykluczone. Warunki liczy prawdziwy backend – tu tylko stałe stany do testów UI.
Map<String, Object?> _drzewo() {
  final a1 = odpowiedzi['sytuacja'];
  return {
    'osoba': 0, 'rola': 'matka', 'postep': {'odpowiedziane': a1 == null ? 1 : 2, 'aktywne': a1 == null ? 2 : 3},
    'sekcje': [
      {'id': 'A', 'tytul': 'Sytuacja i rola', 'postep': {'odpowiedziane': a1 == null ? 0 : 1, 'aktywne': 1},
       'pytania': [
         _pytanie('A1', 'A', 'sytuacja', 'Jaka jest Twoja sytuacja?', 'wielokrotny',
             opcje: [{'wartosc': 'ciaza', 'etykieta': 'Jestem w ciąży'}, {'wartosc': 'urodzenie', 'etykieta': 'Dziecko się urodziło'}],
             wartosc: a1 == null ? null : {'wartosc': a1, 'zrodlo': 'uzytkownik', 'potwierdzone': true}),
       ]},
      {'id': 'B', 'tytul': 'Ubezpieczenie', 'postep': {'odpowiedziane': 1, 'aktywne': 1},
       'pytania': [
         _pytanie('B1', 'B', 'tytuly', 'Na jakiej podstawie pracujesz?', 'wielokrotny',
             opcje: [{'wartosc': 'umowa_o_prace', 'etykieta': 'Umowa o pracę'}],
             wartosc: {'wartosc': ['umowa_o_prace'], 'zrodlo': 'dokument', 'dokument': 'Z-3', 'strona': 2, 'pewnosc': 0.4},
             doSprawdzenia: true),
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
    final l = (jsonDecode(r.body) as Map)['uzytkownik'] as String;
    return _konta.containsKey(l) ? _json(_sesja(l)) : _json({'detail': 'Nie ma takiego konta testowego.'}, 404);
  }
  if (!zalogowany && (p == '/auth/ja' || p.startsWith('/zus'))) {
    return _json({'detail': 'Sesja wygasła.'}, 401);
  }
  if (p == '/auth/ja') return _json(_sesja(login!));
  if (p == '/zus/ubezpieczenie') return _json(_ubezpieczenie(login!));
  if (p == '/sprawy' && r.method == 'POST') return _json({'id': 'sprawa1', 'osoby': []});
  if (p == '/sprawy/sprawa1/dane') return _json(_drzewo());
  if (p == '/sprawy/sprawa1/odpowiedzi') {
    for (final o in jsonDecode(r.body) as List) {
      odpowiedzi[(o as Map)['pole'] as String] = o['wartosc'];
    }
    return _json({'id': 'sprawa1', 'osoby': []});
  }
  if (p == '/sprawy/sprawa1/uprawnienia') {
    return _json([
      {
        'swiadczenie': 'zasilek_macierzynski', 'status': 'brak_danych',
        'uzasadnienie': ['Uzupełnij dane, aby ustalić prawo do zasiłku.'],
        'podstawa_prawna': ['art. 29 ustawy zasiłkowej'], 'brakujace_pola': ['B1'],
        'brakujace_pytania': [{'id': 'B1', 'tresc': 'Na jakiej podstawie pracujesz?', 'gdzie_znalezc': null}],
        'ostrzezenia': [], 'kto_wyplaca': null,
      },
    ]);
  }
  if (p == '/sprawy/sprawa1/kalkulator') {
    return _json({'detail': 'Aby policzyć zasiłek, podaj datę porodu (pytania G1, G2).'}, 422);
  }
  if (p == '/zus/pobierz-do-sprawy/sprawa1') {
    return _json({
      'uzupelniono': ['tytuly', 'chorobowe_od'],
      'pominieto': [],
      'ubezpieczenie': _ubezpieczenie(login!),
    });
  }
  return _json({'detail': 'Nie znaleziono'}, 404);
});

Future<void> uruchomAplikacje(WidgetTester tester, Size rozmiar) async {
  wywolania.clear();
  odpowiedzi.clear();
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
