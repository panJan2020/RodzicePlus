import 'package:flutter/foundation.dart';

import '../../data/api_client.dart';
import '../../data/models/modele.dart';
import '../../data/repositories/sprawa_repository.dart';
import '../../data/repositories/zus_repository.dart';

/// Ekran „Moje ubezpieczenie” – dane z ZUS (symulacja, FR-02).
class UbezpieczenieViewModel extends ChangeNotifier {
  UbezpieczenieViewModel(this._zus, this._sprawy) {
    zaladuj();
  }

  final ZusRepository _zus;
  final SprawaRepository _sprawy;

  DaneUbezpieczenia? dane;
  bool laduje = false;
  String? blad;

  bool zapisuje = false;
  WynikPobrania? wynikZapisu;
  String? bladZapisu;

  Future<void> zaladuj() async {
    laduje = true;
    blad = null;
    notifyListeners();
    try {
      dane = await _zus.ubezpieczenie();
    } on ApiException catch (e) {
      blad = e.komunikat;
    } finally {
      laduje = false;
      notifyListeners();
    }
  }

  /// Zapisuje dane z ZUS w profilu sprawy, żeby kreator o nie nie pytał.
  Future<void> zapiszWSprawie() async {
    if (zapisuje) return;
    zapisuje = true;
    bladZapisu = null;
    notifyListeners();
    try {
      final id = await _sprawy.biezacaSprawa();
      wynikZapisu = await _zus.pobierzDoSprawy(id);
      dane = wynikZapisu!.ubezpieczenie;
    } on ApiException catch (e) {
      bladZapisu = e.komunikat;
    } finally {
      zapisuje = false;
      notifyListeners();
    }
  }
}
