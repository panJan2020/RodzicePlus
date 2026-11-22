import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/responsive.dart';
import '../../core/theme.dart';
import '../../data/models/modele.dart';
import '../../shared/formatowanie.dart';
import '../../shared/widgets/przycisk_wstecz.dart';
import '../../shared/widgets/stan_ladowania.dart';
import '../../shared/widgets/tresc_strony.dart';
import '../../shared/widgets/znacznik.dart';
import 'moje_swiadczenia_viewmodel.dart';

/// „Moje świadczenia” – wynik każdej reguły z uzasadnieniem: status, okres, kwota, kto wypłaca, braki.
/// Komputer: karty po dwie obok siebie; telefon i tablet: jedna pod drugą.
class MojeSwiadczeniaView extends StatelessWidget {
  const MojeSwiadczeniaView({super.key});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (c) => MojeSwiadczeniaViewModel(c.read()),
      child: const _Tresc(),
    );
  }
}

class _Tresc extends StatelessWidget {
  const _Tresc();

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<MojeSwiadczeniaViewModel>();
    final t = Theme.of(context).textTheme;
    return TrescStrony(
      children: [
        const PrzyciskWstecz(domyslna: '/dokumenty'),
        Semantics(header: true, child: Text('Twoje świadczenia', style: t.headlineMedium)),
        const SizedBox(height: 8),
        Text('Sprawdzamy, czy przysługuje Ci zasiłek, za jaki okres i w jakiej wysokości. Korzystamy z Twoich '
            'dokumentów i danych z zakładki „Moje dane”.', style: t.bodyLarge),
        const SizedBox(height: 24),
        StanLadowania(
          laduje: vm.laduje,
          blad: vm.blad,
          onPonow: vm.zaladuj,
          tresc: (_) {
            if (vm.wyniki.isEmpty) return const _Pusto();
            final karty = [for (final w in vm.wyniki) KartaSwiadczenia(wynik: w)];
            if (Responsive.uklad(context) != Uklad.komputer) {
              return Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [for (final k in karty) ...[k, const SizedBox(height: 16)]],
              );
            }
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                for (var i = 0; i < karty.length; i += 2) ...[
                  IntrinsicHeight(
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Expanded(child: karty[i]),
                        const SizedBox(width: 16),
                        Expanded(child: i + 1 < karty.length ? karty[i + 1] : const SizedBox()),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),
                ],
              ],
            );
          },
        ),
      ],
    );
  }
}

class _Pusto extends StatelessWidget {
  const _Pusto();

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return Card(
      margin: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(children: [
          const Icon(Icons.inbox_outlined, size: 40, color: Kolory.tekstDrugorzedny, semanticLabel: 'Brak wyników'),
          const SizedBox(height: 12),
          Text('Nie mamy jeszcze wyników.', style: t.titleMedium),
          const SizedBox(height: 4),
          Text('Wgraj dokumenty albo uzupełnij „Moje dane”, a ocenimy, jakie świadczenia Ci przysługują.',
              textAlign: TextAlign.center, style: t.bodyLarge),
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: () => context.go('/dokumenty'),
            icon: const Icon(Icons.upload_file),
            label: const Text('Wgraj dokumenty'),
          ),
        ]),
      ),
    );
  }
}

/// Status zawsze z ikoną i tekstem, nie tylko kolorem.
(Color, Color, IconData, String) wygladStatusu(StatusSwiadczenia s) => switch (s) {
      StatusSwiadczenia.przysluguje => (Kolory.primary, Kolory.primaryLight, Icons.check_circle, 'Przysługuje'),
      StatusSwiadczenia.warunkowo => (Kolory.secondary, Kolory.warunkowoTlo, Icons.schedule, 'Przysługuje warunkowo'),
      StatusSwiadczenia.niePrzysluguje => (Kolory.blad, Kolory.bladTlo, Icons.cancel, 'Nie przysługuje'),
      StatusSwiadczenia.brakDanych => (Kolory.ostrzezenie, Kolory.ostrzezenieTlo, Icons.help, 'Brakuje danych'),
    };

/// Karta jednego świadczenia: status (kolor + słowo + ikona), podsumowanie, okres i kwota, uzasadnienie
/// (rozwijane), uwagi, braki i kroki oraz „Skąd te dane?”.
class KartaSwiadczenia extends StatelessWidget {
  const KartaSwiadczenia({super.key, required this.wynik});
  final WynikSwiadczenia wynik;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final w = wynik;
    final (kolor, tlo, ikona, napis) = wygladStatusu(w.status);
    final powodyIUzasadnienie = [
      ...w.uzasadnienie,
      for (final p in w.powody) p.komunikat,
    ];
    final maOkresLubKwote = w.kwota != null || w.okres != null || w.okresWynagrodzenia != null;
    final pokazBlokKwoty = maOkresLubKwote ||
        w.status == StatusSwiadczenia.przysluguje ||
        w.status == StatusSwiadczenia.warunkowo;
    final maKroki = w.brakujacePola.isNotEmpty || w.polaDoPotwierdzenia.isNotEmpty || w.coZrobic.isNotEmpty;

    return Card(
      margin: EdgeInsets.zero,
      clipBehavior: Clip.antiAlias,
      child: Container(
        decoration: BoxDecoration(border: Border(left: BorderSide(color: kolor, width: 4))),
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Semantics(header: true, child: Text(w.nazwa, style: t.titleLarge)),
            const SizedBox(height: 8),
            Wrap(spacing: 8, runSpacing: 8, children: [
              Znacznik(kolor: kolor, tlo: tlo, ikona: ikona, napis: napis),
              if (w.orientacyjny)
                const Znacznik(kolor: Kolory.ostrzezenie, tlo: Kolory.ostrzezenieTlo, ikona: Icons.info_outline,
                    napis: 'Wynik orientacyjny'),
            ]),
            const SizedBox(height: 12),
            Text(w.podsumowanie, style: t.bodyLarge?.copyWith(fontWeight: FontWeight.w600)),
            if (pokazBlokKwoty) ...[const SizedBox(height: 12), _OkresIKwota(wynik: w)],
            if (w.warunki.isNotEmpty) ...[
              const SizedBox(height: 12),
              Text('Warunek', style: t.titleMedium),
              const SizedBox(height: 4),
              for (final x in w.warunki) _Punkt(tekst: x.opis, ikona: Icons.schedule),
            ],
            if (powodyIUzasadnienie.isNotEmpty) ...[
              const SizedBox(height: 8),
              Theme(
                data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
                child: ExpansionTile(
                  tilePadding: EdgeInsets.zero,
                  childrenPadding: EdgeInsets.zero,
                  initiallyExpanded: w.status == StatusSwiadczenia.niePrzysluguje,
                  title: Text('Dlaczego tak?', style: t.titleMedium),
                  expandedCrossAxisAlignment: CrossAxisAlignment.start,
                  children: [for (final x in powodyIUzasadnienie) _Punkt(tekst: x)],
                ),
              ),
            ],
            if (w.uwagi.isNotEmpty) ...[
              const SizedBox(height: 4),
              for (final u in w.uwagi)
                _Punkt(tekst: u, ikona: Icons.info_outline, kolorIkony: Kolory.secondary, opis: 'Uwaga'),
            ],
            if (maKroki) ...[const SizedBox(height: 12), _CzegoBrakuje(wynik: w)],
            if (w.podstawaPrawna.isNotEmpty) ...[
              const SizedBox(height: 12),
              Text('(${w.podstawaPrawna.join('; ')})', style: t.bodyMedium),
            ],
            if (w.zrodlaDanych.isNotEmpty) ...[
              const SizedBox(height: 8),
              Align(
                alignment: Alignment.centerLeft,
                child: TextButton.icon(
                  onPressed: () => _pokazZrodla(context, w),
                  icon: const Icon(Icons.travel_explore),
                  label: const Text('Skąd te dane?'),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

/// „Skąd te dane?” – pola użyte w wyniku z dokumentem i stroną (albo innym źródłem).
void _pokazZrodla(BuildContext context, WynikSwiadczenia w) {
  showDialog<void>(
    context: context,
    builder: (c) => AlertDialog(
      title: const Text('Skąd te dane?'),
      content: SizedBox(
        width: Responsive.maxFormularz,
        child: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('Wynik „${w.nazwa}” opiera się na tych danych:', style: Theme.of(c).textTheme.bodyLarge),
            const SizedBox(height: 12),
            for (final z in w.zrodlaDanych)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(z.tresc, style: Theme.of(c).textTheme.titleMedium),
                  Text(z.zrodloOpis, style: Theme.of(c).textTheme.bodyLarge),
                  if (z.doSprawdzenia)
                    const Padding(
                      padding: EdgeInsets.only(top: 4),
                      child: Znacznik(kolor: Kolory.ostrzezenie, tlo: Kolory.ostrzezenieTlo,
                          ikona: Icons.warning_amber, napis: 'Do potwierdzenia'),
                    ),
                ]),
              ),
          ]),
        ),
      ),
      actions: [TextButton(onPressed: () => Navigator.pop(c), child: const Text('Zamknij'))],
    ),
  );
}

/// Punkt listy z ikoną.
class _Punkt extends StatelessWidget {
  const _Punkt({required this.tekst, this.ikona, this.kolorIkony = Kolory.tekstDrugorzedny, this.opis});
  final String tekst;
  final IconData? ikona;
  final Color kolorIkony;
  final String? opis;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Padding(
          padding: EdgeInsets.only(top: ikona == null ? 9 : 2, right: 10, left: ikona == null ? 4 : 0),
          child: Icon(ikona ?? Icons.circle, size: ikona == null ? 6 : 18, color: kolorIkony, semanticLabel: opis),
        ),
        Expanded(child: Text(tekst, style: t.bodyLarge)),
      ]),
    );
  }
}

/// Okres, kto wypłaca i kwota – wiersze „etykieta: wartość” (czytelne też na telefonie).
class _OkresIKwota extends StatelessWidget {
  const _OkresIKwota({required this.wynik});
  final WynikSwiadczenia wynik;

  /// Dlaczego nie ma kwoty: brakujące dane albo pierwsza uwaga reguły.
  String _powodBrakuKwoty() {
    final w = wynik;
    if (w.brakujacePola.isNotEmpty) return 'brakuje: ${w.brakujacePola.map((b) => b.tresc).join('; ')}';
    if (w.uwagi.isNotEmpty) return w.uwagi.first;
    return 'brakuje danych do wyliczenia';
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final w = wynik;
    final o = w.okres;
    final k = w.kwota;
    final wo = w.okresWynagrodzenia;
    final wiersze = <(String, String)>[
      if (o != null)
        ('Okres', '${formatujDate(o.odDnia)} – ${formatujDate(o.doDnia)}${o.dlugoscTekst == null ? '' : ' (${o.dlugoscTekst})'}'),
      if (wo != null)
        ('Wynagrodzenie od płatnika składek',
            'za okres ${formatujDate(wo.odDnia)} – ${formatujDate(wo.doDnia)}${wo.dlugoscTekst == null ? '' : ' (${wo.dlugoscTekst})'}'),
      if (w.ktoWyplaca != null)
        ('Kto wypłaca', w.ktoWyplaca == 'zus' ? 'ZUS' : 'pracodawca (płatnik składek)'),
      if (k != null) ...[
        ('Miesięcznie', '${formatujKwote(k.miesieczna)} brutto'),
        ('Za cały okres', '${formatujKwote(k.zaOkres)} brutto'),
        ('Stawka', k.stawka == null
            ? 'różna w częściach okresu (zależnie od kodu zwolnienia)'
            : '${formatujProcent(k.stawka!)} podstawy${k.stawkaDzienna == null ? '' : ' · ${formatujKwote(k.stawkaDzienna!)} dziennie'}'),
        ('Podstawa wymiaru', formatujKwote(k.podstawaWymiaru)),
      ] else ...[
        if (w.stawka != null) ('Stawka', '${formatujProcent(w.stawka!)} podstawy'),
        ('Kwota', 'nie można jeszcze obliczyć – ${_powodBrakuKwoty()}'),
      ],
    ];
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(color: Kolory.tlo, borderRadius: BorderRadius.circular(6)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          for (final (etykieta, wartosc) in wiersze)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 2),
              child: Wrap(spacing: 8, children: [
                Text('$etykieta:', style: t.bodyMedium),
                Text(wartosc, style: t.bodyLarge?.copyWith(fontWeight: FontWeight.w600)),
              ]),
            ),
          if (w.ktoWyplacaOpis != null || w.gdzieZlozyc != null) ...[
            const SizedBox(height: 8),
            for (final x in [?w.ktoWyplacaOpis, ?w.gdzieZlozyc]) Text(x, style: t.bodyMedium),
          ],
        ],
      ),
    );
  }
}

/// „Czego brakuje i co zrobić”: braki (z przejściem do „Moich danych”), pola do potwierdzenia i kroki.
class _CzegoBrakuje extends StatelessWidget {
  const _CzegoBrakuje({required this.wynik});
  final WynikSwiadczenia wynik;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final w = wynik;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(color: Kolory.ostrzezenieTlo, borderRadius: BorderRadius.circular(6)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Semantics(header: true, child: Text('Czego brakuje i co zrobić', style: t.titleMedium)),
          if (w.brakujacePola.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(w.status == StatusSwiadczenia.brakDanych
                ? 'Brakuje odpowiedzi: ${w.brakujacePola.length}'
                : 'Uzupełnij, aby wynik był pełny: ${w.brakujacePola.length}', style: t.bodyMedium),
            for (final b in w.brakujacePola) _Pytanie(pole: b),
          ],
          if (w.polaDoPotwierdzenia.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text('Do potwierdzenia (wynik opiera się na Twoich deklaracjach albo przybliżeniu):', style: t.bodyMedium),
            for (final b in w.polaDoPotwierdzenia) _Pytanie(pole: b),
          ],
          if (w.coZrobic.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text('Co możesz zrobić:', style: t.bodyMedium),
            for (final x in w.coZrobic) _Punkt(tekst: x, ikona: Icons.arrow_forward),
          ],
          if (w.brakujacePola.isNotEmpty) ...[
            const SizedBox(height: 8),
            FilledButton.icon(
              onPressed: () => context
                  .go(Uri(path: '/dane', queryParameters: {'pytanie': w.brakujacePola.first.pytanieId}).toString()),
              icon: const Icon(Icons.edit),
              label: const Text('Uzupełnij'),
            ),
          ],
        ],
      ),
    );
  }
}

class _Pytanie extends StatelessWidget {
  const _Pytanie({required this.pole});
  final BrakujacePole pole;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return Padding(
      padding: const EdgeInsets.only(top: 6),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(pole.tresc, style: t.bodyLarge),
        if (pole.gdzieZnalezc != null) Text('Znajdziesz to: ${pole.gdzieZnalezc}', style: t.bodyMedium),
      ]),
    );
  }
}
