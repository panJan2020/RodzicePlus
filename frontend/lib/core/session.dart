import 'dart:convert';

import 'package:flutter/foundation.dart';

import '../data/models/modele.dart';
import 'magazyn.dart';

/// Stan zalogowania (symulacja mObywatela) i bieżąca sprawa. Jeden obiekt na całą aplikację.
/// Router nasłuchuje zmian i przekierowuje po zalogowaniu / wylogowaniu.
///
/// Sesję i id sprawy zapamiętujemy w [MagazynTrwaly] (w przeglądarce: sessionStorage), żeby odświeżenie
/// strony nie gubiło sprawy. Same dane sprawy są na serwerze.
class SesjaAplikacji extends ChangeNotifier {
  SesjaAplikacji({MagazynTrwaly? magazyn}) : _magazyn = magazyn ?? const MagazynPusty() {
    _przywroc();
  }

  static const _kluczSesji = 'rodziceplus.sesja';
  static const _kluczSprawy = 'rodziceplus.sprawa';

  final MagazynTrwaly _magazyn;
  Sesja? _dane;
  String? _sprawaId;

  Sesja? get dane => _dane;
  String? get token => _dane?.token;
  bool get zalogowany => _dane != null;

  /// Id sprawy (profilu), do której zapisujemy dane z ZUS, kreatora i dokumentów.
  String? get sprawaId => _sprawaId;

  void _przywroc() {
    try {
      final sesja = _magazyn.czytaj(_kluczSesji);
      if (sesja != null) _dane = Sesja.fromJson(jsonDecode(sesja) as Map<String, dynamic>);
      _sprawaId = _magazyn.czytaj(_kluczSprawy);
    } catch (_) {
      _dane = null; // uszkodzony zapis – zaczynamy od zera
      _sprawaId = null;
    }
  }

  void _zapisz() {
    _magazyn.zapisz(_kluczSesji, _dane == null ? null : jsonEncode(_dane!.toJson()));
    _magazyn.zapisz(_kluczSprawy, _sprawaId);
  }

  void ustaw(Sesja sesja) {
    _dane = sesja;
    _sprawaId = null; // nowa osoba = nowa sprawa
    _zapisz();
    notifyListeners();
  }

  void ustawSprawe(String id) {
    _sprawaId = id;
    _zapisz();
    notifyListeners();
  }

  /// Serwer nie zna już tej sprawy (np. po restarcie) – przy następnym użyciu założymy nową.
  void zapomnijSprawe() {
    _sprawaId = null;
    _zapisz();
  }

  void wyczysc() {
    if (_dane == null && _sprawaId == null) return;
    _dane = null;
    _sprawaId = null;
    _zapisz();
    notifyListeners();
  }
}
