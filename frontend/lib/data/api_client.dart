import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import '../core/config.dart';
import '../core/session.dart';
import 'models/plik_do_wgrania.dart';

/// Błąd z API z komunikatem gotowym do pokazania użytkownikowi (po polsku).
class ApiException implements Exception {
  const ApiException(this.komunikat, {this.kod});
  final String komunikat;
  final int? kod;

  @override
  String toString() => komunikat;
}

/// Brak połączenia z serwerem (sieć, serwer śpi, zła konfiguracja adresu).
class BladSieci extends ApiException {
  const BladSieci()
      : super('Nie udało się połączyć z serwerem. Sprawdź internet i spróbuj ponownie.');
}

/// Serwer nie odpowiedział w wyznaczonym czasie.
class BladCzasu extends ApiException {
  const BladCzasu()
      : super('Serwer odpowiada zbyt wolno. Spróbuj ponownie za chwilę.');
}

/// 413 – plik większy niż limit serwera.
class PlikZaDuzy extends ApiException {
  const PlikZaDuzy() : super('Plik jest za duży. Maksymalny rozmiar jednego pliku to 30 MB.', kod: 413);
}

/// 415 – plik nie jest PDF-em.
class NieobslugiwanyFormat extends ApiException {
  const NieobslugiwanyFormat() : super('Na razie przyjmujemy tylko pliki PDF.', kod: 415);
}

/// Jedyne miejsce z HTTP. Dodaje nagłówek Authorization, dekoduje UTF-8,
/// zamienia błędy na [ApiException]. Nie zna logiki biznesowej.
class ApiClient {
  ApiClient(this._sesja, {http.Client? klient, String? bazowyUrl})
      : _http = klient ?? http.Client(),
        _baza = bazowyUrl ?? Config.apiUrl;

  final SesjaAplikacji _sesja;
  final http.Client _http;
  final String _baza;

  /// Zwykłe zapytania mają 30 s; wgrywanie plików dłużej (transfer dużych skanów).
  static const _limitCzasu = Duration(seconds: 30);
  static const _limitCzasuUploadu = Duration(minutes: 3);

  Future<dynamic> get(String sciezka) => _wyslij(() => _http.get(_uri(sciezka), headers: _naglowki()));

  Future<dynamic> delete(String sciezka) => _wyslij(() => _http.delete(_uri(sciezka), headers: _naglowki()));

  /// Wysyła pliki jako multipart (jedno pole `pole` z wieloma plikami). Działa w przeglądarce.
  Future<dynamic> wgraj(String sciezka, String pole, List<PlikDoWgrania> pliki) => _wyslij(() async {
        final zapytanie = http.MultipartRequest('POST', _uri(sciezka))
          ..headers.addAll({
            'Accept': 'application/json',
            if (_sesja.token != null) 'Authorization': _sesja.token!,
          });
        for (final p in pliki) {
          zapytanie.files.add(http.MultipartFile.fromBytes(pole, p.bajty, filename: p.nazwa));
        }
        return http.Response.fromStream(await _http.send(zapytanie));
      }, limit: _limitCzasuUploadu);

  Future<dynamic> post(String sciezka, [Object? body]) => _wyslij(
        () => _http.post(_uri(sciezka), headers: _naglowki(), body: body == null ? null : jsonEncode(body)),
      );

  Uri _uri(String sciezka) => Uri.parse('$_baza$sciezka');

  Map<String, String> _naglowki() => {
        'Content-Type': 'application/json; charset=utf-8',
        'Accept': 'application/json',
        if (_sesja.token != null) 'Authorization': _sesja.token!,
      };

  Future<dynamic> _wyslij(Future<http.Response> Function() zadanie, {Duration limit = _limitCzasu}) async {
    final http.Response r;
    try {
      r = await zadanie().timeout(limit);
    } on TimeoutException {
      throw const BladCzasu();
    } catch (_) {
      throw const BladSieci();
    }
    // Odpowiedź nie-JSON (np. strona błędu z proxy) nie może kończyć się surowym wyjątkiem parsera.
    dynamic tresc;
    try {
      tresc = r.bodyBytes.isEmpty ? null : jsonDecode(utf8.decode(r.bodyBytes));
    } on FormatException {
      tresc = null;
    }
    if (r.statusCode >= 200 && r.statusCode < 300) return tresc;

    // Sesja nieważna – wylogowujemy, router przeniesie na ekran logowania.
    if (r.statusCode == 401) _sesja.wyczysc();
    if (r.statusCode == 413) throw const PlikZaDuzy();
    if (r.statusCode == 415) throw const NieobslugiwanyFormat();
    throw ApiException(_komunikat(tresc, r.statusCode), kod: r.statusCode);
  }

  static String _komunikat(dynamic tresc, int kod) {
    final detail = tresc is Map ? tresc['detail'] : null;
    if (detail is String && detail.isNotEmpty) return detail;
    if (detail is List) return 'Niektóre dane mają nieprawidłowy format.'; // walidacja FastAPI (422)
    return 'Wystąpił błąd serwera ($kod). Spróbuj ponownie za chwilę.';
  }
}
