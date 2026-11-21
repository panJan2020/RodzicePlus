import 'package:flutter/material.dart';

/// Progi szerokości i pozycje menu (CLAUDE.md, sekcja 6).
/// Nie wpisuj liczb szerokości w widokach – bierz je stąd.
enum Uklad { telefon, tablet, komputer }

class Responsive {
  static const double telefonDo = 600;
  static const double komputerOd = 1024;

  /// Maksymalna szerokość całej treści i formularzy/kreatora.
  static const double maxTresc = 1200;
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
class PozycjaMenu {
  const PozycjaMenu(this.etykieta, this.ikona, this.ikonaAktywna, this.sciezka);
  final String etykieta;
  final IconData ikona;
  final IconData ikonaAktywna;
  final String sciezka;
}

const pozycjeMenu = <PozycjaMenu>[
  PozycjaMenu('Start', Icons.home_outlined, Icons.home, '/'),
  PozycjaMenu('Ubezpieczenie', Icons.health_and_safety_outlined, Icons.health_and_safety, '/ubezpieczenie'),
  PozycjaMenu('Moje konto', Icons.person_outline, Icons.person, '/konto'),
];

/// Indeks aktywnej pozycji menu dla bieżącej ścieżki.
int indeksMenu(String sciezka) {
  if (sciezka == '/logowanie') return pozycjeMenu.indexWhere((p) => p.sciezka == '/konto');
  final i = pozycjeMenu.indexWhere((p) => p.sciezka != '/' && sciezka.startsWith(p.sciezka));
  return i >= 0 ? i : 0;
}
