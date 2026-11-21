import 'package:flutter/foundation.dart';

import '../../data/api_client.dart';
import '../../data/models/modele.dart';
import '../../data/repositories/auth_repository.dart';

/// Ekran „Moje konto” – dane zalogowanej osoby pobrane z serwera (GET /auth/ja).
class KontoViewModel extends ChangeNotifier {
  KontoViewModel(this._repo) {
    zaladuj();
  }

  final AuthRepository _repo;

  Sesja? dane;
  bool laduje = false;
  String? blad;

  Future<void> zaladuj() async {
    laduje = true;
    blad = null;
    notifyListeners();
    try {
      dane = await _repo.ja();
    } on ApiException catch (e) {
      blad = e.komunikat;
    } finally {
      laduje = false;
      notifyListeners();
    }
  }

  void wyloguj() => _repo.wyloguj();
}
