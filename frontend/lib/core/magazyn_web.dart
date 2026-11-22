import 'package:web/web.dart' as web;

import 'magazyn.dart';

MagazynTrwaly magazynPrzegladarki() => _MagazynSessionStorage();

class _MagazynSessionStorage implements MagazynTrwaly {
  @override
  String? czytaj(String klucz) {
    try {
      return web.window.sessionStorage.getItem(klucz);
    } catch (_) {
      return null;
    }
  }

  @override
  void zapisz(String klucz, String? wartosc) {
    try {
      if (wartosc == null) {
        web.window.sessionStorage.removeItem(klucz);
      } else {
        web.window.sessionStorage.setItem(klucz, wartosc);
      }
    } catch (_) {
      // Storage zablokowany – działamy bez zapamiętywania.
    }
  }
}
