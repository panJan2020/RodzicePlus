/// Modele danych z API. Kształt = docs/api.md (zmieniaj oba pliki w tym samym commicie).
library;

/// Konto testowe do symulowanego logowania (GET /auth/mobywatel/konta).
class KontoTestowe {
  const KontoTestowe({required this.login, required this.imie, required this.nazwisko, this.opis = ''});

  final String login;
  final String imie;
  final String nazwisko;
  final String opis;

  String get imieINazwisko => '$imie $nazwisko';

  factory KontoTestowe.fromJson(Map<String, dynamic> j) => KontoTestowe(
        login: j['login'] as String,
        imie: j['imie'] as String,
        nazwisko: j['nazwisko'] as String,
        opis: (j['opis'] as String?) ?? '',
      );
}

/// Wynik logowania (POST /auth/mobywatel, GET /auth/ja).
class Sesja {
  const Sesja({required this.token, required this.login, required this.imie, required this.nazwisko});

  final String token;
  final String login;
  final String imie;
  final String nazwisko;

  String get imieINazwisko => '$imie $nazwisko';

  factory Sesja.fromJson(Map<String, dynamic> j) => Sesja(
        token: j['token'] as String,
        login: j['login'] as String,
        imie: j['imie'] as String,
        nazwisko: j['nazwisko'] as String,
      );
}

DateTime? _dataLubNull(Object? v) => v == null ? null : DateTime.parse(v as String);

/// Jeden okres ubezpieczenia z konta w ZUS (symulacja, FR-02).
class OkresUbezpieczenia {
  const OkresUbezpieczenia({
    required this.tytul,
    required this.tytulOpis,
    required this.platnik,
    required this.odDnia,
    required this.chorobowe,
    required this.chorobowoDobrowolne,
    required this.aktywny,
    this.platnikPonad20,
    this.doDnia,
  });

  final String tytul;
  final String tytulOpis;
  final String platnik;
  final String? platnikPonad20;
  final DateTime odDnia;
  final DateTime? doDnia; // null = trwa
  final bool chorobowe;
  final bool chorobowoDobrowolne;
  final bool aktywny;

  factory OkresUbezpieczenia.fromJson(Map<String, dynamic> j) => OkresUbezpieczenia(
        tytul: j['tytul'] as String,
        tytulOpis: j['tytul_opis'] as String,
        platnik: j['platnik'] as String,
        platnikPonad20: j['platnik_ponad_20'] as String?,
        odDnia: DateTime.parse(j['od'] as String),
        doDnia: _dataLubNull(j['do']),
        chorobowe: j['chorobowe'] as bool,
        chorobowoDobrowolne: (j['chorobowe_dobrowolne'] as bool?) ?? false,
        aktywny: j['aktywny'] as bool,
      );
}

/// Dane o ubezpieczeniu (GET /zus/ubezpieczenie). Teksty przychodzą gotowe z backendu.
class DaneUbezpieczenia {
  const DaneUbezpieczenia({
    required this.stanNa,
    required this.ubezpieczonyChorobowo,
    required this.podsumowanie,
    required this.wyjasnienia,
    required this.okresy,
    required this.tytuly,
    this.chorobowoOd,
    this.chorobowoDobrowolne,
    this.platnikPonad20,
  });

  final DateTime stanNa;
  final bool ubezpieczonyChorobowo;
  final String podsumowanie;
  final List<String> wyjasnienia;
  final List<OkresUbezpieczenia> okresy;
  final List<String> tytuly;
  final DateTime? chorobowoOd;
  final bool? chorobowoDobrowolne;
  final String? platnikPonad20;

  factory DaneUbezpieczenia.fromJson(Map<String, dynamic> j) => DaneUbezpieczenia(
        stanNa: DateTime.parse(j['stan_na'] as String),
        ubezpieczonyChorobowo: j['ubezpieczony_chorobowo'] as bool,
        podsumowanie: j['podsumowanie'] as String,
        wyjasnienia: (j['wyjasnienia'] as List).cast<String>(),
        okresy: (j['okresy'] as List).map((e) => OkresUbezpieczenia.fromJson(e as Map<String, dynamic>)).toList(),
        tytuly: (j['tytuly'] as List).cast<String>(),
        chorobowoOd: _dataLubNull(j['chorobowe_od']),
        chorobowoDobrowolne: j['chorobowe_dobrowolne'] as bool?,
        platnikPonad20: j['platnik_ponad_20'] as String?,
      );
}

/// Wynik POST /zus/pobierz-do-sprawy/{id}.
class WynikPobrania {
  const WynikPobrania({required this.uzupelniono, required this.pominieto, required this.ubezpieczenie});

  final List<String> uzupelniono;
  final List<String> pominieto;
  final DaneUbezpieczenia ubezpieczenie;

  factory WynikPobrania.fromJson(Map<String, dynamic> j) => WynikPobrania(
        uzupelniono: (j['uzupelniono'] as List).cast<String>(),
        pominieto: (j['pominieto'] as List).cast<String>(),
        ubezpieczenie: DaneUbezpieczenia.fromJson(j['ubezpieczenie'] as Map<String, dynamic>),
      );
}
