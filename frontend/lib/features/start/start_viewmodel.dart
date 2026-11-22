import 'package:flutter/foundation.dart';

import '../../data/api_client.dart';
import '../../data/repositories/sprawa_repository.dart';

/// Ekran startowy: czy sprawa ma już dane (wtedy „Zobacz świadczenia” jest aktywne).
///
/// Nie zakłada sprawy na serwerze – sprawdza tylko, jeśli już istnieje (po logowaniu albo po wgraniu dokumentów).
class StartViewModel extends ChangeNotifier {
  StartViewModel(this._sprawy) {
    zaladuj();
  }

  final SprawaRepository _sprawy;
  bool _zniszczony = false;

  bool laduje = false;
  bool maDane = false;
  String? blad;

  Future<void> zaladuj() async {
    if (!_sprawy.maSprawe) {
      maDane = false;
      return;
    }
    laduje = true;
    blad = null;
    notifyListeners();
    try {
      maDane = (await _sprawy.sprawa()).liczniki.dokumenty > 0;
    } on ApiException catch (e) {
      blad = e.komunikat;
      maDane = false;
    } finally {
      laduje = false;
      if (!_zniszczony) notifyListeners();
    }
  }

  @override
  void dispose() {
    _zniszczony = true;
    super.dispose();
  }
}
