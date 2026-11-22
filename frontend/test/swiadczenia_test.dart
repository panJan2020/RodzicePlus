// Ekrany „Świadczenia” i „Kalkulator” na fałszywym serwerze (telefon i komputer).
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'fake_serwer.dart';

void main() {
  for (final (nazwa, rozmiar) in [('telefon', const Size(375, 812)), ('komputer', const Size(1440, 1000))]) {
    testWidgets('$nazwa: świadczenia – status z ikoną, okres, kwota, kto wypłaca, wynik orientacyjny', (tester) async {
      await uruchomAplikacje(tester, rozmiar);
      await tester.tap(find.text('Świadczenia').first);
      await tester.pumpAndSettle();

      expect(find.text('Twoje świadczenia'), findsOneWidget);
      expect(find.text('Przysługuje warunkowo'), findsOneWidget);
      expect(find.byIcon(Icons.schedule), findsWidgets); // status nie tylko kolorem: ikona + tekst
      expect(find.text('Wynik orientacyjny'), findsOneWidget);
      expect(find.textContaining('o ile w dniu porodu nadal będziesz ubezpieczona'), findsOneWidget);
      expect(find.textContaining('075,78 zł brutto'), findsOneWidget); // miesięcznie
      expect(find.textContaining('020,40 zł brutto'), findsOneWidget); // za cały okres
      expect(find.text('10.03.2027 – 27.07.2027 (20 tyg.)'), findsOneWidget);
      expect(find.text('Ubezpieczenie chorobowe w dniu porodu'), findsOneWidget);
      expect(find.textContaining('złóż w kadrach'), findsOneWidget);
      expect(find.text('Wynagrodzenie w kolejnych miesiącach'), findsOneWidget); // do potwierdzenia
      expect(find.text('Brakuje danych'), findsOneWidget);
      expect(tester.takeException(), isNull); // bez przepełnień układu
    });
  }

  testWidgets('kalkulator: okresy, powrót do pracy i ostrzeżenia (komputer)', (tester) async {
    await uruchomAplikacje(tester, const Size(1440, 1000));
    kalkulatorPoliczony = true;
    await tester.tap(find.text('Kalkulator'));
    await tester.pumpAndSettle();

    expect(find.text('Kalkulator zasiłku'), findsOneWidget);
    expect(find.text('Urlop macierzyński'), findsOneWidget);
    expect(find.text('Urlop rodzicielski'), findsWidgets); // okres (i link w stopce)
    expect(find.text('Powrót do pracy'), findsOneWidget);
    expect(find.text('09.07.2027'), findsOneWidget);
    expect(find.text('Wynik orientacyjny'), findsOneWidget);
    expect(find.textContaining('wyłącznie drugiemu rodzicowi'), findsOneWidget);
    expect(find.textContaining('235,86 zł za każdy dzień'), findsOneWidget);
    expect(find.text('Przysługuje warunkowo'), findsNothing); // statusy są na ekranie „Świadczenia”
  });

  testWidgets('kalkulator bez daty porodu pokazuje komunikat z backendu (telefon)', (tester) async {
    await uruchomAplikacje(tester, const Size(375, 812));
    await tester.tap(find.text('Kalkulator'));
    await tester.pumpAndSettle();
    expect(find.textContaining('podaj datę porodu'), findsOneWidget);
    expect(find.text('Przejdź do „Moich danych”'), findsOneWidget);
  });

  testWidgets('telefon: 5 pozycji w dolnym pasku, reszta w „Więcej”', (tester) async {
    await uruchomAplikacje(tester, const Size(360, 800));
    expect(find.byType(NavigationDestination), findsNWidgets(5));
    await tester.tap(find.text('Więcej'));
    await tester.pumpAndSettle();
    expect(find.text('Ubezpieczenie'), findsOneWidget);
    expect(find.text('Moje konto'), findsOneWidget);
  });
}
