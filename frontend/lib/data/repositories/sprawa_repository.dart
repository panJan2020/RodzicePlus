import '../../core/session.dart';
import '../api_client.dart';

/// Sprawa = profil danych użytkownika (Sprawa → Osoba → pola). Rozbudowa w FR-03 (kreator).
class SprawaRepository {
  SprawaRepository(this._api, this._sesja);

  final ApiClient _api;
  final SesjaAplikacji _sesja;

  /// Id bieżącej sprawy – tworzy nową, jeśli jeszcze jej nie ma.
  Future<String> biezacaSprawa() async {
    final istniejaca = _sesja.sprawaId;
    if (istniejaca != null) return istniejaca;
    final s = await _api.post('/sprawy') as Map<String, dynamic>;
    final id = s['id'] as String;
    _sesja.ustawSprawe(id);
    return id;
  }
}
