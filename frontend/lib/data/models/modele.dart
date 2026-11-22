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

// ---------------------------------------------------------------------------
// Drzewo pytań – zakładka „Dane” (GET /sprawy/{id}/dane) i kreator.
// ---------------------------------------------------------------------------

/// Skąd pochodzi wartość w sprawie.
enum ZrodloWartosci { uzytkownik, zus, dokument, wyliczone }

/// Wartość pola w sprawie (backend: FieldValue).
class WartoscPola {
  const WartoscPola({
    required this.wartosc,
    required this.zrodlo,
    this.dokument,
    this.strona,
    this.pewnosc,
    this.potwierdzone = false,
  });

  final Object? wartosc;
  final ZrodloWartosci zrodlo;
  final String? dokument;
  final int? strona;
  final double? pewnosc;
  final bool potwierdzone;

  factory WartoscPola.fromJson(Map<String, dynamic> j) => WartoscPola(
        wartosc: j['wartosc'],
        zrodlo: ZrodloWartosci.values.byName(j['zrodlo'] as String),
        dokument: j['dokument'] as String?,
        strona: j['strona'] as int?,
        pewnosc: (j['pewnosc'] as num?)?.toDouble(),
        potwierdzone: (j['potwierdzone'] as bool?) ?? false,
      );
}

class OpcjaPytania {
  const OpcjaPytania({required this.wartosc, required this.etykieta});
  final Object? wartosc;
  final String etykieta;

  factory OpcjaPytania.fromJson(Map<String, dynamic> j) =>
      OpcjaPytania(wartosc: j['wartosc'], etykieta: j['etykieta'] as String);
}

/// Stan pytania liczony w backendzie.
enum StatusPytania { aktywne, zablokowane, wykluczone }

/// Rodzaj pola odpowiedzi.
enum TypPytania {
  wybor('wybor'),
  wielokrotny('wielokrotny'),
  takNie('tak_nie'),
  liczba('liczba'),
  kwota('kwota'),
  data('data'),
  okresy('okresy');

  const TypPytania(this.json);
  final String json;
  static TypPytania zJson(String s) => values.firstWhere((t) => t.json == s);
}

class PytanieDrzewa {
  const PytanieDrzewa({
    required this.id,
    required this.sekcja,
    required this.pole,
    required this.tresc,
    required this.typ,
    required this.status,
    this.opcje = const [],
    this.pomoc,
    this.gdzieZnalezc,
    this.czekaNa = const [],
    this.wartosc,
    this.odpowiedziane = false,
    this.doSprawdzenia = false,
  });

  final String id;
  final String sekcja;
  final String pole;
  final String tresc;
  final TypPytania typ;
  final List<OpcjaPytania> opcje;
  final String? pomoc;
  final String? gdzieZnalezc;
  final StatusPytania status;
  final List<String> czekaNa; // ID pytań, na które trzeba odpowiedzieć najpierw
  final WartoscPola? wartosc;
  final bool odpowiedziane;
  final bool doSprawdzenia; // niepewny odczyt z dokumentu

  bool get edytowalne => typ != TypPytania.okresy;

  factory PytanieDrzewa.fromJson(Map<String, dynamic> j) => PytanieDrzewa(
        id: j['id'] as String,
        sekcja: j['sekcja'] as String,
        pole: j['pole'] as String,
        tresc: j['tresc'] as String,
        typ: TypPytania.zJson(j['typ'] as String),
        opcje: [for (final o in (j['opcje'] as List? ?? [])) OpcjaPytania.fromJson(o as Map<String, dynamic>)],
        pomoc: j['pomoc'] as String?,
        gdzieZnalezc: j['gdzie_znalezc'] as String?,
        status: StatusPytania.values.byName(j['status'] as String),
        czekaNa: (j['czeka_na'] as List? ?? []).cast<String>(),
        wartosc: j['wartosc'] == null ? null : WartoscPola.fromJson(j['wartosc'] as Map<String, dynamic>),
        odpowiedziane: (j['odpowiedziane'] as bool?) ?? false,
        doSprawdzenia: (j['do_sprawdzenia'] as bool?) ?? false,
      );
}

class Postep {
  const Postep({required this.odpowiedziane, required this.aktywne});
  final int odpowiedziane;
  final int aktywne;

  factory Postep.fromJson(Map<String, dynamic> j) =>
      Postep(odpowiedziane: j['odpowiedziane'] as int, aktywne: j['aktywne'] as int);
}

class SekcjaDanych {
  const SekcjaDanych({required this.id, required this.tytul, required this.postep, required this.pytania});
  final String id;
  final String tytul;
  final Postep postep;
  final List<PytanieDrzewa> pytania;

  /// Pytania do pokazania (wykluczone są ukryte).
  List<PytanieDrzewa> get widoczne => pytania.where((p) => p.status != StatusPytania.wykluczone).toList();

  factory SekcjaDanych.fromJson(Map<String, dynamic> j) => SekcjaDanych(
        id: j['id'] as String,
        tytul: j['tytul'] as String,
        postep: Postep.fromJson(j['postep'] as Map<String, dynamic>),
        pytania: [for (final p in j['pytania'] as List) PytanieDrzewa.fromJson(p as Map<String, dynamic>)],
      );
}

/// GET /sprawy/{id}/dane
class DaneOsoby {
  const DaneOsoby({required this.osoba, required this.rola, required this.postep, required this.sekcje});
  final int osoba;
  final String rola;
  final Postep postep;
  final List<SekcjaDanych> sekcje;

  /// Sekcje, w których jest co najmniej jedno widoczne pytanie.
  List<SekcjaDanych> get widoczneSekcje => sekcje.where((s) => s.widoczne.isNotEmpty).toList();

  PytanieDrzewa? pytanie(String id) {
    for (final s in sekcje) {
      for (final p in s.pytania) {
        if (p.id == id) return p;
      }
    }
    return null;
  }

  factory DaneOsoby.fromJson(Map<String, dynamic> j) => DaneOsoby(
        osoba: j['osoba'] as int,
        rola: j['rola'] as String,
        postep: Postep.fromJson(j['postep'] as Map<String, dynamic>),
        sekcje: [for (final s in j['sekcje'] as List) SekcjaDanych.fromJson(s as Map<String, dynamic>)],
      );
}

// ---------------------------------------------------------------------------
// Uprawnienia i kalkulator (GET /sprawy/{id}/uprawnienia, /kalkulator).
// ---------------------------------------------------------------------------

enum StatusUprawnienia {
  przysluguje('przysluguje'),
  niePrzysluguje('nie_przysluguje'),
  brakDanych('brak_danych');

  const StatusUprawnienia(this.json);
  final String json;
  static StatusUprawnienia zJson(String s) => values.firstWhere((t) => t.json == s);
}

class BrakujacePytanie {
  const BrakujacePytanie({required this.id, required this.tresc, this.gdzieZnalezc});
  final String id;
  final String tresc;
  final String? gdzieZnalezc;

  factory BrakujacePytanie.fromJson(Map<String, dynamic> j) => BrakujacePytanie(
        id: j['id'] as String,
        tresc: j['tresc'] as String,
        gdzieZnalezc: j['gdzie_znalezc'] as String?,
      );
}

class WynikUprawnienia {
  const WynikUprawnienia({
    required this.swiadczenie,
    required this.status,
    this.uzasadnienie = const [],
    this.podstawaPrawna = const [],
    this.brakujacePola = const [],
    this.brakujacePytania = const [],
    this.ostrzezenia = const [],
    this.ktoWyplaca,
  });

  final String swiadczenie;
  final StatusUprawnienia status;
  final List<String> uzasadnienie;
  final List<String> podstawaPrawna;
  final List<String> brakujacePola; // ID pytań
  final List<BrakujacePytanie> brakujacePytania;
  final List<String> ostrzezenia;
  final String? ktoWyplaca;

  factory WynikUprawnienia.fromJson(Map<String, dynamic> j) => WynikUprawnienia(
        swiadczenie: j['swiadczenie'] as String,
        status: StatusUprawnienia.zJson(j['status'] as String),
        uzasadnienie: (j['uzasadnienie'] as List? ?? []).cast<String>(),
        podstawaPrawna: (j['podstawa_prawna'] as List? ?? []).cast<String>(),
        brakujacePola: (j['brakujace_pola'] as List? ?? []).cast<String>(),
        brakujacePytania: [
          for (final b in (j['brakujace_pytania'] as List? ?? [])) BrakujacePytanie.fromJson(b as Map<String, dynamic>),
        ],
        ostrzezenia: (j['ostrzezenia'] as List? ?? []).cast<String>(),
        ktoWyplaca: j['kto_wyplaca'] as String?,
      );
}

class OkresZasilku {
  const OkresZasilku({
    required this.rodzaj,
    required this.osoba,
    required this.odDnia,
    required this.doDnia,
    required this.stawka,
    required this.kwotaMiesieczna,
    required this.kwotaZaOkres,
    this.uwagi = const [],
  });

  final String rodzaj;
  final String osoba;
  final DateTime odDnia;
  final DateTime doDnia;
  final double stawka;
  final double kwotaMiesieczna;
  final double kwotaZaOkres;
  final List<String> uwagi;

  factory OkresZasilku.fromJson(Map<String, dynamic> j) => OkresZasilku(
        rodzaj: j['rodzaj'] as String,
        osoba: j['osoba'] as String,
        odDnia: DateTime.parse(j['od'] as String),
        doDnia: DateTime.parse(j['do'] as String),
        stawka: (j['stawka'] as num).toDouble(),
        kwotaMiesieczna: (j['kwota_miesieczna'] as num).toDouble(),
        kwotaZaOkres: (j['kwota_za_okres'] as num).toDouble(),
        uwagi: (j['uwagi'] as List? ?? []).cast<String>(),
      );
}

class WynikKalkulatora {
  const WynikKalkulatora({
    required this.podstawaWymiaru,
    required this.okresy,
    required this.suma,
    required this.wersjaParametrow,
    this.ostrzezenia = const [],
  });

  final double podstawaWymiaru;
  final List<OkresZasilku> okresy;
  final double suma;
  final String wersjaParametrow;
  final List<String> ostrzezenia;

  factory WynikKalkulatora.fromJson(Map<String, dynamic> j) => WynikKalkulatora(
        podstawaWymiaru: (j['podstawa_wymiaru'] as num).toDouble(),
        okresy: [for (final o in j['okresy'] as List) OkresZasilku.fromJson(o as Map<String, dynamic>)],
        suma: (j['suma'] as num).toDouble(),
        wersjaParametrow: j['wersja_parametrow'] as String,
        ostrzezenia: (j['ostrzezenia'] as List? ?? []).cast<String>(),
      );
}
