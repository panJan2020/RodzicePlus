import '../../core/session.dart';
import '../api_client.dart';
import '../models/modele.dart';

/// Sprawa = profil danych użytkownika (Sprawa → Osoba → pola).
/// Zakładka „Dane”, kreator, uprawnienia i kalkulator korzystają z tej samej sprawy.
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

  /// Wykonuje zapytanie dla bieżącej sprawy. Gdy serwer jej nie zna (np. restart darmowego
  /// hostingu – sprawy są w pamięci), zakłada nową i próbuje jeszcze raz.
  Future<T> _wSprawie<T>(Future<T> Function(String id) zapytanie) async {
    final id = await biezacaSprawa();
    try {
      return await zapytanie(id);
    } on ApiException catch (e) {
      if (e.kod != 404 || !e.komunikat.contains('sprawy')) rethrow;
      _sesja.zapomnijSprawe();
      return zapytanie(await biezacaSprawa());
    }
  }

  /// Całe drzewo pytań jednej osoby (zakładka „Dane”).
  Future<DaneOsoby> dane({int osoba = 0}) => _wSprawie(
        (id) async => DaneOsoby.fromJson(await _api.get('/sprawy/$id/dane?osoba=$osoba') as Map<String, dynamic>),
      );

  /// Zapisuje odpowiedź użytkownika. `wartosc == null` czyści odpowiedź.
  Future<void> zapiszOdpowiedz(String pole, Object? wartosc, {int osoba = 0}) => _wSprawie(
        (id) => _api.post('/sprawy/$id/odpowiedzi', [
          {'pole': pole, 'wartosc': wartosc, 'osoba': osoba},
        ]),
      );

  Future<List<WynikUprawnienia>> uprawnienia({int osoba = 0}) => _wSprawie((id) async {
        final lista = await _api.get('/sprawy/$id/uprawnienia?osoba=$osoba') as List<dynamic>;
        return [for (final w in lista) WynikUprawnienia.fromJson(w as Map<String, dynamic>)];
      });

  /// Wynik kalkulatora. Rzuca [ApiException] z kodem 422 i komunikatem, gdy brakuje danych.
  Future<WynikKalkulatora> kalkulator({int osoba = 0}) => _wSprawie(
        (id) async =>
            WynikKalkulatora.fromJson(await _api.get('/sprawy/$id/kalkulator?osoba=$osoba') as Map<String, dynamic>),
      );
}
