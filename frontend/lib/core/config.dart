/// Konfiguracja z `--dart-define`.
///
/// Domyślnie adres API jest **względny** (ten sam origin co strona) – tak działa wdrożenie, w którym
/// backend i frontend są pod jednym adresem. Przy lokalnej pracy (Flutter na innym porcie niż backend)
/// podaj adres: `flutter run -d chrome --dart-define=API_URL=http://localhost:8000`
class Config {
  static const String apiUrl = String.fromEnvironment('API_URL');

  static const String nazwaAplikacji = 'Zasiłkowy Przewodnik Rodzica';
}
