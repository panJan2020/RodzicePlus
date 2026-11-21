import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/responsive.dart';
import '../../core/theme.dart';
import '../../data/models/modele.dart';
import '../../shared/widgets/stan_ladowania.dart';
import '../../shared/widgets/tresc_strony.dart';
import 'logowanie_viewmodel.dart';

/// Symulowane logowanie przez mObywatela (FR-01): wybór fikcyjnego konta testowego.
class LogowanieView extends StatelessWidget {
  const LogowanieView({super.key});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (c) => LogowanieViewModel(c.read()),
      child: const _Tresc(),
    );
  }
}

class _Tresc extends StatelessWidget {
  const _Tresc();

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<LogowanieViewModel>();
    final t = Theme.of(context).textTheme;

    return TrescStrony(
      maxSzerokosc: Responsive.maxFormularz,
      children: [
        Semantics(header: true, child: Text('Logowanie przez mObywatel', style: t.headlineMedium)),
        const SizedBox(height: 8),
        Text(
          'Po zalogowaniu pobierzemy z ZUS dane o Twoim ubezpieczeniu, '
          'żeby nie pytać Cię o rzeczy, które już wiemy.',
          style: t.bodyLarge,
        ),
        const SizedBox(height: 16),
        const _InformacjaOSymulacji(),
        const SizedBox(height: 24),
        Semantics(header: true, child: Text('Wybierz konto testowe', style: t.titleLarge)),
        const SizedBox(height: 12),
        if (vm.bladLogowania != null) ...[
          _Komunikat(tekst: vm.bladLogowania!),
          const SizedBox(height: 12),
        ],
        StanLadowania(
          laduje: vm.laduje,
          blad: vm.blad,
          onPonow: vm.zaladuj,
          tresc: (_) => Column(
            children: [
              for (final k in vm.konta) ...[
                _KartaKonta(
                  konto: k,
                  logujeSie: vm.logujeSie == k.login,
                  zablokowana: vm.logujeSie != null,
                  onWybierz: () => _zaloguj(context, vm, k),
                ),
                const SizedBox(height: 12),
              ],
            ],
          ),
        ),
      ],
    );
  }

  Future<void> _zaloguj(BuildContext context, LogowanieViewModel vm, KontoTestowe k) async {
    final messenger = ScaffoldMessenger.of(context);
    final sesja = await vm.zaloguj(k.login);
    if (sesja != null) {
      messenger.showSnackBar(SnackBar(content: Text('Zalogowano jako ${sesja.imieINazwisko}.')));
    }
  }
}

class _InformacjaOSymulacji extends StatelessWidget {
  const _InformacjaOSymulacji();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Kolory.ostrzezenieTlo,
        borderRadius: BorderRadius.circular(6),
        border: const Border(left: BorderSide(color: Kolory.ostrzezenie, width: 4)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.info_outline, color: Kolory.ostrzezenie, semanticLabel: 'Informacja'),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              'To symulacja logowania. Nie łączymy się z prawdziwym mObywatelem '
              'i nie podajesz żadnych swoich danych. Konta testowe są fikcyjne.',
              style: Theme.of(context).textTheme.bodyLarge,
            ),
          ),
        ],
      ),
    );
  }
}

class _Komunikat extends StatelessWidget {
  const _Komunikat({required this.tekst});
  final String tekst;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      liveRegion: true,
      child: Row(
        children: [
          const Icon(Icons.error_outline, color: Kolory.blad, semanticLabel: 'Błąd'),
          const SizedBox(width: 8),
          Expanded(child: Text(tekst, style: const TextStyle(color: Kolory.blad, fontSize: 16))),
        ],
      ),
    );
  }
}

class _KartaKonta extends StatelessWidget {
  const _KartaKonta({
    required this.konto,
    required this.logujeSie,
    required this.zablokowana,
    required this.onWybierz,
  });

  final KontoTestowe konto;
  final bool logujeSie;
  final bool zablokowana;
  final VoidCallback onWybierz;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return Semantics(
      button: true,
      label: 'Zaloguj jako ${konto.imieINazwisko}. ${konto.opis}',
      excludeSemantics: true,
      child: Card(
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: zablokowana ? null : onWybierz,
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                CircleAvatar(
                  radius: 24,
                  backgroundColor: Kolory.primaryLight,
                  foregroundColor: Kolory.primaryDark,
                  child: Text(konto.imie.characters.first, style: const TextStyle(fontWeight: FontWeight.w700)),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(konto.imieINazwisko, style: t.titleMedium),
                      if (konto.opis.isNotEmpty) ...[
                        const SizedBox(height: 4),
                        Text(konto.opis, style: t.bodyMedium),
                      ],
                    ],
                  ),
                ),
                const SizedBox(width: 12),
                SizedBox.square(
                  dimension: 24,
                  child: logujeSie
                      ? const CircularProgressIndicator(strokeWidth: 2.5)
                      : const Icon(Icons.chevron_right, color: Kolory.primary),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
