/// Mały magazyn klucz → tekst, który przeżywa odświeżenie strony.
///
/// W przeglądarce: `sessionStorage` (znika po zamknięciu karty – to symulowane logowanie, nie chcemy
/// trzymać go dłużej). Każdy odczyt i zapis jest w try/catch: storage bywa zablokowany (tryb prywatny,
/// polityka przeglądarki) i wtedy aplikacja działa dalej, tylko bez zapamiętywania.
abstract class MagazynTrwaly {
  String? czytaj(String klucz);
  void zapisz(String klucz, String? wartosc); // null usuwa
}

/// Nie zapamiętuje niczego (domyślnie w testach i poza przeglądarką).
class MagazynPusty implements MagazynTrwaly {
  const MagazynPusty();

  @override
  String? czytaj(String klucz) => null;

  @override
  void zapisz(String klucz, String? wartosc) {}
}

/// Pamięć procesu – do testów odświeżenia strony (ten sam magazyn przekazany nowej sesji).
class MagazynWPamieci implements MagazynTrwaly {
  final Map<String, String> dane = {};

  @override
  String? czytaj(String klucz) => dane[klucz];

  @override
  void zapisz(String klucz, String? wartosc) {
    if (wartosc == null) {
      dane.remove(klucz);
    } else {
      dane[klucz] = wartosc;
    }
  }
}
