import 'dart:convert';

import 'package:http/http.dart' as http;

import '../core/config.dart';
import '../core/session.dart';

/// Błąd z API z komunikatem gotowym do pokazania użytkownikowi (po polsku).
class ApiException implements Exception {
  const ApiException(this.komunikat, {this.kod});
  final String komunikat;
  final int? kod;

  @override
  String toString() => komunikat;
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

  Future<dynamic> get(String sciezka) => _wyslij(() => _http.get(_uri(sciezka), headers: _naglowki()));

  Future<dynamic> post(String sciezka, [Object? body]) => _wyslij(
        () => _http.post(_uri(sciezka), headers: _naglowki(), body: body == null ? null : jsonEncode(body)),
      );

  Uri _uri(String sciezka) => Uri.parse('$_baza$sciezka');

  Map<String, String> _naglowki() => {
        'Content-Type': 'application/json; charset=utf-8',
        'Accept': 'application/json',
        if (_sesja.token != null) 'Authorization': _sesja.token!,
      };

  Future<dynamic> _wyslij(Future<http.Response> Function() zadanie) async {
    final http.Response r;
    try {
      r = await zadanie();
    } catch (_) {
      throw const ApiException('Nie udało się połączyć z serwerem. Sprawdź internet i spróbuj ponownie.');
    }
    final tresc = r.bodyBytes.isEmpty ? null : jsonDecode(utf8.decode(r.bodyBytes));
    if (r.statusCode >= 200 && r.statusCode < 300) return tresc;

    // Sesja nieważna – wylogowujemy, router przeniesie na ekran logowania.
    if (r.statusCode == 401) _sesja.wyczysc();
    throw ApiException(_komunikat(tresc, r.statusCode), kod: r.statusCode);
  }

  static String _komunikat(dynamic tresc, int kod) {
    final detail = tresc is Map ? tresc['detail'] : null;
    if (detail is String && detail.isNotEmpty) return detail;
    if (detail is List) return 'Niektóre dane mają nieprawidłowy format.'; // walidacja FastAPI (422)
    return 'Wystąpił błąd serwera ($kod). Spróbuj ponownie za chwilę.';
  }
}
