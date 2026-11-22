import 'package:flutter/foundation.dart';

import '../../data/api_client.dart';
import '../../data/models/modele.dart';
import '../../data/repositories/sprawa_repository.dart';

/// Ekran „Kalkulator”: uprawnienia (przysługuje / nie / brak danych) i wyliczone okresy z kwotami.
class KalkulatorViewModel extends ChangeNotifier {
  KalkulatorViewModel(this._sprawy) {
    zaladuj();
  }

  final SprawaRepository _sprawy;

  List<WynikUprawnienia> uprawnienia = [];
  WynikKalkulatora? wynik;
  bool laduje = false;
  String? blad;

  /// Kalkulator nie mógł policzyć kwot (np. brak daty porodu) – komunikat z backendu.
  String? bladKalkulatora;

  Future<void> zaladuj() async {
    laduje = true;
    blad = null;
    notifyListeners();
    try {
      uprawnienia = await _sprawy.uprawnienia();
      try {
        wynik = await _sprawy.kalkulator();
        bladKalkulatora = null;
      } on ApiException catch (e) {
        if (e.kod != 422) rethrow;
        wynik = null;
        bladKalkulatora = e.komunikat;
      }
    } on ApiException catch (e) {
      blad = e.komunikat;
    } finally {
      laduje = false;
      notifyListeners();
    }
  }
}
