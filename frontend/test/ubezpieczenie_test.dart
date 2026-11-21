// FR-02 – symulowane pobranie z ZUS danych o ubezpieczeniu albo o jego braku.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'fake_serwer.dart';

void main() {
  testWidgets('ubezpieczona: status, okres i zapis do sprawy (komputer)', (tester) async {
    await uruchomAplikacje(tester, const Size(1440, 900));
    await tester.tap(find.text('Ubezpieczenie'));
    await tester.pumpAndSettle();
    await zalogujJako(tester, 'Anna Testowa');

    expect(find.text('Podlegasz ubezpieczeniu chorobowemu (umowa o pracę).'), findsOneWidget);
    expect(find.text('Hurtownia Przykładowa S.A.'), findsOneWidget);
    expect(find.text('01.03.2021 – nadal'), findsOneWidget);
    expect(find.text('Ubezpieczenie chorobowe: obowiązkowe'), findsOneWidget);

    await tester.tap(find.text('Zapisz w mojej sprawie'));
    await tester.pumpAndSettle();
    expect(find.text('Zapisano dane z ZUS w Twojej sprawie.'), findsOneWidget);
    expect(wywolania['/sprawy'], 1);
    expect(wywolania['/zus/pobierz-do-sprawy/sprawa1'], 1);
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
