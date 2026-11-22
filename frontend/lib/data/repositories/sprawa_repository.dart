import '../../core/session.dart';
import '../../shared/formatowanie.dart';
import '../api_client.dart';
import '../models/modele.dart';
import '../models/plik_do_wgrania.dart';

/// Sprawa = profil danych (Sprawa → Osoby → Pola → wartości z różnych źródeł).
/// „Moje dane”, „Moje ubezpieczenie” i kalkulator korzystają z tej samej, bieżącej sprawy.
class SprawaRepository {
  SprawaRepository(this._api, this._sesja);

  final ApiClient _api;
  final SesjaAplikacji _sesja;

  /// Źródła, z których pobieramy dane po kliknięciu „Pobierz z ZUS” (symulacja – docs/api.md 2.4).
  static const zrodlaZus = ['zus_konto', 'zus_platnik', 'ezla'];

  Future<String>? _tworzenie;

  /// Czy bieżąca sprawa już istnieje (nie tworzy jej – do ekranów, które tylko sprawdzają stan).
  bool get maSprawe => _sesja.sprawaId != null;

  /// Id bieżącej sprawy – tworzy nową, jeśli jeszcze jej nie ma (anonimową albo zalogowanej osoby).
  /// Równoległe wywołania (np. logowanie i Start) czekają na to samo utworzenie, więc sprawa jest jedna.
  Future<String> biezacaSprawa() async {
    final istniejaca = _sesja.sprawaId;
    if (istniejaca != null) return istniejaca;
    return _tworzenie ??= _utworzSprawe().whenComplete(() => _tworzenie = null);
  }

  Future<String> _utworzSprawe() async {
    final s = Sprawa.fromJson(await _api.post('/sprawy') as Map<String, dynamic>);
    _sesja.ustawSprawe(s.id);
    return s.id;
  }

  /// Po zalogowaniu: zakłada sprawę i pobiera z (symulowanego) mObywatela dane osobowe. Dane o ubezpieczeniu
  /// z ZUS użytkownik pobiera osobno („Ubezpieczenie”). Błąd nie przerywa logowania – dane można dodać później.
  Future<void> przygotujSprawePoLogowaniu() async {
    try {
      await pobierzZrodlo('mobywatel');
    } on ApiException {
      // sprawa i tak powstała (albo powstanie przy pierwszym użyciu)
    }
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

  // --- Dokumenty (upload) ---------------------------------------------------------------------

  /// Wgrywa pliki PDF; zwraca id zadania w tle (stan: [zadanie]).
  Future<String> wgrajDokumenty(List<PlikDoWgrania> pliki) => _wSprawie((id) async {
        final odp = await _api.wgraj('/sprawy/$id/dokumenty', 'pliki', pliki) as Map<String, dynamic>;
        return odp['zadanie_id'] as String;
      });

  Future<Zadanie> zadanie(String zadanieId) async =>
      Zadanie.fromJson(await _api.get('/zadania/$zadanieId') as Map<String, dynamic>);

  Future<List<Dokument>> dokumenty() => _wSprawie((id) async {
        final lista = await _api.get('/sprawy/$id/dokumenty') as List<dynamic>;
        return [for (final d in lista) Dokument.fromJson(d as Map<String, dynamic>)];
      });

  /// Usuwa dokument razem z wartościami z niego odczytanymi.
  Future<ZmianaDanych> usunDokument(String dokumentId) => _wSprawie(
        (id) async => ZmianaDanych.fromJson(await _api.delete('/sprawy/$id/dokumenty/$dokumentId') as Map<String, dynamic>),
      );

  /// Porównanie wyniku aplikacji z decyzją ZUS; `null`, gdy sprawa nie ma decyzji ZUS (404).
  Future<Porownanie?> porownanie() => _wSprawie((id) async {
        try {
          return Porownanie.fromJson(await _api.get('/sprawy/$id/porownanie') as Map<String, dynamic>);
        } on ApiException catch (e) {
          if (e.kod == 404 && !e.komunikat.contains('sprawy')) return null;
          rethrow;
        }
      });

  /// Wartości odczytane z dokumentów (`kanal: "upload"`) dla wszystkich osób sprawy.
  /// Wartość-część (z której powstała wartość scalona) pomijamy, żeby nie dublować okresów.
  Future<List<OdczytanePole>> odczytanePola() async {
    final s = await sprawa();
    final wynik = <OdczytanePole>[];
    for (final o in s.osoby) {
      final d = await dane(osoba: o.id);
      for (final sekcja in d.sekcje) {
        for (final p in sekcja.pytania) {
          for (final w in p.wartosci) {
            if (w.kanal != 'upload' || w.czescZ != null) continue;
            wynik.add(OdczytanePole(osoba: d.osoba, pytanie: p, wartosc: w, opis: opisWartosciPola(p, w.wartosc)));
          }
        }
      }
    }
    return wynik;
  }
}
