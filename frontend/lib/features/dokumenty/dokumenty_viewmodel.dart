import 'package:flutter/foundation.dart';

import '../../data/api_client.dart';
import '../../data/models/modele.dart';
import '../../data/models/plik_do_wgrania.dart';
import '../../data/repositories/sprawa_repository.dart';

/// Ekran „Dokumenty”: wybór plików PDF → wgranie → odczyt w tle (odpytywanie co 3 s) →
/// lista rozpoznanych dokumentów, odczytane dane i porównanie z decyzją ZUS.
class DokumentyViewModel extends ChangeNotifier {
  DokumentyViewModel(this._sprawy, {this.odstepOdpytywania = const Duration(seconds: 3)}) {
    zaladuj();
  }

  /// Limit z backendu (`MAX_UPLOAD_MB`). Serwer sprawdza go jeszcze raz.
  static const maxRozmiarPliku = 30 * 1024 * 1024;

  /// Po tylu nieudanych odpytaniach z rzędu (sieć) przerywamy śledzenie; analiza na serwerze trwa dalej.
  static const _maxBledowOdpytywania = 3;

  final SprawaRepository _sprawy;
  final Duration odstepOdpytywania;
  bool _zniszczony = false;

  // --- wybór plików ---
  final List<PlikDoWgrania> wybrane = [];

  /// Informacja o odrzuconych plikach (nie-PDF, za duże), do pokazania pod listą wybranych.
  String? uwagaOPlikach;

  // --- wgrywanie i analiza ---
  bool wgrywa = false;
  Zadanie? zadanie;
  String? bladWgrania;

  // --- wyniki ---
  bool laduje = false;
  String? blad;
  List<Dokument> dokumenty = [];
  List<OdczytanePole> odczytane = [];
  Porownanie? porownanie;

  /// Pytanie „Jaka jest Twoja sytuacja?”, dopóki użytkownik na nie nie odpowie (null – odpowiedziano).
  PytanieDrzewa? pytanieOSytuacje;
  final Set<Object?> wybraneSytuacje = {};
  bool zapisujeSytuacje = false;
  String? bladSytuacji;

  // --- usuwanie ---
  String? usuwanyId;
  String? bladUsuwania;

  bool get maWynik => dokumenty.isNotEmpty;
  bool get mozeWgrac => wybrane.isNotEmpty && !wgrywa;

  /// Nazwa etapu po polsku (gdy backend nie przysłał własnego komunikatu).
  static String nazwaEtapu(String etap) => switch (etap) {
        'klasyfikacja' => 'Rozpoznajemy dokumenty…',
        'podzial' => 'Dzielimy pliki na dokumenty…',
        'odczyt' => 'Odczytujemy dane z dokumentów…',
        'scalanie' => 'Łączymy odczytane dane…',
        'wyniki' => 'Liczymy wyniki…',
        _ => 'Przyjmujemy pliki…',
      };

  /// Komunikat bieżącego etapu: z backendu („Odczytujemy Z-3 (2 z 4)…”) albo nazwa etapu.
  String get komunikatEtapu {
    final z = zadanie;
    if (z == null) return nazwaEtapu('przyjecie');
    final k = z.komunikat;
    return (k != null && k.isNotEmpty) ? k : nazwaEtapu(z.etap);
  }

  // ---------------------------------------------------------------------------------------------

  void dodajPliki(List<PlikDoWgrania> pliki) {
    final odrzucone = <String>[];
    for (final p in pliki) {
      if (!p.toPdf) {
        odrzucone.add('„${p.nazwa}” nie jest plikiem PDF');
      } else if (p.rozmiar > maxRozmiarPliku) {
        odrzucone.add('„${p.nazwa}” jest większy niż 30 MB');
      } else if (!wybrane.any((w) => w.nazwa == p.nazwa && w.rozmiar == p.rozmiar)) {
        wybrane.add(p);
      }
    }
    uwagaOPlikach = odrzucone.isEmpty ? null : 'Pominięto: ${odrzucone.join('; ')}. Wybierz pliki w formacie PDF.';
    bladWgrania = null;
    notifyListeners();
  }

  void usunWybrany(PlikDoWgrania plik) {
    wybrane.remove(plik);
    notifyListeners();
  }

  /// Wgrywa wybrane pliki i czeka na koniec odczytu. Po zakończeniu (także błędzie odczytu) pokazuje to,
  /// co udało się rozpoznać.
  Future<void> wgraj() async {
    if (!mozeWgrac) return;
    wgrywa = true;
    bladWgrania = null;
    zadanie = null;
    var wgrano = false;
    notifyListeners();
    try {
      final id = await _sprawy.wgrajDokumenty(List.of(wybrane));
      wgrano = true;
      var bledyZRzedu = 0;
      while (!_zniszczony) {
        try {
          final z = await _sprawy.zadanie(id);
          bledyZRzedu = 0;
          zadanie = z;
          notifyListeners();
          if (!z.wToku) {
            if (z.status == 'blad') bladWgrania = z.blad ?? 'Nie udało się odczytać dokumentów. Spróbuj ponownie.';
            wybrane.clear();
            break;
          }
        } on ApiException catch (e) {
          // Pojedyncza chwilowa awaria sieci nie przerywa analizy, która trwa na serwerze.
          if (e is! BladSieci && e is! BladCzasu) rethrow;
          if (++bledyZRzedu >= _maxBledowOdpytywania) rethrow;
        }
        await Future<void>.delayed(odstepOdpytywania);
      }
    } on ApiException catch (e) {
      bladWgrania = e.komunikat; // wybrane pliki zostają – można spróbować jeszcze raz
    } finally {
      wgrywa = false;
      if (!_zniszczony) notifyListeners();
    }
    // Także po błędzie odczytu: część dokumentów mogła się zapisać.
    if (!_zniszczony && wgrano) await zaladuj();
  }

  Future<void> zaladuj() async {
    laduje = true;
    blad = null;
    notifyListeners();
    try {
      dokumenty = await _sprawy.dokumenty();
      odczytane = await _sprawy.odczytanePola();
      porownanie = await _sprawy.porownanie();
      pytanieOSytuacje = dokumenty.isEmpty ? null : await _sprawy.pytanieOSytuacje();
    } on ApiException catch (e) {
      blad = e.komunikat;
    } finally {
      laduje = false;
      if (!_zniszczony) notifyListeners();
    }
  }

  void przelaczSytuacje(Object? wartosc) {
    if (!wybraneSytuacje.remove(wartosc)) wybraneSytuacje.add(wartosc);
    notifyListeners();
  }

  /// Zapisuje odpowiedź na A1 i przelicza wyniki (odświeża też porównanie z decyzją ZUS).
  Future<void> zapiszSytuacje() async {
    if (wybraneSytuacje.isEmpty || zapisujeSytuacje) return;
    zapisujeSytuacje = true;
    bladSytuacji = null;
    notifyListeners();
    try {
      await _sprawy.zapiszOdpowiedz('sytuacja', wybraneSytuacje.toList());
      wybraneSytuacje.clear();
      await zaladuj();
    } on ApiException catch (e) {
      bladSytuacji = e.komunikat;
    } finally {
      zapisujeSytuacje = false;
      if (!_zniszczony) notifyListeners();
    }
  }

  /// Usuwa dokument razem z odczytanymi z niego wartościami i przelicza porównanie.
  Future<void> usun(Dokument dokument) async {
    if (usuwanyId != null) return;
    usuwanyId = dokument.id;
    bladUsuwania = null;
    notifyListeners();
    try {
      await _sprawy.usunDokument(dokument.id);
      usuwanyId = null;
      await zaladuj();
    } on ApiException catch (e) {
      bladUsuwania = e.komunikat;
    } finally {
      usuwanyId = null;
      if (!_zniszczony) notifyListeners();
    }
  }

  @override
  void dispose() {
    _zniszczony = true;
    super.dispose();
  }
}
