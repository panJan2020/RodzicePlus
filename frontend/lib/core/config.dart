/// Konfiguracja z `--dart-define`. Adres API podajemy przy uruchomieniu:
/// `flutter run -d chrome --dart-define=API_URL=http://localhost:8000`
class Config {
  static const String apiUrl = String.fromEnvironment(
    'API_URL',
    defaultValue: 'http://localhost:8000',
  );

  static const String nazwaAplikacji = 'Zasiłkowy Przewodnik Rodzica';
}
