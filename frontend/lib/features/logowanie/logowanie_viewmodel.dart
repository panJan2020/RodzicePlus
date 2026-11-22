import 'package:flutter/foundation.dart';

import '../../data/api_client.dart';
import '../../data/models/modele.dart';
import '../../data/repositories/auth_repository.dart';
import '../../data/repositories/sprawa_repository.dart';

/// Ekran symulowanego logowania mObywatel.
class LogowanieViewModel extends ChangeNotifier {
  LogowanieViewModel(this._repo, this._sprawy) {
    zaladuj();
  }

  final AuthRepository _repo;
  final SprawaRepository _sprawy;
  bool _zniszczony = false;

  List<KontoTestowe> konta = [];
  bool laduje = false;
  String? blad; // błąd ładowania listy kont

  /// Konto wybrane do zalogowania (domyślnie pierwsze z listy).
  String? wybrany;

  void wybierz(String login) {
    wybrany = login;
    notifyListeners();
  }

  /// Login konta, na które właśnie logujemy (pokazujemy przy nim kółko ładowania).
  String? logujeSie;
  String? bladLogowania;

  Future<void> zaladuj() async {
    laduje = true;
    blad = null;
    notifyListeners();
    try {
      konta = await _repo.kontaTestowe();
      if (konta.isNotEmpty && !konta.any((k) => k.login == wybrany)) wybrany = konta.first.login;
    } on ApiException catch (e) {
      blad = e.komunikat;
    } finally {
      laduje = false;
      notifyListeners();
    }
  }

  /// Loguje wybranym kontem, zakłada sprawę z symulowanym źródłem mObywatela i zwraca dane sesji
  /// (albo `null` przy błędzie). Po zalogowaniu router sam przenosi dalej – ekran znika, więc po
  /// każdym oczekiwaniu sprawdzamy, czy ViewModel jeszcze żyje.
  Future<Sesja?> zaloguj() async {
    final login = wybrany;
    if (logujeSie != null || login == null) return null;
    logujeSie = login;
    bladLogowania = null;
    notifyListeners();
    try {
      final sesja = await _repo.zaloguj(login);
      await _sprawy.przygotujSprawePoLogowaniu();
      return sesja;
    } on ApiException catch (e) {
      bladLogowania = e.komunikat;
      return null;
    } finally {
      logujeSie = null;
      if (!_zniszczony) notifyListeners();
    }
  }

  @override
  void dispose() {
    _zniszczony = true;
    super.dispose();
  }
}
