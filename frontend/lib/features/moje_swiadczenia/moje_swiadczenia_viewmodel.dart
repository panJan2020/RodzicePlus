import 'package:flutter/foundation.dart';

import '../../data/api_client.dart';
import '../../data/models/modele.dart';
import '../../data/repositories/sprawa_repository.dart';

/// Ekran „Świadczenia”: czy świadczenie przysługuje (4 statusy), za jaki okres, ile i kto wypłaca.
class MojeSwiadczeniaViewModel extends ChangeNotifier {
  MojeSwiadczeniaViewModel(this._sprawy) {
    zaladuj();
  }

  final SprawaRepository _sprawy;

  List<WynikSwiadczenia> wyniki = [];
  bool laduje = false;
  String? blad;

  Future<void> zaladuj() async {
    laduje = true;
    blad = null;
    notifyListeners();
    try {
      wyniki = await _sprawy.swiadczenia();
    } on ApiException catch (e) {
      blad = e.komunikat;
    } finally {
      laduje = false;
      notifyListeners();
    }
  }
}
