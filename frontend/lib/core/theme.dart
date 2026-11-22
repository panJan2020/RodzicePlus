import 'package:flutter/material.dart';

/// Paleta inspirowana zus.pl (CLAUDE.md, sekcja 7). Jedyne miejsce z kolorami w aplikacji.
class Kolory {
  static const primary = Color(0xFF00843D); // zieleń – przyciski, aktywne menu, „przysługuje”
  static const primaryDark = Color(0xFF006B31); // hover / pressed
  static const primaryLight = Color(0xFFE6F3EC); // tło wyróżnionych sekcji
  static const secondary = Color(0xFF1B365D); // granat – nagłówki, stopka
  static const tlo = Color(0xFFF5F7F6); // tło strony pod kartami
  static const powierzchnia = Color(0xFFFFFFFF); // karty, formularze
  static const tekst = Color(0xFF1A1A1A);
  static const tekstDrugorzedny = Color(0xFF4A4A4A);
  static const ramka = Color(0xFFDADDDC);
  static const blad = Color(0xFFC8102E); // „nie przysługuje”
  static const bladTlo = Color(0xFFFDECEE);
  static const ostrzezenie = Color(0xFF9A4F00); // „brak danych”, do sprawdzenia
  static const ostrzezenieTlo = Color(0xFFFFF4E5);
  static const warunkowoTlo = Color(0xFFE8EEF5); // „warunkowo” (granat na jasnym tle), konflikt
}

const _zaokraglenie = BorderRadius.all(Radius.circular(6));

ThemeData zbudujMotyw() {
  final schemat = ColorScheme.fromSeed(seedColor: Kolory.primary).copyWith(
    primary: Kolory.primary,
    onPrimary: Colors.white,
    primaryContainer: Kolory.primaryLight,
    onPrimaryContainer: Kolory.primaryDark,
    secondary: Kolory.secondary,
    onSecondary: Colors.white,
    error: Kolory.blad,
    surface: Kolory.powierzchnia,
    onSurface: Kolory.tekst,
    onSurfaceVariant: Kolory.tekstDrugorzedny,
    outline: Kolory.ramka,
    outlineVariant: Kolory.ramka,
  );

  const tekst = TextTheme(
    // H1 – tytuł ekranu (jeden na ekran)
    headlineMedium: TextStyle(fontSize: 28, fontWeight: FontWeight.w700, color: Kolory.secondary, height: 1.25),
    // H2 – sekcja
    titleLarge: TextStyle(fontSize: 20, fontWeight: FontWeight.w600, color: Kolory.secondary),
    titleMedium: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: Kolory.tekst),
    bodyLarge: TextStyle(fontSize: 16, color: Kolory.tekst, height: 1.5),
    bodyMedium: TextStyle(fontSize: 14, color: Kolory.tekstDrugorzedny, height: 1.45),
    labelLarge: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
  );

  const rozmiarPrzycisku = Size(48, 48);

  return ThemeData(
    useMaterial3: true,
    colorScheme: schemat,
    scaffoldBackgroundColor: Kolory.tlo,
    textTheme: tekst,
    appBarTheme: const AppBarTheme(
      backgroundColor: Kolory.powierzchnia,
      foregroundColor: Kolory.secondary,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      scrolledUnderElevation: 1,
      titleTextStyle: TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: Kolory.secondary),
    ),
    cardTheme: const CardThemeData(
      color: Kolory.powierzchnia,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(borderRadius: _zaokraglenie, side: BorderSide(color: Kolory.ramka)),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        minimumSize: rozmiarPrzycisku,
        padding: const EdgeInsets.symmetric(horizontal: 20),
        shape: const RoundedRectangleBorder(borderRadius: _zaokraglenie),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        minimumSize: rozmiarPrzycisku,
        padding: const EdgeInsets.symmetric(horizontal: 20),
        foregroundColor: Kolory.primary,
        side: const BorderSide(color: Kolory.primary),
        shape: const RoundedRectangleBorder(borderRadius: _zaokraglenie),
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(minimumSize: rozmiarPrzycisku, foregroundColor: Kolory.primary),
    ),
    navigationBarTheme: const NavigationBarThemeData(
      backgroundColor: Kolory.powierzchnia,
      indicatorColor: Kolory.primaryLight,
      surfaceTintColor: Colors.transparent,
    ),
    navigationRailTheme: const NavigationRailThemeData(
      backgroundColor: Kolory.powierzchnia,
      indicatorColor: Kolory.primaryLight,
      selectedIconTheme: IconThemeData(color: Kolory.primaryDark),
      selectedLabelTextStyle: TextStyle(color: Kolory.primaryDark, fontWeight: FontWeight.w600, fontSize: 15),
      unselectedLabelTextStyle: TextStyle(color: Kolory.tekstDrugorzedny, fontSize: 15),
    ),
    dividerTheme: const DividerThemeData(color: Kolory.ramka, thickness: 1, space: 1),
  );
}
