// FR-03 – zakładka „Moje dane”: drzewo pytań, źródła wartości, edycja, głęboki link z kalkulatora.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'fake_serwer.dart';

Future<void> _otworzDane(WidgetTester tester) async {
  await tester.tap(find.text('Moje dane').first);
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('komputer: sekcje po lewej, stany pytań i źródła', (tester) async {
    await uruchomAplikacje(tester, const Size(1440, 1000));
    await _otworzDane(tester);

    // Sekcja z samymi wykluczonymi pytaniami jest ukryta.
    expect(find.text('Sytuacja i rola'), findsWidgets);
    expect(find.text('Składki – działalność gospodarcza'), findsNothing);
    expect(find.text('0/1'), findsOneWidget); // licznik sekcji A

    // Sekcja B: niepewny odczyt z dokumentu z ostrzeżeniem.
    await tester.tap(find.text('Ubezpieczenie').last);
    await tester.pumpAndSettle();
    expect(find.text('Z dokumentu Z-3, str. 2'), findsOneWidget);
    expect(find.textContaining('odczyt z dokumentu jest niepewny'), findsOneWidget);
    expect(find.text('Sprawdź i popraw'), findsOneWidget);

    // Sekcja G: pytanie zablokowane z podpowiedzią → klik przenosi do A1.
    await tester.tap(find.text('Poród i dziecko'));
    await tester.pumpAndSettle();
    expect(find.text('Odpowiedz najpierw na:'), findsOneWidget);
    await tester.tap(find.text('A1 – Jaka jest Twoja sytuacja?'));
    await tester.pumpAndSettle();
    expect(find.text('Odpowiedz'), findsOneWidget); // widać A1 bez odpowiedzi
  });

  testWidgets('edycja odpowiedzi odświeża drzewo (odblokowuje pytanie zależne)', (tester) async {
    await uruchomAplikacje(tester, const Size(1440, 1000));
    await _otworzDane(tester);

    await tester.tap(find.text('Odpowiedz'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Jestem w ciąży'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Zapisz'));
    await tester.pumpAndSettle();

    expect(odpowiedzi['sytuacja'], ['ciaza']);
    expect(find.text('Twoja odpowiedź'), findsOneWidget);
    expect(find.text('1/1'), findsWidgets);

    await tester.tap(find.text('Poród i dziecko'));
    await tester.pumpAndSettle();
    expect(find.text('Odpowiedz najpierw na:'), findsNothing); // G2 już aktywne
  });

  testWidgets('telefon: akordeon i „Uzupełnij” z kalkulatora otwiera właściwe pytanie', (tester) async {
    await uruchomAplikacje(tester, const Size(375, 812));
    await tester.tap(find.text('Kalkulator'));
    await tester.pumpAndSettle();

    expect(find.text('Brakuje danych'), findsOneWidget);
    expect(find.text('Na jakiej podstawie pracujesz? (B1)'), findsOneWidget);
    expect(find.textContaining('podaj datę porodu'), findsOneWidget); // 422 z kalkulatora

    await tester.ensureVisible(find.text('Uzupełnij'));
    await tester.tap(find.text('Uzupełnij'));
    await tester.pumpAndSettle();

    // /dane?pytanie=B1 → sekcja B rozwinięta, pytanie widoczne; inne sekcje zwinięte.
    expect(find.text('Na jakiej podstawie pracujesz?'), findsOneWidget);
    expect(find.text('Jaka jest Twoja sytuacja?'), findsNothing);
    expect(tester.getTopLeft(find.text('Na jakiej podstawie pracujesz?')).dy, lessThan(812));
  });
}
