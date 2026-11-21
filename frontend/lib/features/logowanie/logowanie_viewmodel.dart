import 'package:flutter/foundation.dart';

import '../../data/api_client.dart';
import '../../data/models/modele.dart';
import '../../data/repositories/auth_repository.dart';

/// Ekran symulowanego logowania mObywatel (FR-01).
class LogowanieViewModel extends ChangeNotifier {
  LogowanieViewModel(this._repo) {
    zaladuj();
  }

  final AuthRepository _repo;

  List<KontoTestowe> konta = [];
  bool laduje = false;
  String? blad; // błąd ładowania listy kont

  /// Login konta, na które właśnie logujemy (pokazujemy przy nim kółko ładowania).
  String? logujeSie;
  String? bladLogowania;

  Future<void> zaladuj() async {
    laduje = true;
    blad = null;
    notifyListeners();
    try {
      konta = await _repo.kontaTestowe();
    } on ApiException catch (e) {
      blad = e.komunikat;
    } finally {
      laduje = false;
      notifyListeners();
    }
  }

  /// Zwraca dane sesji albo `null` przy błędzie. Po sukcesie router sam przenosi dalej.
  Future<Sesja?> zaloguj(String login) async {
    if (logujeSie != null) return null;
    logujeSie = login;
    bladLogowania = null;
    notifyListeners();
    try {
      return await _repo.zaloguj(login);
    } on ApiException catch (e) {
      bladLogowania = e.komunikat;
      return null;
    } finally {
      logujeSie = null;
      notifyListeners();
    }
  }
}
