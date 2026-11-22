import 'package:flutter/material.dart';

import '../../core/theme.dart';
import '../../data/models/modele.dart';
import '../formatowanie.dart';

/// Pole odpowiedzi na jedno pytanie z katalogu. Wspólne dla zakładki „Dane” i kreatora.
///
/// Widżet tylko zbiera odpowiedź i oddaje ją przez [onZmiana] w formacie API:
/// wybor → String, wielokrotny → List, tak_nie → bool, liczba/kwota → num, data → `RRRR-MM-DD`,
/// pole „na tytuł” → `{tytuł: odpowiedź}`. `null` = brak odpowiedzi. Niczego nie sprawdza – to robi backend
/// (on też zamienia kwoty i ułamki na tekst).
class PytanieWidget extends StatefulWidget {
  const PytanieWidget({super.key, required this.pytanie, required this.wartosc, required this.onZmiana});

  final PytanieDrzewa pytanie;
  final Object? wartosc;
  final ValueChanged<Object?> onZmiana;

  @override
  State<PytanieWidget> createState() => _PytanieWidgetState();
}

class _PytanieWidgetState extends State<PytanieWidget> {
  late final TextEditingController _tekst = TextEditingController(
    text: switch (widget.wartosc) {
      final num n => formatujLiczbe(n),
      final String s when num.tryParse(s) != null => formatujLiczbe(s),
      _ => '',
    },
  );

  @override
  void dispose() {
    _tekst.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final p = widget.pytanie;
    if (p.naTytul) return _naTytul(p);
    return switch (p.typ) {
      TypPytania.wybor => _karty(
          [for (final o in p.opcje) (o.etykieta, widget.wartosc == o.wartosc, () => widget.onZmiana(o.wartosc))],
          wielokrotny: false,
        ),
      TypPytania.takNie => _karty([
          ('Tak', widget.wartosc == true, () => widget.onZmiana(true)),
          ('Nie', widget.wartosc == false, () => widget.onZmiana(false)),
        ], wielokrotny: false),
      TypPytania.wielokrotny => _karty([
          for (final o in p.opcje) (o.etykieta, _wybrane.contains(o.wartosc), () => _przelacz(o.wartosc)),
        ], wielokrotny: true),
      TypPytania.liczba || TypPytania.kwota => _pole(p),
      TypPytania.data => _data(context),
      TypPytania.okresy || TypPytania.miesiace || TypPytania.zasilek => Text(opisWartosci(p), style: Theme.of(context).textTheme.bodyLarge),
    };
  }

  /// Pole „na tytuł” (np. C1): osobna odpowiedź dla każdej umowy.
  Widget _naTytul(PytanieDrzewa p) {
    final t = Theme.of(context).textTheme;
    if (p.klucze.isEmpty) {
      return Text('Najpierw zaznacz, na jakiej podstawie pracujesz (pytanie B1).', style: t.bodyLarge);
    }
    final mapa = widget.wartosc is Map ? Map<String, Object?>.from(widget.wartosc as Map) : <String, Object?>{};
    void ustaw(Object? klucz, Object? v) {
      final nowa = {...mapa, '$klucz': v};
      widget.onZmiana(nowa.values.every((x) => x != null) && nowa.length == p.klucze.length ? nowa : null);
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (final k in p.klucze) ...[
          Text(k.etykieta, style: t.titleMedium),
          const SizedBox(height: 8),
          if (p.typ == TypPytania.takNie)
            _karty([
              ('Tak', mapa['${k.wartosc}'] == true, () => ustaw(k.wartosc, true)),
              ('Nie', mapa['${k.wartosc}'] == false, () => ustaw(k.wartosc, false)),
            ], wielokrotny: false)
          else
            _karty([
              for (final o in p.opcje) (o.etykieta, mapa['${k.wartosc}'] == o.wartosc, () => ustaw(k.wartosc, o.wartosc)),
            ], wielokrotny: false),
          const SizedBox(height: 8),
        ],
      ],
    );
  }

  List<Object?> get _wybrane => widget.wartosc is List ? List<Object?>.from(widget.wartosc as List) : [];

  void _przelacz(Object? v) {
    final w = _wybrane;
    w.contains(v) ? w.remove(v) : w.add(v);
    widget.onZmiana(w.isEmpty ? null : w);
  }

  /// Duże karty do kliknięcia (min. 48 px) – jak w serwisach publicznych.
  Widget _karty(List<(String, bool, VoidCallback)> opcje, {required bool wielokrotny}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (final (etykieta, wybrana, onTap) in opcje)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Semantics(
              checked: wybrana,
              inMutuallyExclusiveGroup: !wielokrotny,
              child: Material(
                color: wybrana ? Kolory.primaryLight : Kolory.powierzchnia,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(6),
                  side: BorderSide(color: wybrana ? Kolory.primary : Kolory.ramka, width: wybrana ? 2 : 1),
                ),
                child: InkWell(
                  borderRadius: BorderRadius.circular(6),
                  onTap: onTap,
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(minHeight: 48),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                      child: Row(
                        children: [
                          Icon(
                            wielokrotny
                                ? (wybrana ? Icons.check_box : Icons.check_box_outline_blank)
                                : (wybrana ? Icons.radio_button_checked : Icons.radio_button_unchecked),
                            color: wybrana ? Kolory.primary : Kolory.tekstDrugorzedny,
                          ),
                          const SizedBox(width: 12),
                          Expanded(child: Text(etykieta, style: Theme.of(context).textTheme.bodyLarge)),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
      ],
    );
  }

  Widget _pole(PytanieDrzewa p) {
    return TextField(
      controller: _tekst,
      autofocus: true,
      keyboardType: const TextInputType.numberWithOptions(decimal: true),
      decoration: InputDecoration(
        border: const OutlineInputBorder(),
        labelText: p.typ == TypPytania.kwota ? 'Kwota brutto' : 'Liczba',
        suffixText: p.typ == TypPytania.kwota ? 'zł' : null,
        helperText: 'Możesz użyć przecinka, np. 0,5',
      ),
      onChanged: (t) {
        final tekst = t.trim().replaceAll(' ', '').replaceAll(' ', '').replaceAll(',', '.');
        widget.onZmiana(tekst.isEmpty ? null : num.tryParse(tekst));
      },
    );
  }

  Widget _data(BuildContext context) {
    final obecna = widget.wartosc is String ? DateTime.tryParse(widget.wartosc as String) : null;
    return Align(
      alignment: Alignment.centerLeft,
      child: OutlinedButton.icon(
        icon: const Icon(Icons.calendar_today),
        label: Text(obecna == null ? 'Wybierz datę' : formatujDate(obecna)),
        onPressed: () async {
          final teraz = DateTime.now();
          final d = await showDatePicker(
            context: context,
            initialDate: obecna ?? teraz,
            firstDate: DateTime(1940),
            lastDate: DateTime(teraz.year + 3),
            helpText: widget.pytanie.tresc,
          );
          if (d != null) widget.onZmiana(dataIso(d));
        },
      ),
    );
  }
}

/// Wynik okna edycji: `null` = anulowano.
class EdycjaOdpowiedzi {
  const EdycjaOdpowiedzi(this.wartosc);
  final Object? wartosc; // null = wyczyść odpowiedź
}

/// Okno „Zmień odpowiedź” z [PytanieWidget]. Zwraca nową wartość albo `null`, gdy anulowano.
Future<EdycjaOdpowiedzi?> pokazEdycjePytania(BuildContext context, PytanieDrzewa p) {
  Object? wartosc = p.wartosc?.wartosc;
  final t = Theme.of(context).textTheme;
  return showDialog<EdycjaOdpowiedzi>(
    context: context,
    builder: (context) => StatefulBuilder(
      builder: (context, setState) => AlertDialog(
        insetPadding: const EdgeInsets.all(16),
        titlePadding: const EdgeInsets.fromLTRB(24, 24, 24, 8),
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            EtykietaId(id: p.id),
            const SizedBox(height: 8),
            Text(p.tresc, style: t.titleLarge),
          ],
        ),
        content: SizedBox(
          width: 520,
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              mainAxisSize: MainAxisSize.min,
              children: [
                if (p.pomoc != null) ...[Text(p.pomoc!, style: t.bodyMedium), const SizedBox(height: 16)],
                PytanieWidget(pytanie: p, wartosc: wartosc, onZmiana: (v) => setState(() => wartosc = v)),
                if (p.gdzieZnalezc != null) ...[
                  const SizedBox(height: 12),
                  Text('Gdzie to znaleźć: ${p.gdzieZnalezc}', style: t.bodyMedium),
                ],
              ],
            ),
          ),
        ),
        actions: [
          if (p.maOdpowiedzUzytkownika)
            TextButton(
              onPressed: () => Navigator.pop(context, const EdycjaOdpowiedzi(null)),
              child: const Text('Wyczyść'),
            ),
          OutlinedButton(onPressed: () => Navigator.pop(context), child: const Text('Anuluj')),
          FilledButton(
            onPressed: wartosc == null ? null : () => Navigator.pop(context, EdycjaOdpowiedzi(wartosc)),
            child: const Text('Zapisz'),
          ),
        ],
      ),
    ),
  );
}

/// Mała etykieta z ID pytania, np. „B5” (te same ID co w dokumentacji i w komunikatach o brakach).
class EtykietaId extends StatelessWidget {
  const EtykietaId({super.key, required this.id});
  final String id;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: 'Pytanie $id',
      excludeSemantics: true,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
        decoration: BoxDecoration(
          color: Kolory.tlo,
          borderRadius: BorderRadius.circular(4),
          border: Border.all(color: Kolory.ramka),
        ),
        child: Text(id, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: Kolory.secondary)),
      ),
    );
  }
}
