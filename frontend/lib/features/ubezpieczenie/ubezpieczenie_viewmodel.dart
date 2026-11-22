import 'package:flutter/foundation.dart';

import '../../data/api_client.dart';
import '../../data/models/modele.dart';
import '../../data/repositories/sprawa_repository.dart';

/// Ekran „Moje ubezpieczenie” – stan ubezpieczenia z danych sprawy (źródło: konto w ZUS, symulacja).
///
/// Przy pierwszym wejściu sprawa nie ma jeszcze danych z ZUS – wtedy pobieramy je automatycznie
/// (konto ubezpieczonego, dane płatnika, e-ZLA) i zapisujemy w sprawie.
class UbezpieczenieViewModel extends ChangeNotifier {
  UbezpieczenieViewModel(this._sprawy) {
    zaladuj();
  }

  final SprawaRepository _sprawy;

  DaneUbezpieczenia? dane;
  bool laduje = false;
  String? blad;

  /// Ostatnie pobranie z ZUS w tej wizycie (null – dane były już w sprawie).
  ZmianaDanych? pobrano;
  bool pobiera = false;
  String? bladPobrania;

  Future<void> zaladuj() async {
    laduje = true;
    blad = null;
    notifyListeners();
    try {
      try {
        dane = await _sprawy.ubezpieczenie();
      } on ApiException catch (e) {
        if (e.kod != 404) rethrow;
        pobrano = await _sprawy.pobierzZZus();
        dane = await _sprawy.ubezpieczenie();
      }
    } on ApiException catch (e) {
      blad = e.komunikat;
    } finally {
      laduje = false;
      notifyListeners();
    }
  }

  /// Ponowne pobranie danych z ZUS (np. po zmianie umowy). Wartości z innych źródeł zostają.
  Future<void> pobierzPonownie() async {
    if (pobiera) return;
    pobiera = true;
    bladPobrania = null;
    notifyListeners();
    try {
      pobrano = await _sprawy.pobierzZZus();
      dane = await _sprawy.ubezpieczenie();
    } on ApiException catch (e) {
      bladPobrania = e.komunikat;
    } finally {
      pobiera = false;
      notifyListeners();
    }
  }
}
