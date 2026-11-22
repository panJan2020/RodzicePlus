import '../../core/session.dart';
import '../api_client.dart';
import '../models/modele.dart';

/// Sprawa = profil danych (Sprawa → Osoby → Pola → wartości z różnych źródeł).
/// „Moje dane”, „Moje ubezpieczenie” i kalkulator korzystają z tej samej, bieżącej sprawy.
class SprawaRepository {
  SprawaRepository(this._api, this._sesja);

  final ApiClient _api;
  final SesjaAplikacji _sesja;

  /// Źródła, z których pobieramy dane po kliknięciu „Pobierz z ZUS” (symulacja – docs/api.md 2.4).
  static const zrodlaZus = ['zus_konto', 'zus_platnik', 'ezla'];

  /// Id bieżącej sprawy – tworzy nową, jeśli jeszcze jej nie ma (anonimową albo zalogowanej osoby).
  Future<String> biezacaSprawa() async {
    final istniejaca = _sesja.sprawaId;
    if (istniejaca != null) return istniejaca;
    final s = Sprawa.fromJson(await _api.post('/sprawy') as Map<String, dynamic>);
    _sesja.ustawSprawe(s.id);
    return s.id;
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

  static String _osoba(String? osoba) => osoba == null ? '' : '?osoba=$osoba';

  Future<Sprawa> sprawa() =>
      _wSprawie((id) async => Sprawa.fromJson(await _api.get('/sprawy/$id') as Map<String, dynamic>));

  /// Wszystkie pytania jednej osoby („Moje dane”). `osoba == null` – wnioskodawca.
  Future<DaneOsoby> dane({String? osoba}) => _wSprawie(
        (id) async => DaneOsoby.fromJson(await _api.get('/sprawy/$id/dane${_osoba(osoba)}') as Map<String, dynamic>),
      );

  /// Zapisuje odpowiedź użytkownika. `wartosc == null` usuwa tylko odpowiedź użytkownika.
  Future<ZmianaDanych> zapiszOdpowiedz(String pole, Object? wartosc, {String? osoba}) => _wSprawie(
        (id) async => ZmianaDanych.fromJson(await _api.post('/sprawy/$id/odpowiedzi', [
          {'osoba': osoba, 'pole': pole, 'wartosc': wartosc},
        ]) as Map<String, dynamic>),
      );

  /// Pobiera dane z jednego źródła (symulacja). Wymaga zalogowania.
  Future<ZmianaDanych> pobierzZrodlo(String kod) => _wSprawie(
        (id) async => ZmianaDanych.fromJson(await _api.post('/sprawy/$id/zrodla/$kod/pobierz') as Map<String, dynamic>),
      );

  /// „Pobierz z ZUS”: konto ubezpieczonego, dane płatnika, e-ZLA. Zwraca wynik ostatniego pobrania.
  Future<ZmianaDanych> pobierzZZus() async {
    ZmianaDanych? ostatnia;
    var dodano = 0;
    for (final kod in zrodlaZus) {
      ostatnia = await pobierzZrodlo(kod);
      dodano += ostatnia.dodano;
    }
    return ZmianaDanych(
      dodano: dodano,
      zmienionoAktywne: ostatnia!.zmienionoAktywne,
      noweKonflikty: ostatnia.noweKonflikty,
      liczniki: ostatnia.liczniki,
      wynikiNieaktualne: ostatnia.wynikiNieaktualne,
    );
  }

  /// Stan ubezpieczenia z danych sprawy. `404`, gdy dane z ZUS nie zostały jeszcze pobrane.
  Future<DaneUbezpieczenia> ubezpieczenie() => _wSprawie(
        (id) async => DaneUbezpieczenia.fromJson(await _api.get('/sprawy/$id/ubezpieczenie') as Map<String, dynamic>),
      );

  Future<List<WynikSwiadczenia>> swiadczenia() => _wSprawie((id) async {
        final lista = await _api.get('/sprawy/$id/swiadczenia') as List<dynamic>;
        return [for (final w in lista) WynikSwiadczenia.fromJson(w as Map<String, dynamic>)];
      });

  /// Wynik kalkulatora. Rzuca [ApiException] z kodem 422 i komunikatem, gdy brakuje danych.
  Future<WynikKalkulatora> kalkulator() => _wSprawie(
        (id) async => WynikKalkulatora.fromJson(await _api.get('/sprawy/$id/kalkulator') as Map<String, dynamic>),
      );
}
