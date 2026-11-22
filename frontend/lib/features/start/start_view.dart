import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/responsive.dart';
import '../../core/session.dart';
import '../../core/theme.dart';
import '../../shared/widgets/tresc_strony.dart';
import 'start_viewmodel.dart';

/// Ekran startowy: do kogo jest aplikacja, co zrobi, i dwa duże przyciski – „Wgraj dokumenty”
/// oraz „Zobacz świadczenia” (aktywny, gdy sprawa ma dane).
class StartView extends StatelessWidget {
  const StartView({super.key});

  @override
  Widget build(BuildContext context) =>
      ChangeNotifierProvider(create: (c) => StartViewModel(c.read()), child: const _Tresc());
}

class _Tresc extends StatelessWidget {
  const _Tresc();

  @override
  Widget build(BuildContext context) {
    final sesja = context.watch<SesjaAplikacji>();
    final vm = context.watch<StartViewModel>();
    final t = Theme.of(context).textTheme;
    const duzyPrzycisk = Size.fromHeight(56);

    return TrescStrony(
      maxSzerokosc: Responsive.maxFormularz,
      children: [
        Semantics(
          header: true,
          child: Text(
            sesja.zalogowany ? 'Dzień dobry, ${sesja.dane!.imie}' : 'Sprawdź, jakie świadczenia Ci przysługują',
            style: t.headlineMedium,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          'Dla przyszłych rodziców, kobiet w ciąży oraz rodziców adopcyjnych i zastępczych. '
          'Wgraj skany dokumentów (PDF) – odczytamy je, sprawdzimy, jakie świadczenia z ZUS Ci przysługują, '
          'i policzymy ich okres oraz wysokość.',
          style: t.bodyLarge,
        ),
        const SizedBox(height: 24),
        FilledButton.icon(
          style: FilledButton.styleFrom(minimumSize: duzyPrzycisk, textStyle: t.titleMedium),
          onPressed: () => context.push('/dokumenty'),
          icon: const Icon(Icons.upload_file),
          label: const Text('Wgraj dokumenty'),
        ),
        const SizedBox(height: 12),
        OutlinedButton.icon(
          style: OutlinedButton.styleFrom(minimumSize: duzyPrzycisk, textStyle: t.titleMedium),
          onPressed: vm.maDane ? () => context.push('/swiadczenia') : null,
          icon: const Icon(Icons.verified_outlined),
          label: const Text('Zobacz świadczenia'),
        ),
        if (!vm.maDane) ...[
          const SizedBox(height: 8),
          Text(vm.laduje ? 'Sprawdzamy Twoją sprawę…' : 'Ten przycisk zadziała po wgraniu dokumentów.',
              style: t.bodyMedium?.copyWith(color: Kolory.tekstDrugorzedny)),
        ],
        const SizedBox(height: 32),
        if (sesja.zalogowany)
          Row(children: [
            const Icon(Icons.check_circle, color: Kolory.primary, semanticLabel: 'Zalogowano'),
            const SizedBox(width: 8),
            Expanded(child: Text('Zalogowano jako ${sesja.dane!.imieINazwisko} (symulacja mObywatela).',
                style: t.bodyMedium)),
          ])
        else
          Align(
            alignment: Alignment.centerLeft,
            child: TextButton.icon(
              onPressed: () => context.go('/logowanie'),
              icon: const Icon(Icons.login),
              label: const Text('Zaloguj (mObywatel)'),
            ),
          ),
      ],
    );
  }
}
