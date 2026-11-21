import '../../core/session.dart';
import '../api_client.dart';
import '../models/modele.dart';

/// Symulowane logowanie przez mObywatela (FR-01).
class AuthRepository {
  AuthRepository(this._api, this._sesja);

  final ApiClient _api;
  final SesjaAplikacji _sesja;

  Future<List<KontoTestowe>> kontaTestowe() async {
    final lista = await _api.get('/auth/mobywatel/konta') as List<dynamic>;
    return lista.map((e) => KontoTestowe.fromJson(e as Map<String, dynamic>)).toList();
  }

  /// Loguje i zapisuje sesję – router sam przeniesie użytkownika dalej.
  Future<Sesja> zaloguj(String login) async {
    final sesja = Sesja.fromJson(await _api.post('/auth/mobywatel', {'uzytkownik': login}) as Map<String, dynamic>);
    _sesja.ustaw(sesja);
    return sesja;
  }

  /// Dane zalogowanej osoby z serwera (sprawdza też, czy token jest nadal ważny).
  Future<Sesja> ja() async => Sesja.fromJson(await _api.get('/auth/ja') as Map<String, dynamic>);

  void wyloguj() => _sesja.wyczysc();
}
