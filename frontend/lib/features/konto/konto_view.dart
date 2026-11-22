import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/responsive.dart';
import '../../core/theme.dart';
import '../../shared/widgets/stan_ladowania.dart';
import '../../shared/widgets/tresc_strony.dart';
import 'konto_viewmodel.dart';

/// „Moje konto” – kim jestem po symulowanym logowaniu.
class KontoView extends StatelessWidget {
  const KontoView({super.key});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (c) => KontoViewModel(c.read()),
      child: const _Tresc(),
    );
  }
}

class _Tresc extends StatelessWidget {
  const _Tresc();

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<KontoViewModel>();
    final t = Theme.of(context).textTheme;

    return TrescStrony(
      maxSzerokosc: Responsive.maxFormularz,
      children: [
        Semantics(header: true, child: Text('Moje konto', style: t.headlineMedium)),
        const SizedBox(height: 16),
        StanLadowania(
          laduje: vm.laduje,
          blad: vm.blad,
          onPonow: vm.zaladuj,
          tresc: (_) {
            final d = vm.dane!;
            return Card(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.verified_user_outlined, color: Kolory.primary, semanticLabel: 'Zalogowano'),
                        const SizedBox(width: 8),
                        Expanded(child: Text('Zalogowano przez mObywatel (symulacja)', style: t.bodyMedium)),
                      ],
                    ),
                    const SizedBox(height: 16),
                    _Wiersz(etykieta: 'Imię', wartosc: d.imie),
                    _Wiersz(etykieta: 'Nazwisko', wartosc: d.nazwisko),
                    _Wiersz(etykieta: 'Konto testowe', wartosc: d.login),
                    const SizedBox(height: 24),
                    Align(
                      alignment: Alignment.centerLeft,
                      child: OutlinedButton.icon(
                        onPressed: vm.wyloguj,
                        icon: const Icon(Icons.logout),
                        label: const Text('Wyloguj'),
                      ),
                    ),
                  ],
                ),
              ),
            );
          },
        ),
      ],
    );
  }
}

class _Wiersz extends StatelessWidget {
  const _Wiersz({required this.etykieta, required this.wartosc});
  final String etykieta;
  final String wartosc;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(width: 140, child: Text(etykieta, style: t.bodyMedium)),
          Expanded(child: Text(wartosc, style: t.titleMedium)),
        ],
      ),
    );
  }
}
