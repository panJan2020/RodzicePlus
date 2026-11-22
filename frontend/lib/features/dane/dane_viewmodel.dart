import 'package:flutter/foundation.dart';

import '../../data/api_client.dart';
import '../../data/models/modele.dart';
import '../../data/repositories/sprawa_repository.dart';
import '../../data/repositories/zus_repository.dart';

/// Zakładka „Moje dane” – całe drzewo pytań do przeglądu i edycji.
/// Stany pytań (aktywne / zablokowane / wykluczone) liczy backend; tu trzymamy tylko stan ekranu.
class DaneViewModel extends ChangeNotifier {
  DaneViewModel(this._sprawy, this._zus, {String? pytanie}) {
    zaladuj(pokaz: pytanie);
  }

  final SprawaRepository _sprawy;
  final ZusRepository _zus;

  DaneOsoby? dane;
  bool laduje = false;
  String? blad;

  /// Komputer: sekcja pokazana po prawej.
  String? wybranaSekcja;

  /// Telefon: rozwinięte karty sekcji (akordeon).
  final Set<String> rozwiniete = {};

  /// Pytanie wyróżnione ramką (np. z linku `/dane?pytanie=B5` albo „Odpowiedz najpierw na…”).
  String? wyroznione;

  /// Pytanie, do którego widok ma przewinąć po najbliższym rysowaniu (potem [przewinieto]).
  String? doPrzewiniecia;

  /// ID pytania, którego odpowiedź właśnie zapisujemy.
  String? zapisuje;
  String? bladZapisu;

  bool pobieraZus = false;
  String? komunikat;

  List<SekcjaDanych> get sekcje => dane?.widoczneSekcje ?? const [];

  SekcjaDanych? get sekcjaWybrana {
    for (final s in sekcje) {
      if (s.id == wybranaSekcja) return s;
    }
    return sekcje.isEmpty ? null : sekcje.first;
  }

  Future<void> zaladuj({String? pokaz}) async {
    laduje = dane == null;
    blad = null;
    notifyListeners();
    try {
      dane = await _sprawy.dane();
      _poprawWybor();
      if (pokaz != null) this.pokaz(pokaz, powiadom: false);
    } on ApiException catch (e) {
      blad = e.komunikat;
    } finally {
      laduje = false;
      notifyListeners();
    }
  }

  /// Rozwija sekcję pytania, wyróżnia je i prosi widok o przewinięcie.
  void pokaz(String id, {bool powiadom = true}) {
    final p = dane?.pytanie(id);
    if (p == null || p.status == StatusPytania.wykluczone) return;
    wybranaSekcja = p.sekcja;
    rozwiniete.add(p.sekcja);
    wyroznione = id;
    doPrzewiniecia = id;
    if (powiadom) notifyListeners();
  }

  void przewinieto() => doPrzewiniecia = null;

  void wybierzSekcje(String id) {
    wybranaSekcja = id;
    notifyListeners();
  }

  void przelaczSekcje(String id) {
    rozwiniete.contains(id) ? rozwiniete.remove(id) : rozwiniete.add(id);
    notifyListeners();
  }

  /// Zapisuje odpowiedź i odświeża drzewo – mogą pojawić się albo zniknąć pytania zależne.
  Future<void> zapisz(PytanieDrzewa p, Object? wartosc) async {
    zapisuje = p.id;
    bladZapisu = null;
    komunikat = null;
    notifyListeners();
    try {
      await _sprawy.zapiszOdpowiedz(p.pole, wartosc);
      dane = await _sprawy.dane();
      _poprawWybor();
      wyroznione = p.id;
    } on ApiException catch (e) {
      bladZapisu = e.komunikat;
    } finally {
      zapisuje = null;
      notifyListeners();
    }
  }

  /// Uzupełnia sprawę danymi z ZUS (tylko po zalogowaniu). Odpowiedzi użytkownika zostają.
  Future<void> pobierzZZus() async {
    pobieraZus = true;
    komunikat = null;
    bladZapisu = null;
    notifyListeners();
    try {
      final id = await _sprawy.biezacaSprawa();
      await _zus.pobierzDoSprawy(id);
      dane = await _sprawy.dane();
      _poprawWybor();
      komunikat = 'Uzupełniliśmy dane z ZUS. Twoje wcześniejsze odpowiedzi zostały bez zmian.';
    } on ApiException catch (e) {
      bladZapisu = e.komunikat;
    } finally {
      pobieraZus = false;
      notifyListeners();
    }
  }

  /// Po odświeżeniu wybrana sekcja mogła zniknąć (wszystkie pytania wykluczone).
  void _poprawWybor() {
    if (!sekcje.any((s) => s.id == wybranaSekcja)) {
      wybranaSekcja = sekcje.isEmpty ? null : sekcje.first.id;
    }
  }
}
