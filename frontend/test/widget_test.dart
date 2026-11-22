// Symulowane logowanie mObywatel: test całego przepływu z fałszywym serwerem.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'fake_serwer.dart';

void main() {
  testWidgets('logowanie kontem testowym i podgląd konta (komputer)', (tester) async {
    await uruchomAplikacje(tester, const Size(1440, 900));
    expect(find.text('Zaloguj (mObywatel)'), findsWidgets);
    expect(find.textContaining('nie jest oficjalnym serwisem ZUS'), findsOneWidget);

    await tester.tap(find.text('Zaloguj (mObywatel)').first);
    await tester.pumpAndSettle();
    expect(find.text('Logowanie przez mObywatel'), findsOneWidget);

    await zalogujJako(tester, 'Anna Testowa');
    expect(find.text('Dzień dobry, Anna'), findsOneWidget); // router wrócił na start

    await tester.tap(find.text('Moje konto'));
    await tester.pumpAndSettle();
    expect(find.text('Testowa'), findsOneWidget);

    await tester.tap(find.text('Wyloguj'));
    await tester.pumpAndSettle();
    expect(find.text('Logowanie przez mObywatel'), findsOneWidget); // chroniony ekran → logowanie
  });

  testWidgets('chroniony ekran przekierowuje i wraca po zalogowaniu (telefon)', (tester) async {
    await uruchomAplikacje(tester, const Size(375, 800));
    expect(find.byType(NavigationBar), findsOneWidget);

    await tester.tap(find.text('Moje konto'));
    await tester.pumpAndSettle();
    await zalogujJako(tester, 'Anna Testowa');
    expect(find.text('Konto testowe'), findsOneWidget); // wróciliśmy na „Moje konto”
  });
}
