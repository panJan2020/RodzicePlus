import 'package:flutter/material.dart';

/// Progi szerokości i pozycje menu (CLAUDE.md, sekcja 6).
/// Nie wpisuj liczb szerokości w widokach – bierz je stąd.
enum Uklad { telefon, tablet, komputer }

class Responsive {
  static const double telefonDo = 600;
  static const double komputerOd = 1024;

  /// Maksymalna szerokość całej treści i formularzy/kreatora.
  static const double maxTresc = 960;
  static const double maxFormularz = 640;

  static Uklad ukladDla(double szerokosc) {
    if (szerokosc < telefonDo) return Uklad.telefon;
    if (szerokosc < komputerOd) return Uklad.tablet;
    return Uklad.komputer;
  }

  static Uklad uklad(BuildContext context) => ukladDla(MediaQuery.sizeOf(context).width);

  /// Odstęp od krawędzi ekranu.
  static double margines(BuildContext context) => uklad(context) == Uklad.telefon ? 16 : 24;

  /// Liczba kolumn siatki kafelków: 1 / 2 / 3.
  static int kolumny(double szerokosc) => switch (ukladDla(szerokosc)) {
        Uklad.telefon => 1,
        Uklad.tablet => 2,
        Uklad.komputer => 3,
      };
}

/// Pozycja menu głównego (dolny pasek na telefonie, boczny na tablecie/komputerze).
/// `naTelefonie: false` – na telefonie pozycja jest w „Więcej” (dolny pasek ma najwyżej 5 pozycji).
class PozycjaMenu {
  const PozycjaMenu(this.etykieta, this.ikona, this.ikonaAktywna, this.sciezka, {this.naTelefonie = true});
  final String etykieta;
  final IconData ikona;
  final IconData ikonaAktywna;
  final String sciezka;
  final bool naTelefonie;
}

const pozycjeMenu = <PozycjaMenu>[
  PozycjaMenu('Start', Icons.home_outlined, Icons.home, '/'),
  PozycjaMenu('Ubezpieczenie', Icons.health_and_safety_outlined, Icons.health_and_safety, '/ubezpieczenie',
      naTelefonie: false),
  PozycjaMenu('Moje dane', Icons.fact_check_outlined, Icons.fact_check, '/dane'),
  PozycjaMenu('Dokumenty', Icons.upload_file_outlined, Icons.upload_file, '/dokumenty', naTelefonie: false),
  PozycjaMenu('Świadczenia', Icons.verified_outlined, Icons.verified, '/swiadczenia'),
  PozycjaMenu('Kalkulator', Icons.calculate_outlined, Icons.calculate, '/kalkulator'),
  PozycjaMenu('Moje konto', Icons.person_outline, Icons.person, '/konto', naTelefonie: false),
];

/// Pozycje dolnego paska telefonu (bez „Więcej”) i pozycje schowane w „Więcej”.
final pozycjeTelefonu = [for (final p in pozycjeMenu) if (p.naTelefonie) p];
final pozycjeWiecej = [for (final p in pozycjeMenu) if (!p.naTelefonie) p];

/// Indeks aktywnej pozycji menu dla bieżącej ścieżki.
int indeksMenu(String sciezka) {
  if (sciezka == '/logowanie') return pozycjeMenu.indexWhere((p) => p.sciezka == '/konto');
  final i = pozycjeMenu.indexWhere((p) => p.sciezka != '/' && sciezka.startsWith(p.sciezka));
  return i >= 0 ? i : 0;
}
