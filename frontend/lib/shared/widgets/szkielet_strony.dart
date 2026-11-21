import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/config.dart';
import '../../core/responsive.dart';
import '../../core/session.dart';
import '../../core/theme.dart';

/// Wspólny szkielet: nagłówek + menu (dolne na telefonie, boczne na tablecie/komputerze).
/// Treść ekranu przychodzi jako [child] z routera.
class SzkieletStrony extends StatelessWidget {
  const SzkieletStrony({super.key, required this.sciezka, required this.child});

  final String sciezka;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final uklad = Responsive.uklad(context);
    final wybrany = indeksMenu(sciezka);
    void idz(int i) => context.go(pozycjeMenu[i].sciezka);

    if (uklad == Uklad.telefon) {
      return Scaffold(
        appBar: _Naglowek(kompaktowy: true),
        body: child,
        bottomNavigationBar: NavigationBar(
          selectedIndex: wybrany,
          onDestinationSelected: idz,
          destinations: [
            for (final p in pozycjeMenu)
              NavigationDestination(icon: Icon(p.ikona), selectedIcon: Icon(p.ikonaAktywna), label: p.etykieta),
          ],
        ),
      );
    }

    return Scaffold(
      appBar: _Naglowek(kompaktowy: false),
      body: Row(
        children: [
          NavigationRail(
            extended: uklad == Uklad.komputer,
            minExtendedWidth: 220,
            selectedIndex: wybrany,
            onDestinationSelected: idz,
            labelType: uklad == Uklad.komputer ? NavigationRailLabelType.none : NavigationRailLabelType.all,
            destinations: [
              for (final p in pozycjeMenu)
                NavigationRailDestination(
                  icon: Icon(p.ikona),
                  selectedIcon: Icon(p.ikonaAktywna),
                  label: Text(p.etykieta),
                ),
            ],
          ),
          const VerticalDivider(width: 1),
          Expanded(child: child),
        ],
      ),
    );
  }
}

/// Nagłówek: nazwa aplikacji po lewej, po prawej „Zaloguj (mObywatel)” albo imię użytkownika.
class _Naglowek extends StatelessWidget implements PreferredSizeWidget {
  const _Naglowek({required this.kompaktowy});

  final bool kompaktowy;

  @override
  Size get preferredSize => const Size.fromHeight(kToolbarHeight + 3);

  @override
  Widget build(BuildContext context) {
    final sesja = context.watch<SesjaAplikacji>();
    return AppBar(
      titleSpacing: 16,
      title: Semantics(
        header: true,
        child: InkWell(
          onTap: () => context.go('/'),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.family_restroom, color: Kolory.primary, semanticLabel: 'Strona główna'),
              const SizedBox(width: 8),
              Flexible(child: Text(Config.nazwaAplikacji, overflow: TextOverflow.ellipsis)),
            ],
          ),
        ),
      ),
      actions: [
        if (sesja.zalogowany)
          _MenuUzytkownika(imie: sesja.dane!.imie, kompaktowy: kompaktowy)
        else
          Padding(
            padding: const EdgeInsets.only(right: 12),
            child: FilledButton.icon(
              onPressed: () => context.go('/logowanie'),
              icon: const Icon(Icons.login),
              label: Text(kompaktowy ? 'Zaloguj' : 'Zaloguj (mObywatel)'),
            ),
          ),
      ],
      bottom: const PreferredSize(
        preferredSize: Size.fromHeight(3),
        child: ColoredBox(color: Kolory.primary, child: SizedBox(height: 3, width: double.infinity)),
      ),
    );
  }
}

class _MenuUzytkownika extends StatelessWidget {
  const _MenuUzytkownika({required this.imie, required this.kompaktowy});

  final String imie;
  final bool kompaktowy;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: PopupMenuButton<String>(
        tooltip: 'Menu konta',
        onSelected: (w) {
          if (w == 'konto') context.go('/konto');
          if (w == 'wyloguj') context.read<SesjaAplikacji>().wyczysc();
        },
        itemBuilder: (_) => const [
          PopupMenuItem(value: 'konto', child: ListTile(leading: Icon(Icons.person_outline), title: Text('Moje konto'))),
          PopupMenuItem(value: 'wyloguj', child: ListTile(leading: Icon(Icons.logout), title: Text('Wyloguj'))),
        ],
        child: ConstrainedBox(
          constraints: const BoxConstraints(minHeight: 48),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.account_circle, color: Kolory.primary, semanticLabel: 'Zalogowano'),
              if (!kompaktowy) ...[
                const SizedBox(width: 8),
                Text(imie, style: const TextStyle(fontWeight: FontWeight.w600, color: Kolory.secondary)),
              ],
              const Icon(Icons.arrow_drop_down, color: Kolory.secondary),
            ],
          ),
        ),
      ),
    );
  }
}
