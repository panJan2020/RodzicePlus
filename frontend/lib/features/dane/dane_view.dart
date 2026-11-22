import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/responsive.dart';
import '../../core/session.dart';
import '../../core/theme.dart';
import '../../data/models/modele.dart';
import '../../shared/formatowanie.dart';
import '../../shared/widgets/pytanie_widget.dart';
import '../../shared/widgets/stan_ladowania.dart';
import '../../shared/widgets/tresc_strony.dart';
import 'dane_viewmodel.dart';

/// Zakładka „Moje dane”: wszystkie pytania z katalogu jako drzewo zależności, osobno dla każdej osoby w sprawie.
/// Przy każdej odpowiedzi pokazujemy aktywną wartość i jej źródło („Skąd to wiemy”).
/// Telefon i tablet – sekcje jako rozwijane karty; komputer – sekcje po lewej, pytania po prawej.
/// Głęboki link: `/dane?pytanie=B5` rozwija sekcję, przewija do pytania i je wyróżnia.
class DaneView extends StatelessWidget {
  const DaneView({super.key, this.pytanie});

  final String? pytanie;

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      key: ValueKey(pytanie), // nowy link → nowy stan ekranu
      create: (c) => DaneViewModel(c.read(), pytanie: pytanie),
      child: const _Tresc(),
    );
  }
}

class _Tresc extends StatefulWidget {
  const _Tresc();

  @override
  State<_Tresc> createState() => _TrescState();
}

class _TrescState extends State<_Tresc> {
  final _klucze = <String, GlobalKey>{};

  GlobalKey _klucz(String id) => _klucze.putIfAbsent(id, GlobalKey.new);

  void _przewinJesliTrzeba(DaneViewModel vm) {
    final id = vm.doPrzewiniecia;
    if (id == null) return;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final ctx = _klucze[id]?.currentContext;
      if (ctx != null) {
        Scrollable.ensureVisible(ctx, alignment: 0.15, duration: const Duration(milliseconds: 300));
      }
      vm.przewinieto();
    });
  }

  Future<void> _zmien(DaneViewModel vm, PytanieDrzewa p) async {
    final wynik = await pokazEdycjePytania(context, p);
    if (wynik != null) await vm.zapisz(p, wynik.wartosc);
  }

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<DaneViewModel>();
    final t = Theme.of(context).textTheme;
    _przewinJesliTrzeba(vm);

    return TrescStrony(
      children: [
        Semantics(header: true, child: Text('Moje dane', style: t.headlineMedium)),
        const SizedBox(height: 8),
        Text(
          'Tu widzisz wszystkie informacje o Twojej sytuacji – z ZUS, z dokumentów i Twoje odpowiedzi. '
          'Możesz je sprawdzić i poprawić. Pytania, które Cię nie dotyczą, ukrywamy.',
          style: t.bodyLarge,
        ),
        const SizedBox(height: 16),
        StanLadowania(
          laduje: vm.laduje,
          blad: vm.blad,
          onPonow: vm.zaladuj,
          tresc: (_) => Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              _Naglowek(vm: vm),
              const SizedBox(height: 24),
              if (Responsive.uklad(context) == Uklad.komputer)
                _UkladKomputer(vm: vm, karta: _karta)
              else
                _UkladTelefon(vm: vm, karta: _karta),
            ],
          ),
        ),
      ],
    );
  }

  Widget _karta(DaneViewModel vm, PytanieDrzewa p) => _KartaPytania(
        key: _klucz(p.id),
        pytanie: p,
        wyroznione: vm.wyroznione == p.id,
        zapisuje: vm.zapisuje == p.id,
        dane: vm.dane!,
        onZmien: () => _zmien(vm, p),
        onPokaz: vm.pokaz,
      );
}

typedef _BudujKarte = Widget Function(DaneViewModel vm, PytanieDrzewa p);

/// Postęp całości + pobranie z ZUS + komunikaty.
class _Naglowek extends StatelessWidget {
  const _Naglowek({required this.vm});
  final DaneViewModel vm;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final postep = vm.dane!.postep;
    final zalogowany = context.watch<SesjaAplikacji>().zalogowany;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (vm.osoby.length > 1) ...[
              _WyborOsoby(vm: vm),
              const SizedBox(height: 16),
            ],
            Text('Odpowiedziano na ${postep.odpowiedziane} z ${postep.aktywne} pytań', style: t.titleMedium),
            const SizedBox(height: 8),
            LinearProgressIndicator(
              value: postep.aktywne == 0 ? 0 : postep.odpowiedziane / postep.aktywne,
              minHeight: 8,
              borderRadius: BorderRadius.circular(4),
              backgroundColor: Kolory.primaryLight,
              semanticsLabel: 'Postęp odpowiedzi: ${postep.odpowiedziane} z ${postep.aktywne}',
            ),
            if (zalogowany && vm.wybranyWnioskodawca) ...[
              const SizedBox(height: 16),
              Align(
                alignment: Alignment.centerLeft,
                child: OutlinedButton.icon(
                  onPressed: vm.pobieraZus ? null : vm.pobierzZZus,
                  icon: vm.pobieraZus
                      ? const SizedBox.square(dimension: 18, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Icon(Icons.download),
                  label: const Text('Uzupełnij danymi z ZUS'),
                ),
              ),
            ],
            if (vm.komunikat != null) ...[
              const SizedBox(height: 12),
              _Komunikat(tekst: vm.komunikat!, blad: false),
            ],
            if (vm.bladZapisu != null) ...[
              const SizedBox(height: 12),
              _Komunikat(tekst: vm.bladZapisu!, blad: true),
            ],
          ],
        ),
      ),
    );
  }
}

/// Czyje dane oglądamy: Ty, dziecko, drugi rodzic.
class _WyborOsoby extends StatelessWidget {
  const _WyborOsoby({required this.vm});
  final DaneViewModel vm;

  static String _etykieta(OsobaSprawy o, bool pierwsza) => switch (o.rola) {
        _ when pierwsza => o.imie == null ? 'Ty' : 'Ty (${o.imie})',
        RolaOsoby.dziecko => o.imie ?? 'Dziecko',
        RolaOsoby.matka => o.imie ?? 'Matka',
        RolaOsoby.ojciec => o.imie ?? 'Ojciec',
        RolaOsoby.drugiRodzic => o.imie ?? 'Drugi rodzic',
      };

  @override
  Widget build(BuildContext context) {
    final wybrana = vm.osobaId ?? vm.osoby.first.id;
    return Semantics(
      label: 'Czyje dane pokazać',
      child: Wrap(
        spacing: 8,
        runSpacing: 8,
        children: [
          for (final (i, o) in vm.osoby.indexed)
            ChoiceChip(
              label: Text(_etykieta(o, i == 0)),
              selected: o.id == wybrana,
              onSelected: (_) => vm.wybierzOsobe(o.id),
              materialTapTargetSize: MaterialTapTargetSize.padded,
            ),
        ],
      ),
    );
  }
}

class _Komunikat extends StatelessWidget {
  const _Komunikat({required this.tekst, required this.blad});
  final String tekst;
  final bool blad;

  @override
  Widget build(BuildContext context) {
    final kolor = blad ? Kolory.blad : Kolory.primary;
    return Semantics(
      liveRegion: true,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(blad ? Icons.error_outline : Icons.check_circle, color: kolor, semanticLabel: blad ? 'Błąd' : 'Gotowe'),
          const SizedBox(width: 8),
          Expanded(child: Text(tekst, style: TextStyle(fontSize: 16, color: blad ? Kolory.blad : Kolory.tekst))),
        ],
      ),
    );
  }
}

/// „3/5” z ikoną, gdy sekcja jest kompletna.
class _Licznik extends StatelessWidget {
  const _Licznik({required this.postep});
  final Postep postep;

  @override
  Widget build(BuildContext context) {
    final komplet = postep.aktywne > 0 && postep.odpowiedziane == postep.aktywne;
    return Semantics(
      label: 'Odpowiedziano ${postep.odpowiedziane} z ${postep.aktywne}',
      excludeSemantics: true,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (komplet) const Icon(Icons.check_circle, size: 18, color: Kolory.primary),
          if (komplet) const SizedBox(width: 4),
          Text(
            '${postep.odpowiedziane}/${postep.aktywne}',
            style: TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w600,
              color: komplet ? Kolory.primaryDark : Kolory.tekstDrugorzedny,
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Komputer: lista sekcji po lewej, pytania wybranej sekcji po prawej.
// ---------------------------------------------------------------------------

class _UkladKomputer extends StatelessWidget {
  const _UkladKomputer({required this.vm, required this.karta});
  final DaneViewModel vm;
  final _BudujKarte karta;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final wybrana = vm.sekcjaWybrana;
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 300,
          child: Card(
            child: Column(
              children: [
                for (final s in vm.sekcje)
                  _PozycjaSekcji(sekcja: s, wybrana: s.id == wybrana?.id, onTap: () => vm.wybierzSekcje(s.id)),
              ],
            ),
          ),
        ),
        const SizedBox(width: 24),
        Expanded(
          child: wybrana == null
              ? const SizedBox.shrink()
              : Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Semantics(header: true, child: Text(wybrana.tytul, style: t.titleLarge)),
                    const SizedBox(height: 12),
                    for (final p in wybrana.widoczne) ...[karta(vm, p), const SizedBox(height: 12)],
                  ],
                ),
        ),
      ],
    );
  }
}

class _PozycjaSekcji extends StatelessWidget {
  const _PozycjaSekcji({required this.sekcja, required this.wybrana, required this.onTap});
  final SekcjaDanych sekcja;
  final bool wybrana;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      selected: wybrana,
      button: true,
      child: Material(
        color: wybrana ? Kolory.primaryLight : Colors.transparent,
        child: InkWell(
          onTap: onTap,
          child: Container(
            constraints: const BoxConstraints(minHeight: 52),
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: BoxDecoration(
              border: Border(left: BorderSide(color: wybrana ? Kolory.primary : Colors.transparent, width: 4)),
            ),
            child: Row(
              children: [
                Expanded(
                  child: Text(
                    sekcja.tytul,
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: wybrana ? FontWeight.w600 : FontWeight.w400,
                      color: wybrana ? Kolory.primaryDark : Kolory.tekst,
                    ),
                  ),
                ),
                _Licznik(postep: sekcja.postep),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Telefon / tablet: sekcje jako rozwijane karty (akordeon).
// ---------------------------------------------------------------------------

class _UkladTelefon extends StatelessWidget {
  const _UkladTelefon({required this.vm, required this.karta});
  final DaneViewModel vm;
  final _BudujKarte karta;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (final s in vm.sekcje) ...[
          Card(
            clipBehavior: Clip.antiAlias,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Semantics(
                  button: true,
                  expanded: vm.rozwiniete.contains(s.id),
                  child: InkWell(
                    onTap: () => vm.przelaczSekcje(s.id),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                      child: Row(
                        children: [
                          Expanded(child: Text(s.tytul, style: Theme.of(context).textTheme.titleMedium)),
                          _Licznik(postep: s.postep),
                          const SizedBox(width: 8),
                          Icon(
                            vm.rozwiniete.contains(s.id) ? Icons.expand_less : Icons.expand_more,
                            color: Kolory.secondary,
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
                if (vm.rozwiniete.contains(s.id))
                  Container(
                    color: Kolory.tlo,
                    padding: const EdgeInsets.all(12),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        for (final p in s.widoczne) ...[karta(vm, p), const SizedBox(height: 8)],
                      ],
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 12),
        ],
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// Karta jednego pytania.
// ---------------------------------------------------------------------------

class _KartaPytania extends StatelessWidget {
  const _KartaPytania({
    super.key,
    required this.pytanie,
    required this.wyroznione,
    required this.zapisuje,
    required this.dane,
    required this.onZmien,
    required this.onPokaz,
  });

  final PytanieDrzewa pytanie;
  final bool wyroznione;
  final bool zapisuje;
  final DaneOsoby dane;
  final VoidCallback onZmien;
  final ValueChanged<String> onPokaz;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final p = pytanie;
    final zablokowane = p.status == StatusPytania.zablokowane;

    return AnimatedContainer(
      duration: const Duration(milliseconds: 250),
      decoration: BoxDecoration(
        color: zablokowane ? Kolory.tlo : Kolory.powierzchnia,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(
          color: wyroznione ? Kolory.primary : Kolory.ramka,
          width: wyroznione ? 2 : 1,
        ),
      ),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              EtykietaId(id: p.id),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  p.tresc,
                  style: t.titleMedium?.copyWith(color: zablokowane ? Kolory.tekstDrugorzedny : Kolory.tekst),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          if (zablokowane) _Zablokowane(pytanie: p, dane: dane, onPokaz: onPokaz) else ..._aktywne(context),
        ],
      ),
    );
  }

  List<Widget> _aktywne(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final p = pytanie;
    final w = p.wartosc;
    return [
      if (p.odpowiedziane && w != null)
        Container(
          width: double.infinity,
          padding: p.doSprawdzenia ? const EdgeInsets.all(12) : EdgeInsets.zero,
          decoration: p.doSprawdzenia
              ? BoxDecoration(
                  color: Kolory.ostrzezenieTlo,
                  borderRadius: BorderRadius.circular(6),
                  border: const Border(left: BorderSide(color: Kolory.ostrzezenie, width: 4)),
                )
              : null,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(opisWartosci(p), style: t.bodyLarge?.copyWith(fontWeight: FontWeight.w600)),
              const SizedBox(height: 4),
              Row(
                children: [
                  Icon(_ikonaZrodla(w.wystawca), size: 16, color: Kolory.tekstDrugorzedny),
                  const SizedBox(width: 6),
                  Flexible(child: Text(opisZrodla(p, w), style: t.bodyMedium)),
                ],
              ),
              if (p.konflikt) ...[
                const SizedBox(height: 6),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(Icons.compare_arrows, size: 18, color: Kolory.secondary, semanticLabel: 'Różne źródła'),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text(
                        'Mamy też inną wartość z innego źródła (${p.wartosci.length - 1}). '
                        'Do wyliczeń używamy tej powyżej.',
                        style: t.bodyMedium,
                      ),
                    ),
                  ],
                ),
              ],
              if (p.doSprawdzenia) ...[
                const SizedBox(height: 8),
                const Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(Icons.warning_amber_rounded, color: Kolory.ostrzezenie, size: 20, semanticLabel: 'Uwaga'),
                    SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Ten odczyt z dokumentu jest niepewny. Sprawdź, czy wartość jest poprawna.',
                        style: TextStyle(fontSize: 14, color: Kolory.tekst),
                      ),
                    ),
                  ],
                ),
              ],
            ],
          ),
        )
      else
        Text(
          p.edytowalne ? 'Brak odpowiedzi' : 'Brak danych w systemie',
          style: t.bodyMedium?.copyWith(fontStyle: FontStyle.italic),
        ),
      const SizedBox(height: 12),
      if (p.edytowalne)
        zapisuje
            ? const SizedBox.square(dimension: 24, child: CircularProgressIndicator(strokeWidth: 2.5))
            : p.odpowiedziane
                ? OutlinedButton.icon(
                    onPressed: onZmien,
                    icon: const Icon(Icons.edit_outlined),
                    label: Text(p.doSprawdzenia ? 'Sprawdź i popraw' : 'Zmień'),
                  )
                : FilledButton.icon(onPressed: onZmien, icon: const Icon(Icons.edit), label: const Text('Odpowiedz'))
      else
        Text('Tylko do podglądu – te dane pobieramy z systemów albo z dokumentów.', style: t.bodyMedium),
    ];
  }

  static IconData _ikonaZrodla(Wystawca z) => switch (z) {
        Wystawca.uzytkownik => Icons.person_outline,
        Wystawca.zus || Wystawca.urzad => Icons.account_balance_outlined,
        Wystawca.sad => Icons.gavel_outlined,
        Wystawca.pracodawca => Icons.business_outlined,
        Wystawca.lekarz => Icons.medical_services_outlined,
        Wystawca.wyliczone => Icons.calculate_outlined,
      };
}

/// „Odpowiedz najpierw na: A1 – Jaka jest Twoja sytuacja?” (klik przenosi do pytania).
class _Zablokowane extends StatelessWidget {
  const _Zablokowane({required this.pytanie, required this.dane, required this.onPokaz});
  final PytanieDrzewa pytanie;
  final DaneOsoby dane;
  final ValueChanged<String> onPokaz;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Icon(Icons.lock_outline, size: 18, color: Kolory.tekstDrugorzedny, semanticLabel: 'Zablokowane'),
            const SizedBox(width: 6),
            Text('Odpowiedz najpierw na:', style: t.bodyMedium),
          ],
        ),
        for (final id in pytanie.czekaNa)
          TextButton(
            onPressed: () => onPokaz(id),
            style: TextButton.styleFrom(padding: const EdgeInsets.symmetric(horizontal: 4)),
            child: Text(
              '$id – ${dane.pytanie(id)?.tresc ?? ''}',
              style: const TextStyle(decoration: TextDecoration.underline, fontSize: 15),
            ),
          ),
      ],
    );
  }
}
