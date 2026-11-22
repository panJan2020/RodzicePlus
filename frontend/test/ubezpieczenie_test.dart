// „Moje ubezpieczenie”: pobranie danych z ZUS do sprawy i stan ubezpieczenia (albo jego braku).
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'fake_serwer.dart';

void main() {
  testWidgets('ubezpieczona: dane z ZUS pobrane do sprawy, status i okres (komputer)', (tester) async {
    await uruchomAplikacje(tester, const Size(1440, 900));
    await tester.tap(find.text('Ubezpieczenie'));
    await tester.pumpAndSettle();
    await zalogujJako(tester, 'Anna Testowa');

    expect(find.text('Podlegasz ubezpieczeniu chorobowemu (umowa o pracę).'), findsOneWidget);
    expect(find.text('Hurtownia Przykładowa S.A.'), findsOneWidget);
    expect(find.text('01.03.2021 – nadal'), findsOneWidget);
    expect(find.text('Ubezpieczenie chorobowe: obowiązkowe'), findsOneWidget);

    expect(find.textContaining('Dane z ZUS są zapisane w Twojej sprawie'), findsOneWidget);
    expect(wywolania['/sprawy'], 1);
    for (final kod in ['zus_konto', 'zus_platnik', 'ezla']) {
      expect(wywolania['/sprawy/sprawa1/zrodla/$kod/pobierz'], 1, reason: kod);
    }

    await tester.tap(find.text('Pobierz ponownie z ZUS'));
    await tester.pumpAndSettle();
    expect(wywolania['/sprawy/sprawa1/zrodla/zus_konto/pobierz'], 2);
  });

  testWidgets('brak ubezpieczenia: ostrzeżenie i zakończony okres (telefon)', (tester) async {
    await uruchomAplikacje(tester, const Size(375, 800));
    await tester.tap(find.text('Ubezpieczenie'));
    await tester.pumpAndSettle();
    await zalogujJako(tester, 'Katarzyna Przykładowa');

    expect(find.text('Obecnie nie podlegasz ubezpieczeniu chorobowemu.'), findsOneWidget);
    expect(find.bySemanticsLabel('Brak ubezpieczenia'), findsOneWidget);
    await tester.ensureVisible(find.text('zakończony'));
    expect(find.text('01.01.2022 – 31.08.2026'), findsOneWidget);
  });
}
