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
      // Najwyżej 5 pozycji: główne + „Więcej” (pozostałe ekrany w arkuszu od dołu).
      final i = pozycjeTelefonu.indexOf(pozycjeMenu[wybrany]);
      return Scaffold(
        appBar: _Naglowek(kompaktowy: true),
        body: child,
        bottomNavigationBar: NavigationBar(
          selectedIndex: i >= 0 ? i : pozycjeTelefonu.length,
          onDestinationSelected: (n) =>
              n < pozycjeTelefonu.length ? context.go(pozycjeTelefonu[n].sciezka) : _pokazWiecej(context),
          destinations: [
            for (final p in pozycjeTelefonu)
              NavigationDestination(icon: Icon(p.ikona), selectedIcon: Icon(p.ikonaAktywna), label: p.etykieta),
            const NavigationDestination(icon: Icon(Icons.menu), selectedIcon: Icon(Icons.menu_open), label: 'Więcej'),
          ],
        ),
      );
    }

    return Scaffold(
      appBar: _Naglowek(kompaktowy: false),
      body: Row(
        children: [
          _MenuBoczne(rozwiniete: uklad == Uklad.komputer, wybrany: wybrany, onWybor: idz),
          const VerticalDivider(width: 1),
          Expanded(child: child),
        ],
      ),
    );
  }
}

/// Boczne menu tabletu/komputera. Cała pozycja (nie tylko ikona) podświetla się
/// po najechaniu i po wybraniu.
class _MenuBoczne extends StatelessWidget {
  const _MenuBoczne({required this.rozwiniete, required this.wybrany, required this.onWybor});

  final bool rozwiniete;
  final int wybrany;
  final ValueChanged<int> onWybor;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Kolory.powierzchnia,
      child: SizedBox(
        width: rozwiniete ? 240 : 96,
        child: ListView(
          padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 8),
          children: [
            for (var i = 0; i < pozycjeMenu.length; i++) _pozycja(i),
          ],
        ),
      ),
    );
  }

  Widget _pozycja(int i) {
    final p = pozycjeMenu[i];
    final aktywna = i == wybrany;
    final kolor = aktywna ? Kolory.primaryDark : Kolory.tekstDrugorzedny;
    final styl = TextStyle(color: kolor, fontSize: rozwiniete ? 15 : 12, fontWeight: aktywna ? FontWeight.w600 : null);
    final ikona = Icon(aktywna ? p.ikonaAktywna : p.ikona, color: kolor);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Semantics(
        button: true,
        selected: aktywna,
        label: p.etykieta,
        excludeSemantics: true,
        child: Material(
          color: aktywna ? Kolory.primaryLight : Colors.transparent,
          borderRadius: BorderRadius.circular(8),
          clipBehavior: Clip.antiAlias,
          child: InkWell(
            onTap: () => onWybor(i),
            hoverColor: Kolory.primaryLight,
            child: ConstrainedBox(
              constraints: const BoxConstraints(minHeight: 48),
              child: Padding(
                padding: EdgeInsets.symmetric(horizontal: 12, vertical: rozwiniete ? 10 : 8),
                child: rozwiniete
                    ? Row(children: [ikona, const SizedBox(width: 12), Expanded(child: Text(p.etykieta, style: styl))])
                    : Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [ikona, const SizedBox(height: 4), Text(p.etykieta, style: styl, textAlign: TextAlign.center)],
                      ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// „Więcej” na telefonie: ekrany, które nie mieszczą się w dolnym pasku.
void _pokazWiecej(BuildContext context) {
  showModalBottomSheet<void>(
    context: context,
    showDragHandle: true,
    builder: (arkusz) => SafeArea(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          for (final p in pozycjeWiecej)
            ListTile(
              minTileHeight: 56,
              leading: Icon(p.ikona),
              title: Text(p.etykieta),
              onTap: () {
                Navigator.of(arkusz).pop();
                context.go(p.sciezka);
              },
            ),
        ],
      ),
    ),
  );
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
              Image.asset('assets/logo.png', height: 40, semanticLabel: 'Rodzina Plus – strona główna'),
              if (!kompaktowy) ...[
                const SizedBox(width: 12),
                Flexible(child: Text(Config.nazwaAplikacji, overflow: TextOverflow.ellipsis)),
              ],
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
