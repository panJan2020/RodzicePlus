import '../api_client.dart';
import '../models/modele.dart';

/// Symulowane systemy ZUS (FR-02; później FR-04, FR-05, FR-06).
class ZusRepository {
  ZusRepository(this._api);

  final ApiClient _api;

  Future<DaneUbezpieczenia> ubezpieczenie() async =>
      DaneUbezpieczenia.fromJson(await _api.get('/zus/ubezpieczenie') as Map<String, dynamic>);

  /// Kopiuje dane z ZUS do profilu sprawy (źródło „zus”). Odpowiedzi użytkownika nie są nadpisywane.
  Future<WynikPobrania> pobierzDoSprawy(String sprawaId) async =>
      WynikPobrania.fromJson(await _api.post('/zus/pobierz-do-sprawy/$sprawaId') as Map<String, dynamic>);
}
