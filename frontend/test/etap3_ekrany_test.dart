// Etap 3.2: ViewModele (świadczenia, Start, logowanie), zapamiętanie sesji po odświeżeniu i karta świadczenia.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:rodziceplus/core/magazyn.dart';
import 'package:rodziceplus/core/session.dart';
import 'package:rodziceplus/data/api_client.dart';
import 'package:rodziceplus/data/models/modele.dart';
import 'package:rodziceplus/data/repositories/auth_repository.dart';
import 'package:rodziceplus/data/repositories/sprawa_repository.dart';
import 'package:rodziceplus/features/logowanie/logowanie_viewmodel.dart';
import 'package:rodziceplus/features/moje_swiadczenia/moje_swiadczenia_view.dart';
import 'package:rodziceplus/features/moje_swiadczenia/moje_swiadczenia_viewmodel.dart';
import 'package:rodziceplus/features/start/start_viewmodel.dart';
import 'package:rodziceplus/shared/formatowanie.dart';

import 'fake_serwer.dart';

WynikSwiadczenia _wynik({
  StatusSwiadczenia status = StatusSwiadczenia.warunkowo,
  bool orientacyjny = true,
  KwotaWyniku? kwota,
  List<ZrodloDanych> zrodla = const [],
  List<String> uwagi = const [],
  List<BrakujacePole> braki = const [],
}) =>
    WynikSwiadczenia(
      swiadczenie: 'zasilek_chorobowy_ciaza',
      nazwa: 'Zasiłek chorobowy w ciąży',
      osobaId: 'o1',
      status: status,
      podsumowanie: 'Przysługuje Ci zasiłek chorobowy.',
      orientacyjny: orientacyjny,
      kwota: kwota,
      uwagi: uwagi,
      brakujacePola: braki,
      zrodlaDanych: zrodla,
      okresWynagrodzenia: OkresWyniku(odDnia: DateTime(2026, 2, 18), doDnia: DateTime(2026, 3, 22), dni: 33),
    );

class _FakeSprawy extends SprawaRepository {
  _FakeSprawy(SesjaAplikacji sesja) : super(ApiClient(sesja), sesja);

  List<WynikSwiadczenia> wyniki = [];
  Object? blad;
  bool ma = false;
  int liczbaDokumentow = 0;
  bool przygotowano = false;

  @override
  bool get maSprawe => ma;

  @override
  Future<List<WynikSwiadczenia>> swiadczenia() async {
    if (blad != null) throw blad!;
    return wyniki;
  }

  @override
  Future<Sprawa> sprawa() async => Sprawa(
        id: 's1', nazwa: 'x', zdarzenie: 'urodzenie', osoby: const [],
        liczniki: Liczniki(dokumenty: liczbaDokumentow),
      );

  @override
  Future<void> przygotujSprawePoLogowaniu() async => przygotowano = true;
}

class _FakeAuth extends AuthRepository {
  _FakeAuth(SesjaAplikacji sesja) : super(ApiClient(sesja), sesja);

  Object? blad;
  String? zalogowano;

  @override
  Future<List<KontoTestowe>> kontaTestowe() async => const [
        KontoTestowe(login: 'anna', imie: 'Anna', nazwisko: 'Testowa', opis: ''),
        KontoTestowe(login: 'kasia', imie: 'Katarzyna', nazwisko: 'Przykładowa', opis: ''),
      ];

  @override
  Future<Sesja> zaloguj(String login) async {
    if (blad != null) throw blad!;
    zalogowano = login;
    return const Sesja(token: 'sim-anna', login: 'anna', imie: 'Anna', nazwisko: 'Testowa');
  }
}

void main() {
  test('formaty: daty DD.MM.RRRR w tekście z dokumentu, miesiąc MM.RRRR, kwota 1 771,44 zł', () {
    expect(ladnieDaty('za okres 2025-02-18 do 2025-05-27'), 'za okres 18.02.2025 do 27.05.2025');
    expect(formatujMiesiac('2024-10'), '10.2024');
    expect(formatujKwote('1771.44'), '1 771,44 zł');
  });

  group('MojeSwiadczeniaViewModel', () {
    test('ładuje wyniki', () async {
      final repo = _FakeSprawy(SesjaAplikacji())..wyniki = [_wynik()];
      final vm = MojeSwiadczeniaViewModel(repo);
      await Future<void>.delayed(Duration.zero);
      expect(vm.wyniki, hasLength(1));
      expect(vm.blad, isNull);
      expect(vm.laduje, isFalse);
    });

    test('błąd sieci: komunikat i ponowienie po „Spróbuj ponownie”', () async {
      final repo = _FakeSprawy(SesjaAplikacji())..blad = const BladSieci();
      final vm = MojeSwiadczeniaViewModel(repo);
      await Future<void>.delayed(Duration.zero);
      expect(vm.blad, contains('połączyć'));

      repo
        ..blad = null
        ..wyniki = [_wynik()];
      await vm.zaladuj();
      expect(vm.blad, isNull);
      expect(vm.wyniki, hasLength(1));
    });
  });

  group('StartViewModel', () {
    test('bez sprawy nie pyta serwera i nie aktywuje „Zobacz świadczenia”', () async {
      final vm = StartViewModel(_FakeSprawy(SesjaAplikacji()));
      await Future<void>.delayed(Duration.zero);
      expect(vm.maDane, isFalse);
      expect(vm.laduje, isFalse);
    });

    test('sprawa z dokumentami aktywuje „Zobacz świadczenia”, bez dokumentów – nie', () async {
      final repo = _FakeSprawy(SesjaAplikacji())
        ..ma = true
        ..liczbaDokumentow = 2;
      final vm = StartViewModel(repo);
      await Future<void>.delayed(Duration.zero);
      expect(vm.maDane, isTrue);

      repo.liczbaDokumentow = 0;
      await vm.zaladuj();
      expect(vm.maDane, isFalse);
    });
  });

  group('LogowanieViewModel', () {
    test('domyślnie wybiera pierwsze konto, loguje i zakłada sprawę ze źródłem mObywatela', () async {
      final sesja = SesjaAplikacji();
      final auth = _FakeAuth(sesja);
      final sprawy = _FakeSprawy(sesja);
      final vm = LogowanieViewModel(auth, sprawy);
      await Future<void>.delayed(Duration.zero);
      expect(vm.wybrany, 'anna');

      vm.wybierz('kasia');
      expect(await vm.zaloguj(), isNotNull);
      expect(auth.zalogowano, 'kasia');
      expect(sprawy.przygotowano, isTrue);
    });

    test('błąd logowania: komunikat i brak zakładania sprawy', () async {
      final sesja = SesjaAplikacji();
      final auth = _FakeAuth(sesja)..blad = const ApiException('Nie ma takiego konta testowego.', kod: 404);
      final sprawy = _FakeSprawy(sesja);
      final vm = LogowanieViewModel(auth, sprawy);
      await Future<void>.delayed(Duration.zero);

      expect(await vm.zaloguj(), isNull);
      expect(vm.bladLogowania, 'Nie ma takiego konta testowego.');
      expect(sprawy.przygotowano, isFalse);
    });
  });

  group('SesjaAplikacji – odświeżenie strony', () {
    const sesja = Sesja(token: 'sim-anna', login: 'anna', imie: 'Anna', nazwisko: 'Testowa');

    test('sesja i id sprawy wracają po „odświeżeniu” (nowy obiekt, ten sam magazyn)', () {
      final magazyn = MagazynWPamieci();
      SesjaAplikacji(magazyn: magazyn)
        ..ustaw(sesja)
        ..ustawSprawe('sp7');

      final po = SesjaAplikacji(magazyn: magazyn);
      expect(po.zalogowany, isTrue);
      expect(po.dane!.imieINazwisko, 'Anna Testowa');
      expect(po.sprawaId, 'sp7');

      po.wyczysc();
      expect(SesjaAplikacji(magazyn: magazyn).sprawaId, isNull);
    });

    test('uszkodzony zapis nie wywraca aplikacji', () {
      final magazyn = MagazynWPamieci()..zapisz('rodziceplus.sesja', '{nie json');
      expect(SesjaAplikacji(magazyn: magazyn).zalogowany, isFalse);
    });
  });

  testWidgets('karta świadczenia: status słowem i ikoną, znacznik orientacyjny, brak kwoty z powodem, źródła',
      (tester) async {
    tester.view.physicalSize = const Size(375, 1400);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    final wynik = _wynik(
      uwagi: ['Okresy zwolnień z różnych dokumentów nakładają się.'],
      braki: const [BrakujacePole(pytanieId: 'D1a', tresc: 'Kod zwolnienia lekarskiego')],
      zrodla: const [
        ZrodloDanych(
            pole: 'miesiace', tresc: 'Wynagrodzenie w kolejnych miesiącach', zrodloOpis: 'Z-3, str. 7',
            dokumentId: 'd2', strona: 7),
      ],
    );
    await tester.pumpWidget(
        MaterialApp(home: Scaffold(body: SingleChildScrollView(child: KartaSwiadczenia(wynik: wynik)))));

    expect(find.text('Przysługuje warunkowo'), findsOneWidget); // słowo…
    expect(find.byIcon(Icons.schedule), findsWidgets); // …i ikona, nie tylko kolor
    expect(find.text('Wynik orientacyjny'), findsOneWidget);
    expect(find.textContaining('nie można jeszcze obliczyć – brakuje: Kod zwolnienia lekarskiego'), findsOneWidget);
    expect(find.textContaining('18.02.2026 – 22.03.2026 (33 dni)'), findsOneWidget); // wynagrodzenie płatnika
    expect(find.text('Okresy zwolnień z różnych dokumentów nakładają się.'), findsOneWidget);
    expect(find.text('Czego brakuje i co zrobić'), findsOneWidget);

    await tester.tap(find.text('Skąd te dane?'));
    await tester.pumpAndSettle();
    expect(find.text('Z-3, str. 7'), findsOneWidget);
  });

  testWidgets('karta bez znacznika orientacyjnego, gdy wynik jest pewny', (tester) async {
    await tester.pumpWidget(MaterialApp(
        home: Scaffold(
            body: KartaSwiadczenia(wynik: _wynik(status: StatusSwiadczenia.przysluguje, orientacyjny: false)))));
    expect(find.text('Przysługuje'), findsOneWidget);
    expect(find.text('Wynik orientacyjny'), findsNothing);
  });

  testWidgets('Start → Wgraj dokumenty → Wstecz wraca na Start (telefon)', (tester) async {
    await uruchomAplikacje(tester, const Size(375, 800));
    expect(find.text('Sprawdź, jakie świadczenia Ci przysługują'), findsOneWidget);
    final zobacz = find.widgetWithText(OutlinedButton, 'Zobacz świadczenia');
    expect(tester.widget<OutlinedButton>(zobacz).onPressed, isNull); // brak danych – nieaktywny

    await tester.tap(find.text('Wgraj dokumenty'));
    await tester.pumpAndSettle();
    expect(find.text('Wybierz pliki PDF'), findsOneWidget);

    await tester.tap(find.text('Wstecz'));
    await tester.pumpAndSettle();
    expect(find.text('Sprawdź, jakie świadczenia Ci przysługują'), findsOneWidget);
  });
}
