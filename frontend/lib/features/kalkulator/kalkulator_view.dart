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

/// „Kalkulator” – okresy urlopów i kwoty zasiłku (czy przysługuje – ekran „Świadczenia”).
/// Komputer: dwie kolumny (podsumowanie | okresy i kwoty); telefon: jedna pod drugą.
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
        Semantics(header: true, child: Text('Kalkulator zasiłku', style: t.headlineMedium)),
        const SizedBox(height: 8),
        Text('Okresy urlopów i kwoty zasiłku liczymy z Twoich danych z zakładki „Moje dane”.', style: t.bodyLarge),
        const SizedBox(height: 4),
        Align(
          alignment: Alignment.centerLeft,
          child: TextButton.icon(
            onPressed: () => context.go('/swiadczenia'),
            icon: const Icon(Icons.fact_check_outlined),
            label: const Text('Czy zasiłek Ci przysługuje? Zobacz „Świadczenia”'),
          ),
        ),
        const SizedBox(height: 16),
        StanLadowania(
          laduje: vm.laduje,
          blad: vm.blad,
          onPonow: vm.zaladuj,
          tresc: (_) {
            final w = vm.wynik;
            if (w == null) return _BrakKwot(komunikat: vm.bladKalkulatora);
            final lewa = _Podsumowanie(wynik: w);
            final prawa = _Okresy(wynik: w);
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

String _nazwaOkresu(String s) => switch (s) {
      'macierzynski' => 'Urlop macierzyński',
      'rodzicielski' => 'Urlop rodzicielski',
      'ojcowski' => 'Urlop ojcowski',
      _ => s.replaceAll('_', ' '),
    };

class _Uwaga extends StatelessWidget {
  const _Uwaga(this.tekst);
  final String tekst;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Padding(
            padding: EdgeInsets.only(top: 2, right: 8),
            child: Icon(Icons.info_outline, size: 18, color: Kolory.secondary, semanticLabel: 'Uwaga'),
          ),
          Expanded(child: Text(tekst, style: Theme.of(context).textTheme.bodyLarge)),
        ]),
      );
}

class _Podsumowanie extends StatelessWidget {
  const _Podsumowanie({required this.wynik});
  final WynikKalkulatora wynik;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final ty = wynik.osoby.isEmpty ? null : wynik.osoby.first;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Semantics(header: true, child: Text('Podsumowanie', style: t.titleLarge)),
        const SizedBox(height: 12),
        Card(
          margin: EdgeInsets.zero,
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (wynik.orientacyjny) ...[
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(color: Kolory.ostrzezenieTlo, borderRadius: BorderRadius.circular(12)),
                    child: const Row(mainAxisSize: MainAxisSize.min, children: [
                      Icon(Icons.info_outline, color: Kolory.ostrzezenie, size: 18, semanticLabel: 'Wynik orientacyjny'),
                      SizedBox(width: 6),
                      Flexible(
                        child: Text('Wynik orientacyjny',
                            style: TextStyle(color: Kolory.ostrzezenie, fontWeight: FontWeight.w700, fontSize: 15)),
                      ),
                    ]),
                  ),
                  const SizedBox(height: 12),
                ],
                if (ty != null) ...[
                  Text('Podstawa wymiaru zasiłku', style: t.bodyMedium),
                  Text(formatujKwote(ty.podstawaWymiaru), style: t.titleLarge),
                  const SizedBox(height: 8),
                ],
                Text('Razem za wszystkie okresy (brutto)', style: t.bodyMedium),
                Text(formatujKwote(wynik.suma), style: t.titleLarge?.copyWith(color: Kolory.primaryDark)),
                if (ty?.powrotDoPracy != null) ...[
                  const SizedBox(height: 8),
                  Text('Powrót do pracy', style: t.bodyMedium),
                  Text(formatujDate(ty!.powrotDoPracy!), style: t.titleLarge),
                ],
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),
        for (final o in wynik.ostrzezenia) _Uwaga(o),
        Text('Parametry prawne obowiązujące od ${formatujDateIso(wynik.wersjaParametrow)}', style: t.bodyMedium),
      ],
    );
  }
}

class _Okresy extends StatelessWidget {
  const _Okresy({required this.wynik});
  final WynikKalkulatora wynik;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final ty = wynik.osoby.isEmpty ? null : wynik.osoby.first;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Semantics(header: true, child: Text('Okresy i kwoty', style: t.titleLarge)),
        const SizedBox(height: 12),
        for (final o in wynik.okresy) ...[
          Card(
            margin: EdgeInsets.zero,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(_nazwaOkresu(o.rodzaj), style: t.titleMedium),
                  Text('${formatujDate(o.odDnia)} – ${formatujDate(o.doDnia)} · ${o.tygodnie} tyg. · '
                      '${o.osobaId != null && o.osobaId == ty?.osobaId ? 'Ty' : 'drugi rodzic'}',
                      style: t.bodyMedium),
                  const SizedBox(height: 8),
                  Text('${formatujProcent(o.stawka)} podstawy · ${formatujKwote(o.kwotaMiesieczna)} miesięcznie (brutto)',
                      style: t.bodyLarge),
                  if (o.stawkaDzienna.isNotEmpty)
                    Text('${formatujKwote(o.stawkaDzienna)} za każdy dzień', style: t.bodyMedium),
                  Text('Za cały okres: ${formatujKwote(o.kwotaZaOkres)} brutto',
                      style: t.bodyLarge?.copyWith(fontWeight: FontWeight.w600)),
                  for (final u in o.uwagi) Text(u, style: t.bodyMedium),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
        ],
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
