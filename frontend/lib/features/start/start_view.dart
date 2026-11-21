import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/session.dart';
import '../../core/theme.dart';
import '../../shared/widgets/tresc_strony.dart';

/// Ekran startowy (statyczny – bez ViewModelu). Zachęca do zalogowania.
class StartView extends StatelessWidget {
  const StartView({super.key});

  @override
  Widget build(BuildContext context) {
    final sesja = context.watch<SesjaAplikacji>();
    final t = Theme.of(context).textTheme;

    return TrescStrony(
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
          'Pomożemy Ci ustalić prawo do zasiłku macierzyńskiego i innych świadczeń z ZUS, '
          'policzyć ich wysokość i przygotować potrzebne dokumenty.',
          style: t.bodyLarge,
        ),
        const SizedBox(height: 24),
        Container(
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(color: Kolory.primaryLight, borderRadius: BorderRadius.circular(6)),
          child: sesja.zalogowany
              ? Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.check_circle, color: Kolory.primary, semanticLabel: 'Zalogowano'),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Text('Zalogowano jako ${sesja.dane!.imieINazwisko}.', style: t.bodyLarge),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    Text('Sprawdź, co ZUS wie o Twoim ubezpieczeniu.', style: t.bodyLarge),
                    const SizedBox(height: 12),
                    FilledButton.icon(
                      onPressed: () => context.go('/ubezpieczenie'),
                      icon: const Icon(Icons.health_and_safety_outlined),
                      label: const Text('Pobierz dane z ZUS'),
                    ),
                  ],
                )
              : Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Zacznij od zalogowania', style: t.titleLarge),
                    const SizedBox(height: 8),
                    Text(
                      'Zaloguj się przez mObywatel (symulacja), a pobierzemy dane o Twoim ubezpieczeniu z ZUS.',
                      style: t.bodyLarge,
                    ),
                    const SizedBox(height: 16),
                    FilledButton.icon(
                      onPressed: () => context.go('/logowanie'),
                      icon: const Icon(Icons.login),
                      label: const Text('Zaloguj (mObywatel)'),
                    ),
                  ],
                ),
        ),
      ],
    );
  }
}
