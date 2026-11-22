/// Modele danych z API. Kształt = docs/api.md (zmieniaj oba pliki w tym samym commicie).
///
/// Kwoty i stawki przychodzą jako tekst (`"1234.56"`, `"0.815"`) – Flutter ich nie przelicza, tylko formatuje.
library;

DateTime? _dataLubNull(Object? v) => v == null ? null : DateTime.parse(v as String);
List<String> _teksty(Object? v) => (v as List? ?? const []).cast<String>();

// ---------------------------------------------------------------------------
// Logowanie (docs/api.md 2.1, 3.1)
// ---------------------------------------------------------------------------

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
  const Sesja({required this.token, required this.login, required this.imie, required this.nazwisko, this.admin = false});

  final String token;
  final String login;
  final String imie;
  final String nazwisko;
  final bool admin;

  String get imieINazwisko => '$imie $nazwisko';

  factory Sesja.fromJson(Map<String, dynamic> j) => Sesja(
        token: j['token'] as String,
        login: j['login'] as String,
        imie: j['imie'] as String,
        nazwisko: j['nazwisko'] as String,
        admin: (j['admin'] as bool?) ?? false,
      );
}

// ---------------------------------------------------------------------------
// Sprawa i osoby (docs/api.md 2.2, 3.1)
// ---------------------------------------------------------------------------

enum RolaOsoby {
  matka('matka'),
  ojciec('ojciec'),
  drugiRodzic('drugi_rodzic'),
  dziecko('dziecko');

  const RolaOsoby(this.json);
  final String json;
  static RolaOsoby zJson(String s) => values.firstWhere((r) => r.json == s);
}

class OsobaSprawy {
  const OsobaSprawy({required this.id, required this.rola, this.imie, this.zalogowana = false});

  final String id;
  final RolaOsoby rola;
  final String? imie;
  final bool zalogowana;

  factory OsobaSprawy.fromJson(Map<String, dynamic> j) => OsobaSprawy(
        id: j['id'] as String,
        rola: RolaOsoby.zJson(j['rola'] as String),
        imie: j['imie'] as String?,
        zalogowana: (j['zalogowana'] as bool?) ?? false,
      );
}

class Liczniki {
  const Liczniki({this.konflikty = 0, this.niespojnosci = 0, this.brakujacePola = 0});

  final int konflikty;
  final int niespojnosci;
  final int brakujacePola;

  factory Liczniki.fromJson(Map<String, dynamic> j) => Liczniki(
        konflikty: (j['konflikty'] as int?) ?? 0,
        niespojnosci: (j['niespojnosci'] as int?) ?? 0,
        brakujacePola: (j['brakujace_pola'] as int?) ?? 0,
      );
}

/// GET /sprawy/{id}, POST /sprawy
class Sprawa {
  const Sprawa({required this.id, required this.nazwa, required this.zdarzenie, required this.osoby, required this.liczniki});

  final String id;
  final String nazwa;
  final String zdarzenie;
  final List<OsobaSprawy> osoby;
  final Liczniki liczniki;

  factory Sprawa.fromJson(Map<String, dynamic> j) => Sprawa(
        id: j['id'] as String,
        nazwa: j['nazwa'] as String,
        zdarzenie: j['zdarzenie'] as String,
        osoby: [for (final o in j['osoby'] as List) OsobaSprawy.fromJson(o as Map<String, dynamic>)],
        liczniki: Liczniki.fromJson(j['liczniki'] as Map<String, dynamic>),
      );
}

/// Odpowiedź po każdej zmianie danych (POST /odpowiedzi, POST /zrodla/{kod}/pobierz).
class ZmianaDanych {
  const ZmianaDanych({
    required this.dodano,
    required this.zmienionoAktywne,
    required this.noweKonflikty,
    required this.liczniki,
    required this.wynikiNieaktualne,
  });

  final int dodano;
  final List<String> zmienionoAktywne;
  final int noweKonflikty;
  final Liczniki liczniki;
  final bool wynikiNieaktualne;

  factory ZmianaDanych.fromJson(Map<String, dynamic> j) => ZmianaDanych(
        dodano: j['dodano'] as int,
        zmienionoAktywne: _teksty(j['zmieniono_aktywne']),
        noweKonflikty: j['nowe_konflikty'] as int,
        liczniki: Liczniki.fromJson(j['liczniki'] as Map<String, dynamic>),
        wynikiNieaktualne: j['wyniki_nieaktualne'] as bool,
      );
}

// ---------------------------------------------------------------------------
// Ubezpieczenie (GET /sprawy/{id}/ubezpieczenie – docs/api.md 3.5)
// ---------------------------------------------------------------------------

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
    this.wymiarEtatu,
    this.zrodloOpis,
  });

  final String tytul;
  final String tytulOpis;
  final String platnik;
  final bool? platnikPonad20;
  final DateTime odDnia;
  final DateTime? doDnia; // null = trwa
  final String? wymiarEtatu; // tekst, np. "1.00"
  final bool chorobowe;
  final bool chorobowoDobrowolne;
  final bool aktywny;
  final String? zrodloOpis;

  factory OkresUbezpieczenia.fromJson(Map<String, dynamic> j) => OkresUbezpieczenia(
        tytul: j['tytul'] as String,
        tytulOpis: j['tytul_opis'] as String,
        platnik: j['platnik'] as String,
        platnikPonad20: j['platnik_ponad_20'] as bool?,
        odDnia: DateTime.parse(j['od'] as String),
        doDnia: _dataLubNull(j['do']),
        wymiarEtatu: j['wymiar_etatu'] as String?,
        chorobowe: j['chorobowe'] as bool,
        chorobowoDobrowolne: (j['chorobowe_dobrowolne'] as bool?) ?? false,
        aktywny: j['aktywny'] as bool,
        zrodloOpis: j['zrodlo_opis'] as String?,
      );
}

/// Teksty przychodzą gotowe z backendu.
class DaneUbezpieczenia {
  const DaneUbezpieczenia({
    required this.stanNa,
    required this.ubezpieczonyChorobowo,
    required this.podsumowanie,
    required this.wyjasnienia,
    required this.okresy,
  });

  final DateTime stanNa;
  final bool ubezpieczonyChorobowo;
  final String podsumowanie;
  final List<String> wyjasnienia;
  final List<OkresUbezpieczenia> okresy;

  factory DaneUbezpieczenia.fromJson(Map<String, dynamic> j) => DaneUbezpieczenia(
        stanNa: DateTime.parse(j['stan_na'] as String),
        ubezpieczonyChorobowo: j['ubezpieczony_chorobowo'] as bool,
        podsumowanie: j['podsumowanie'] as String,
        wyjasnienia: _teksty(j['wyjasnienia']),
        okresy: [for (final o in j['okresy'] as List) OkresUbezpieczenia.fromJson(o as Map<String, dynamic>)],
      );
}

// ---------------------------------------------------------------------------
// Drzewo pytań – „Moje dane” (GET /sprawy/{id}/dane) i kreator (docs/api.md 3.2).
// ---------------------------------------------------------------------------

/// Kto ręczy za informację.
enum Wystawca {
  zus('zus'),
  urzad('urzad'),
  sad('sad'),
  pracodawca('pracodawca'),
  lekarz('lekarz'),
  uzytkownik('uzytkownik'),
  wyliczone('wyliczone');

  const Wystawca(this.json);
  final String json;
  static Wystawca zJson(String s) => values.firstWhere((w) => w.json == s);
}

/// Jedna wartość pola z jednego źródła.
class WartoscPola {
  const WartoscPola({
    required this.id,
    required this.wartosc,
    required this.wystawca,
    required this.kanal,
    required this.zrodloOpis,
    this.dokumentId,
    this.strona,
    this.pewnosc = 1,
    this.doSprawdzenia = false,
    this.aktywna = false,
  });

  final String id;
  final Object? wartosc;
  final Wystawca wystawca;
  final String kanal; // mobywatel | zus_konto | … | upload | kreator | system
  final String zrodloOpis; // gotowy tekst do „Skąd to wiemy”
  final String? dokumentId;
  final int? strona;
  final double pewnosc;
  final bool doSprawdzenia; // niepewny odczyt AI
  final bool aktywna;

  factory WartoscPola.fromJson(Map<String, dynamic> j) => WartoscPola(
        id: j['id'] as String,
        wartosc: j['wartosc'],
        wystawca: Wystawca.zJson(j['wystawca'] as String),
        kanal: j['kanal'] as String,
        zrodloOpis: j['zrodlo_opis'] as String,
        dokumentId: j['dokument_id'] as String?,
        strona: j['strona'] as int?,
        pewnosc: ((j['pewnosc'] as num?) ?? 1).toDouble(),
        doSprawdzenia: (j['do_sprawdzenia'] as bool?) ?? false,
        aktywna: (j['aktywna'] as bool?) ?? false,
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
  okresy('okresy'), // tylko podgląd
  miesiace('miesiace'), // tylko podgląd: wynagrodzenia z Z-3 (O4)
  zasilek('zasilek'); // tylko podgląd: poprzedni zasiłek (O2)

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
    this.rodzaj = 'fakt',
    this.edytowalne = true,
    this.naTytul = false,
    this.klucze = const [],
    this.czekaNa = const [],
    this.wartosci = const [],
    this.aktywnaWartoscId,
    this.wyborAktywnej = 'automatyczny',
    this.konflikt = false,
  });

  final String id;
  final String sekcja;
  final String pole;
  final String tresc;
  final TypPytania typ;
  final List<OpcjaPytania> opcje;
  final String? pomoc;
  final String? gdzieZnalezc;
  final String rodzaj; // fakt | plan | wyliczone
  final bool edytowalne; // false = tylko podgląd (np. e-ZLA)
  final bool naTytul; // wartość = słownik {tytuł: odpowiedź}
  final List<OpcjaPytania> klucze; // tytuły, dla których podajemy odpowiedź (pola „na tytuł”)
  final StatusPytania status;
  final List<String> czekaNa; // ID pytań, na które trzeba odpowiedzieć najpierw
  final List<WartoscPola> wartosci; // wszystkie źródła
  final String? aktywnaWartoscId;
  final String wyborAktywnej; // automatyczny | uzytkownik
  final bool konflikt;

  /// Aktywna wartość (ta, której używają wyliczenia) – w „Moich danych” pokazujemy ją i jej źródło.
  WartoscPola? get wartosc {
    for (final w in wartosci) {
      if (w.id == aktywnaWartoscId) return w;
    }
    return null;
  }

  bool get odpowiedziane => aktywnaWartoscId != null;
  bool get doSprawdzenia => wartosc?.doSprawdzenia ?? false;

  /// Czy użytkownik wpisał już swoją wartość (wtedy można ją wyczyścić).
  bool get maOdpowiedzUzytkownika => wartosci.any((w) => w.kanal == 'kreator');

  factory PytanieDrzewa.fromJson(Map<String, dynamic> j) => PytanieDrzewa(
        id: j['id'] as String,
        sekcja: j['sekcja'] as String,
        pole: j['pole'] as String,
        tresc: j['tresc'] as String,
        typ: TypPytania.zJson(j['typ'] as String),
        opcje: [for (final o in (j['opcje'] as List? ?? [])) OpcjaPytania.fromJson(o as Map<String, dynamic>)],
        pomoc: j['pomoc'] as String?,
        gdzieZnalezc: j['gdzie_znalezc'] as String?,
        rodzaj: (j['rodzaj'] as String?) ?? 'fakt',
        edytowalne: (j['edytowalne'] as bool?) ?? true,
        naTytul: (j['na_tytul'] as bool?) ?? false,
        klucze: [for (final o in (j['klucze'] as List? ?? [])) OpcjaPytania.fromJson(o as Map<String, dynamic>)],
        status: StatusPytania.values.byName(j['status'] as String),
        czekaNa: _teksty(j['czeka_na']),
        wartosci: [for (final w in (j['wartosci'] as List? ?? [])) WartoscPola.fromJson(w as Map<String, dynamic>)],
        aktywnaWartoscId: j['aktywna_wartosc_id'] as String?,
        wyborAktywnej: (j['wybor_aktywnej'] as String?) ?? 'automatyczny',
        konflikt: (j['konflikt'] as bool?) ?? false,
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

class OsobaSkrot {
  const OsobaSkrot({required this.id, required this.rola, this.imie});
  final String id;
  final RolaOsoby rola;
  final String? imie;

  factory OsobaSkrot.fromJson(Map<String, dynamic> j) =>
      OsobaSkrot(id: j['id'] as String, rola: RolaOsoby.zJson(j['rola'] as String), imie: j['imie'] as String?);
}

/// GET /sprawy/{id}/dane
class DaneOsoby {
  const DaneOsoby({required this.osoba, required this.postep, required this.sekcje});
  final OsobaSkrot osoba;
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
        osoba: OsobaSkrot.fromJson(j['osoba'] as Map<String, dynamic>),
        postep: Postep.fromJson(j['postep'] as Map<String, dynamic>),
        sekcje: [for (final s in j['sekcje'] as List) SekcjaDanych.fromJson(s as Map<String, dynamic>)],
      );
}

// ---------------------------------------------------------------------------
// Świadczenia i kalkulator (GET /sprawy/{id}/swiadczenia, /kalkulator – docs/api.md 3.6–3.7).
// ---------------------------------------------------------------------------

enum StatusSwiadczenia {
  przysluguje('przysluguje'),
  warunkowo('warunkowo'),
  niePrzysluguje('nie_przysluguje'),
  brakDanych('brak_danych');

  const StatusSwiadczenia(this.json);
  final String json;
  static StatusSwiadczenia zJson(String s) => values.firstWhere((t) => t.json == s);
}

class BrakujacePole {
  const BrakujacePole({required this.pytanieId, required this.tresc, this.gdzieZnalezc});
  final String pytanieId;
  final String tresc;
  final String? gdzieZnalezc;

  factory BrakujacePole.fromJson(Map<String, dynamic> j) => BrakujacePole(
        pytanieId: j['pytanie_id'] as String,
        tresc: j['tresc'] as String,
        gdzieZnalezc: j['gdzie_znalezc'] as String?,
      );
}

class Powod {
  const Powod({required this.pole, required this.komunikat, this.wartosc});
  final String pole;
  final String? wartosc;
  final String komunikat;

  factory Powod.fromJson(Map<String, dynamic> j) =>
      Powod(pole: j['pole'] as String, wartosc: j['wartosc'] as String?, komunikat: j['komunikat'] as String);
}

class Warunek {
  const Warunek({required this.opis, this.ryzyko});
  final String opis;
  final String? ryzyko; // kod ryzyka, np. brak_ubezpieczenia_w_dniu_porodu

  factory Warunek.fromJson(Map<String, dynamic> j) => Warunek(opis: j['opis'] as String, ryzyko: j['ryzyko'] as String?);
}

class OkresWyniku {
  const OkresWyniku({required this.odDnia, required this.doDnia, required this.tygodnie});
  final DateTime odDnia;
  final DateTime doDnia;
  final int tygodnie;

  factory OkresWyniku.fromJson(Map<String, dynamic> j) => OkresWyniku(
        odDnia: DateTime.parse(j['od'] as String),
        doDnia: DateTime.parse(j['do'] as String),
        tygodnie: j['tygodnie'] as int,
      );
}

/// Kwoty jako tekst z kropką ("1234.56"), zawsze brutto.
class KwotaWyniku {
  const KwotaWyniku({
    required this.miesieczna,
    required this.zaOkres,
    required this.stawka,
    required this.stawkaDzienna,
    required this.podstawaWymiaru,
    this.brutto = true,
  });
  final String miesieczna;
  final String zaOkres;
  final String stawka;
  final String stawkaDzienna;
  final String podstawaWymiaru;
  final bool brutto;

  factory KwotaWyniku.fromJson(Map<String, dynamic> j) => KwotaWyniku(
        miesieczna: j['miesieczna'] as String,
        zaOkres: j['za_okres'] as String,
        stawka: j['stawka'] as String,
        stawkaDzienna: j['stawka_dzienna'] as String,
        podstawaWymiaru: j['podstawa_wymiaru'] as String,
        brutto: j['brutto'] as bool? ?? true,
      );
}

List<BrakujacePole> _pola(Object? lista) =>
    [for (final b in (lista as List? ?? [])) BrakujacePole.fromJson(b as Map<String, dynamic>)];

class WynikSwiadczenia {
  const WynikSwiadczenia({
    required this.swiadczenie,
    required this.nazwa,
    required this.osobaId,
    required this.status,
    this.scenariuszId = 'domyslny',
    this.podsumowanie = '',
    this.okres,
    this.kwota,
    this.uzasadnienie = const [],
    this.powody = const [],
    this.warunki = const [],
    this.podstawaPrawna = const [],
    this.brakujacePola = const [],
    this.coZrobic = const [],
    this.orientacyjny = false,
    this.polaDoPotwierdzenia = const [],
    this.ryzyka = const [],
    this.uwagi = const [],
    this.ktoWyplaca,
    this.ktoWyplacaOpis,
    this.gdzieZlozyc,
    this.wersjaParametrow = '',
  });

  final String swiadczenie;
  final String nazwa;
  final String osobaId;
  final String scenariuszId;
  final StatusSwiadczenia status;
  final String podsumowanie;
  final OkresWyniku? okres; // null przy nie_przysluguje / brak_danych
  final KwotaWyniku? kwota; // null, gdy brakuje danych do kwoty
  final List<String> uzasadnienie;
  final List<Powod> powody;
  final List<Warunek> warunki;
  final List<String> podstawaPrawna;
  final List<BrakujacePole> brakujacePola;
  final List<String> coZrobic;
  final bool orientacyjny;
  final List<BrakujacePole> polaDoPotwierdzenia;
  final List<String> ryzyka;
  final List<String> uwagi;
  final String? ktoWyplaca; // zus | platnik | null (nie wiemy)
  final String? ktoWyplacaOpis;
  final String? gdzieZlozyc;
  final String wersjaParametrow;

  factory WynikSwiadczenia.fromJson(Map<String, dynamic> j) => WynikSwiadczenia(
        swiadczenie: j['swiadczenie'] as String,
        nazwa: j['nazwa'] as String,
        osobaId: j['osoba_id'] as String,
        scenariuszId: j['scenariusz_id'] as String? ?? 'domyslny',
        status: StatusSwiadczenia.zJson(j['status'] as String),
        podsumowanie: j['podsumowanie'] as String? ?? '',
        okres: j['okres'] == null ? null : OkresWyniku.fromJson(j['okres'] as Map<String, dynamic>),
        kwota: j['kwota'] == null ? null : KwotaWyniku.fromJson(j['kwota'] as Map<String, dynamic>),
        uzasadnienie: _teksty(j['uzasadnienie']),
        powody: [for (final p in (j['powody'] as List? ?? [])) Powod.fromJson(p as Map<String, dynamic>)],
        warunki: [for (final w in (j['warunki'] as List? ?? [])) Warunek.fromJson(w as Map<String, dynamic>)],
        podstawaPrawna: _teksty(j['podstawa_prawna']),
        brakujacePola: _pola(j['brakujace_pola']),
        coZrobic: _teksty(j['co_zrobic']),
        orientacyjny: j['orientacyjny'] as bool? ?? false,
        polaDoPotwierdzenia: _pola(j['pola_do_potwierdzenia']),
        ryzyka: _teksty(j['ryzyka']),
        uwagi: _teksty(j['uwagi']),
        ktoWyplaca: j['kto_wyplaca'] as String?,
        ktoWyplacaOpis: j['kto_wyplaca_opis'] as String?,
        gdzieZlozyc: j['gdzie_zlozyc'] as String?,
        wersjaParametrow: j['wersja_parametrow'] as String? ?? '',
      );
}

class OkresZasilku {
  const OkresZasilku({
    required this.rodzaj,
    required this.odDnia,
    required this.doDnia,
    required this.tygodnie,
    required this.stawka,
    required this.kwotaMiesieczna,
    required this.kwotaZaOkres,
    this.stawkaDzienna = '',
    this.osobaId,
    this.uwagi = const [],
  });

  final String rodzaj;
  final String? osobaId; // null – drugi rodzic spoza sprawy
  final DateTime odDnia;
  final DateTime doDnia;
  final int tygodnie;
  final String stawka; // "0.815"
  final String stawkaDzienna; // "235.86"
  final String kwotaMiesieczna; // "1234.56"
  final String kwotaZaOkres;
  final List<String> uwagi;

  factory OkresZasilku.fromJson(Map<String, dynamic> j) => OkresZasilku(
        rodzaj: j['rodzaj'] as String,
        osobaId: j['osoba_id'] as String?,
        odDnia: DateTime.parse(j['od'] as String),
        doDnia: DateTime.parse(j['do'] as String),
        tygodnie: j['tygodnie'] as int,
        stawka: j['stawka'] as String,
        stawkaDzienna: j['stawka_dzienna'] as String? ?? '',
        kwotaMiesieczna: j['kwota_miesieczna'] as String,
        kwotaZaOkres: j['kwota_za_okres'] as String,
        uwagi: _teksty(j['uwagi']),
      );
}

class OsobaKalkulatora {
  const OsobaKalkulatora({required this.osobaId, required this.podstawaWymiaru, required this.suma, this.powrotDoPracy});
  final String osobaId;
  final String podstawaWymiaru;
  final String suma;
  final DateTime? powrotDoPracy;

  factory OsobaKalkulatora.fromJson(Map<String, dynamic> j) => OsobaKalkulatora(
        osobaId: j['osoba_id'] as String,
        podstawaWymiaru: j['podstawa_wymiaru'] as String,
        suma: j['suma'] as String,
        powrotDoPracy: j['powrot_do_pracy'] == null ? null : DateTime.parse(j['powrot_do_pracy'] as String),
      );
}

class WynikKalkulatora {
  const WynikKalkulatora({
    required this.scenariuszId,
    required this.osoby,
    required this.okresy,
    required this.suma,
    required this.wersjaParametrow,
    this.orientacyjny = false,
    this.ostrzezenia = const [],
  });

  final String scenariuszId;
  final List<OsobaKalkulatora> osoby;
  final List<OkresZasilku> okresy;
  final String suma;
  final String wersjaParametrow;
  final bool orientacyjny;
  final List<String> ostrzezenia;

  factory WynikKalkulatora.fromJson(Map<String, dynamic> j) => WynikKalkulatora(
        scenariuszId: j['scenariusz_id'] as String,
        osoby: [for (final o in j['osoby'] as List) OsobaKalkulatora.fromJson(o as Map<String, dynamic>)],
        okresy: [for (final o in j['okresy'] as List) OkresZasilku.fromJson(o as Map<String, dynamic>)],
        suma: j['suma'] as String,
        wersjaParametrow: j['wersja_parametrow'] as String,
        orientacyjny: j['orientacyjny'] as bool? ?? false,
        ostrzezenia: _teksty(j['ostrzezenia']),
      );
}
