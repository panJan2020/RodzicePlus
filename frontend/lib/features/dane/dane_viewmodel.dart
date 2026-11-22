import 'package:flutter/foundation.dart';

import '../../data/api_client.dart';
import '../../data/models/modele.dart';
import '../../data/repositories/sprawa_repository.dart';

/// Zakładka „Moje dane” – wszystkie pytania wybranej osoby w sprawie (Ty, dziecko…) do przeglądu i edycji.
/// Stany pytań (aktywne / zablokowane / wykluczone) i aktywne wartości liczy backend; tu trzymamy tylko stan ekranu.
class DaneViewModel extends ChangeNotifier {
  DaneViewModel(this._sprawy, {String? pytanie}) {
    zaladuj(pokaz: pytanie);
  }

  final SprawaRepository _sprawy;

  /// Osoby w sprawie (przełącznik nad pytaniami).
  List<OsobaSprawy> osoby = const [];

  /// Wybrana osoba; `null` – wnioskodawca (pierwsza osoba).
  String? osobaId;

  DaneOsoby? dane;
  bool laduje = false;
  String? blad;

  /// Komputer: sekcja pokazana po prawej.
  String? wybranaSekcja;

  /// Telefon: rozwinięte karty sekcji (akordeon).
  final Set<String> rozwiniete = {};

  /// Pytanie wyróżnione ramką (np. z linku `/dane?pytanie=B5` albo „Odpowiedz najpierw na…”).
  String? wyroznione;

  /// Pytanie, do którego widok ma przewinąć po najbliższym rysowaniu (potem [przewinieto]).
  String? doPrzewiniecia;

  /// ID pytania, którego odpowiedź właśnie zapisujemy.
  String? zapisuje;
  String? bladZapisu;

  bool pobieraZus = false;
  String? komunikat;

  List<SekcjaDanych> get sekcje => dane?.widoczneSekcje ?? const [];

  /// Czy wybrana jest osoba prowadząca sprawę (dla niej działa „Uzupełnij danymi z ZUS”).
  bool get wybranyWnioskodawca => osoby.isEmpty || (osobaId ?? osoby.first.id) == osoby.first.id;

  SekcjaDanych? get sekcjaWybrana {
    for (final s in sekcje) {
      if (s.id == wybranaSekcja) return s;
    }
    return sekcje.isEmpty ? null : sekcje.first;
  }

  Future<void> zaladuj({String? pokaz}) async {
    laduje = dane == null;
    blad = null;
    notifyListeners();
    try {
      osoby = (await _sprawy.sprawa()).osoby;
      dane = await _sprawy.dane(osoba: osobaId);
      _poprawWybor();
      if (pokaz != null) this.pokaz(pokaz, powiadom: false);
    } on ApiException catch (e) {
      blad = e.komunikat;
    } finally {
      laduje = false;
      notifyListeners();
    }
  }

  /// Przełącza pytania na inną osobę w sprawie (np. dziecko).
  Future<void> wybierzOsobe(String id) async {
    if (id == (osobaId ?? osoby.first.id)) return;
    osobaId = id;
    dane = null;
    wybranaSekcja = null;
    rozwiniete.clear();
    wyroznione = null;
    komunikat = null;
    bladZapisu = null;
    await zaladuj();
  }

  /// Rozwija sekcję pytania, wyróżnia je i prosi widok o przewinięcie.
  void pokaz(String id, {bool powiadom = true}) {
    final p = dane?.pytanie(id);
    if (p == null || p.status == StatusPytania.wykluczone) return;
    wybranaSekcja = p.sekcja;
    rozwiniete.add(p.sekcja);
    wyroznione = id;
    doPrzewiniecia = id;
    if (powiadom) notifyListeners();
  }

  void przewinieto() => doPrzewiniecia = null;

  void wybierzSekcje(String id) {
    wybranaSekcja = id;
    notifyListeners();
  }

  void przelaczSekcje(String id) {
    rozwiniete.contains(id) ? rozwiniete.remove(id) : rozwiniete.add(id);
    notifyListeners();
  }

  /// Zapisuje odpowiedź i odświeża drzewo – mogą pojawić się albo zniknąć pytania zależne.
  Future<void> zapisz(PytanieDrzewa p, Object? wartosc) async {
    zapisuje = p.id;
    bladZapisu = null;
    komunikat = null;
    notifyListeners();
    try {
      await _sprawy.zapiszOdpowiedz(p.pole, wartosc, osoba: osobaId);
      dane = await _sprawy.dane(osoba: osobaId);
      _poprawWybor();
      wyroznione = p.id;
    } on ApiException catch (e) {
      bladZapisu = e.komunikat;
    } finally {
      zapisuje = null;
      notifyListeners();
    }
  }

  /// Uzupełnia sprawę danymi z ZUS (tylko po zalogowaniu). Odpowiedzi użytkownika zostają jako osobne wartości.
  Future<void> pobierzZZus() async {
    pobieraZus = true;
    komunikat = null;
    bladZapisu = null;
    notifyListeners();
    try {
      final zmiana = await _sprawy.pobierzZZus();
      dane = await _sprawy.dane(osoba: osobaId);
      _poprawWybor();
      komunikat = zmiana.noweKonflikty == 0
          ? 'Uzupełniliśmy dane z ZUS.'
          : 'Uzupełniliśmy dane z ZUS. Część z nich różni się od Twoich odpowiedzi – do wyliczeń używamy '
              'danych z ZUS, a Twoja odpowiedź zostaje zapisana.';
    } on ApiException catch (e) {
      bladZapisu = e.komunikat;
    } finally {
      pobieraZus = false;
      notifyListeners();
    }
  }

  /// Po odświeżeniu wybrana sekcja mogła zniknąć (wszystkie pytania wykluczone).
  void _poprawWybor() {
    if (!sekcje.any((s) => s.id == wybranaSekcja)) {
      wybranaSekcja = sekcje.isEmpty ? null : sekcje.first.id;
    }
  }
}
