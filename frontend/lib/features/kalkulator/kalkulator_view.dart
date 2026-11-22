import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/responsive.dart';
import '../../core/theme.dart';
import '../../data/models/modele.dart';
import '../../shared/formatowanie.dart';
import '../../shared/widgets/stan_ladowania.dart';
import '../../shared/widgets/tresc_strony.dart';
import 'kalkulator_viewmodel.dart';

/// „Kalkulator” – czy świadczenie przysługuje (z uzasadnieniem) i ile wynosi.
/// Komputer: dwie kolumny (uprawnienia | okresy i kwoty); telefon: jedna pod drugą.
class KalkulatorView extends StatelessWidget {
  const KalkulatorView({super.key});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (c) => KalkulatorViewModel(c.read()),
      child: const _Tresc(),
    );
  }
}

class _Tresc extends StatelessWidget {
  const _Tresc();

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<KalkulatorViewModel>();
    final t = Theme.of(context).textTheme;
    return TrescStrony(
      children: [
        Semantics(header: true, child: Text('Twoje świadczenia', style: t.headlineMedium)),
        const SizedBox(height: 8),
        Text('Wynik liczymy na podstawie Twoich danych z zakładki „Moje dane”.', style: t.bodyLarge),
        const SizedBox(height: 24),
        StanLadowania(
          laduje: vm.laduje,
          blad: vm.blad,
          onPonow: vm.zaladuj,
          tresc: (_) {
            final lewa = Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Semantics(header: true, child: Text('Czy Ci przysługuje', style: t.titleLarge)),
                const SizedBox(height: 12),
                for (final u in vm.uprawnienia) ...[_KartaUprawnienia(wynik: u), const SizedBox(height: 12)],
              ],
            );
            final prawa = Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Semantics(header: true, child: Text('Okresy i kwoty', style: t.titleLarge)),
                const SizedBox(height: 12),
                if (vm.wynik != null) _Kwoty(wynik: vm.wynik!) else _BrakKwot(komunikat: vm.bladKalkulatora),
              ],
            );
            if (Responsive.uklad(context) == Uklad.komputer) {
              return Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [Expanded(child: lewa), const SizedBox(width: 24), Expanded(child: prawa)],
              );
            }
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [lewa, const SizedBox(height: 24), prawa],
            );
          },
        ),
      ],
    );
  }
}

String _nazwaSwiadczenia(String s) => switch (s) {
      'zasilek_macierzynski' => 'Zasiłek macierzyński',
      'zasilek_chorobowy_ciaza' => 'Zasiłek chorobowy w ciąży',
      _ => s.replaceAll('_', ' '),
    };

String _nazwaOkresu(String s) => switch (s) {
      'macierzynski' => 'Urlop macierzyński',
      'rodzicielski' => 'Urlop rodzicielski',
      'rodzicielski_9_tyg' => 'Urlop rodzicielski – 9 tygodni drugiego rodzica',
      'ojcowski' => 'Urlop ojcowski',
      _ => s.replaceAll('_', ' '),
    };

class _KartaUprawnienia extends StatelessWidget {
  const _KartaUprawnienia({required this.wynik});
  final WynikUprawnienia wynik;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final w = wynik;
    final (kolor, tlo, ikona, napis) = switch (w.status) {
      StatusUprawnienia.przysluguje => (Kolory.primary, Kolory.primaryLight, Icons.check_circle, 'Przysługuje'),
      StatusUprawnienia.niePrzysluguje => (Kolory.blad, Kolory.bladTlo, Icons.cancel, 'Nie przysługuje'),
      StatusUprawnienia.brakDanych => (Kolory.ostrzezenie, Kolory.ostrzezenieTlo, Icons.help, 'Brakuje danych'),
    };

    return Card(
      clipBehavior: Clip.antiAlias,
      child: Container(
        decoration: BoxDecoration(border: Border(left: BorderSide(color: kolor, width: 4))),
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(_nazwaSwiadczenia(w.swiadczenie), style: t.titleMedium),
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(color: tlo, borderRadius: BorderRadius.circular(12)),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(ikona, color: kolor, size: 18, semanticLabel: napis),
                  const SizedBox(width: 6),
                  Text(napis, style: TextStyle(color: kolor, fontWeight: FontWeight.w700, fontSize: 15)),
                ],
              ),
            ),
            const SizedBox(height: 12),
            for (final u in w.uzasadnienie) Text(u, style: t.bodyLarge),
            if (w.ktoWyplaca != null) ...[
              const SizedBox(height: 8),
              Text('Kto wypłaca: ${w.ktoWyplaca}', style: t.bodyLarge),
            ],
            if (w.status == StatusUprawnienia.brakDanych && w.brakujacePytania.isNotEmpty) ...[
              const SizedBox(height: 12),
              _Brakujace(wynik: w),
            ],
            if (w.podstawaPrawna.isNotEmpty) ...[
              const SizedBox(height: 12),
              Text('(${w.podstawaPrawna.join('; ')})', style: t.bodyMedium),
            ],
          ],
        ),
      ),
    );
  }
}

/// „Brakuje N odpowiedzi:” + lista pytań + „Uzupełnij” → `/dane?pytanie=<pierwsze ID>`.
class _Brakujace extends StatelessWidget {
  const _Brakujace({required this.wynik});
  final WynikUprawnienia wynik;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final braki = wynik.brakujacePytania;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Brakuje odpowiedzi: ${braki.length}', style: t.titleMedium),
        const SizedBox(height: 6),
        for (final b in braki)
          Padding(
            padding: const EdgeInsets.only(bottom: 6),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Padding(
                  padding: EdgeInsets.only(top: 9, right: 10, left: 4),
                  child: Icon(Icons.circle, size: 6, color: Kolory.tekstDrugorzedny),
                ),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('${b.tresc} (${b.id})', style: t.bodyLarge),
                      if (b.gdzieZnalezc != null) Text('Znajdziesz to: ${b.gdzieZnalezc}', style: t.bodyMedium),
                    ],
                  ),
                ),
              ],
            ),
          ),
        const SizedBox(height: 8),
        FilledButton.icon(
          onPressed: () => context.go(Uri(path: '/dane', queryParameters: {'pytanie': braki.first.id}).toString()),
          icon: const Icon(Icons.edit),
          label: const Text('Uzupełnij'),
        ),
      ],
    );
  }
}

class _Kwoty extends StatelessWidget {
  const _Kwoty({required this.wynik});
  final WynikKalkulatora wynik;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Podstawa wymiaru zasiłku', style: t.bodyMedium),
                Text(formatujKwote(wynik.podstawaWymiaru), style: t.titleLarge),
                const SizedBox(height: 8),
                Text('Razem za wszystkie okresy (brutto)', style: t.bodyMedium),
                Text(formatujKwote(wynik.suma), style: t.titleLarge?.copyWith(color: Kolory.primaryDark)),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),
        for (final o in wynik.okresy) ...[
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(_nazwaOkresu(o.rodzaj), style: t.titleMedium),
                  Text('${formatujDate(o.odDnia)} – ${formatujDate(o.doDnia)} · ${o.osoba}', style: t.bodyMedium),
                  const SizedBox(height: 8),
                  Text('${formatujProcent(o.stawka)} podstawy · ${formatujKwote(o.kwotaMiesieczna)} miesięcznie (brutto)',
                      style: t.bodyLarge),
                  Text('Za cały okres: ${formatujKwote(o.kwotaZaOkres)} brutto',
                      style: t.bodyLarge?.copyWith(fontWeight: FontWeight.w600)),
                  for (final u in o.uwagi) Text(u, style: t.bodyMedium),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
        ],
        Text('Parametry prawne: ${wynik.wersjaParametrow}', style: t.bodyMedium),
      ],
    );
  }
}

class _BrakKwot extends StatelessWidget {
  const _BrakKwot({required this.komunikat});
  final String? komunikat;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Icon(Icons.info_outline, color: Kolory.secondary, semanticLabel: 'Informacja'),
            const SizedBox(height: 8),
            Text(komunikat ?? 'Nie możemy jeszcze policzyć kwot.', style: t.bodyLarge),
            const SizedBox(height: 12),
            OutlinedButton(onPressed: () => context.go('/dane'), child: const Text('Przejdź do „Moich danych”')),
          ],
        ),
      ),
    );
  }
}
