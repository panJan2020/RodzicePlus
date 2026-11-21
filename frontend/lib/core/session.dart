import 'package:flutter/foundation.dart';

import '../data/models/modele.dart';

/// Stan zalogowania (symulacja mObywatela, FR-01) i bieżąca sprawa. Jeden obiekt na całą aplikację.
/// Router nasłuchuje zmian i przekierowuje po zalogowaniu / wylogowaniu.
///
/// Sesja jest trzymana w pamięci – odświeżenie strony wylogowuje.
class SesjaAplikacji extends ChangeNotifier {
  Sesja? _dane;
  String? _sprawaId;

  Sesja? get dane => _dane;
  String? get token => _dane?.token;
  bool get zalogowany => _dane != null;

  /// Id sprawy (profilu), do której zapisujemy dane z ZUS, kreatora i dokumentów.
  String? get sprawaId => _sprawaId;

  void ustaw(Sesja sesja) {
    _dane = sesja;
    _sprawaId = null; // nowa osoba = nowa sprawa
    notifyListeners();
  }

  void ustawSprawe(String id) {
    _sprawaId = id;
    notifyListeners();
  }

  void wyczysc() {
    if (_dane == null && _sprawaId == null) return;
    _dane = null;
    _sprawaId = null;
    notifyListeners();
  }
}
