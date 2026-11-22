import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/responsive.dart';
import '../../core/theme.dart';
import '../../data/models/modele.dart';
import '../../shared/formatowanie.dart';
import '../../shared/widgets/stan_ladowania.dart';
import '../../shared/widgets/tresc_strony.dart';
import 'moje_swiadczenia_viewmodel.dart';

/// „Świadczenia” – wynik każdej reguły z uzasadnieniem: status, okres, kwota, kto wypłaca, braki.
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
        Semantics(header: true, child: Text('Twoje świadczenia', style: t.headlineMedium)),
        const SizedBox(height: 8),
        Text('Sprawdzamy, czy przysługuje Ci zasiłek, za jaki okres i w jakiej wysokości. Korzystamy z Twoich '
            'danych z zakładki „Moje dane”.', style: t.bodyLarge),
        const SizedBox(height: 24),
        StanLadowania(
          laduje: vm.laduje,
          blad: vm.blad,
          onPonow: vm.zaladuj,
          tresc: (_) {
            if (vm.wyniki.isEmpty) {
              return Text('Nie mamy jeszcze wyników. Uzupełnij „Moje dane”.', style: t.bodyLarge);
            }
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

/// Status zawsze z ikoną i tekstem, nie tylko kolorem.
(Color, Color, IconData, String) wygladStatusu(StatusSwiadczenia s) => switch (s) {
      StatusSwiadczenia.przysluguje => (Kolory.primary, Kolory.primaryLight, Icons.check_circle, 'Przysługuje'),
      StatusSwiadczenia.warunkowo => (Kolory.secondary, Kolory.warunkowoTlo, Icons.schedule, 'Przysługuje warunkowo'),
      StatusSwiadczenia.niePrzysluguje => (Kolory.blad, Kolory.bladTlo, Icons.cancel, 'Nie przysługuje'),
      StatusSwiadczenia.brakDanych => (Kolory.ostrzezenie, Kolory.ostrzezenieTlo, Icons.help, 'Brakuje danych'),
    };

class KartaSwiadczenia extends StatelessWidget {
  const KartaSwiadczenia({super.key, required this.wynik});
  final WynikSwiadczenia wynik;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final w = wynik;
    final (kolor, tlo, ikona, napis) = wygladStatusu(w.status);

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
              _Znacznik(kolor: kolor, tlo: tlo, ikona: ikona, napis: napis),
              if (w.orientacyjny)
                const _Znacznik(kolor: Kolory.ostrzezenie, tlo: Kolory.ostrzezenieTlo, ikona: Icons.info_outline,
                    napis: 'Wynik orientacyjny'),
            ]),
            const SizedBox(height: 12),
            Text(w.podsumowanie, style: t.bodyLarge?.copyWith(fontWeight: FontWeight.w600)),
            if (w.kwota != null || w.okres != null) ...[const SizedBox(height: 12), _OkresIKwota(wynik: w)],
            if (w.warunki.isNotEmpty) ...[
              const SizedBox(height: 12),
              _Lista(tytul: 'Warunek', teksty: [for (final x in w.warunki) x.opis], ikona: Icons.schedule),
            ],
            if (w.uzasadnienie.isNotEmpty) ...[
              const SizedBox(height: 12),
              _Lista(tytul: 'Dlaczego', teksty: w.uzasadnienie),
            ],
            if (w.powody.isNotEmpty) ...[
              const SizedBox(height: 12),
              _Lista(tytul: 'Powód', teksty: [for (final p in w.powody) p.komunikat], ikona: Icons.cancel_outlined),
            ],
            if (w.ktoWyplacaOpis != null || w.gdzieZlozyc != null) ...[
              const SizedBox(height: 12),
              _Lista(tytul: 'Kto wypłaca i gdzie złożyć wniosek',
                  teksty: [?w.ktoWyplacaOpis, ?w.gdzieZlozyc], ikona: Icons.account_balance_outlined),
            ],
            if (w.coZrobic.isNotEmpty) ...[
              const SizedBox(height: 12),
              _Lista(tytul: 'Co możesz zrobić', teksty: w.coZrobic, ikona: Icons.arrow_forward),
            ],
            if (w.polaDoPotwierdzenia.isNotEmpty) ...[
              const SizedBox(height: 12),
              _Pytania(
                tytul: 'Do potwierdzenia (wynik opiera się na Twoich deklaracjach albo przybliżeniu)',
                pytania: w.polaDoPotwierdzenia,
                przycisk: null,
              ),
            ],
            if (w.brakujacePola.isNotEmpty) ...[
              const SizedBox(height: 12),
              _Pytania(
                tytul: w.status == StatusSwiadczenia.brakDanych
                    ? 'Brakuje odpowiedzi: ${w.brakujacePola.length}'
                    : 'Uzupełnij, aby wynik był pełny: ${w.brakujacePola.length}',
                pytania: w.brakujacePola,
                przycisk: 'Uzupełnij',
              ),
            ],
            if (w.uwagi.isNotEmpty) ...[
              const SizedBox(height: 12),
              for (final u in w.uwagi)
                Padding(
                  padding: const EdgeInsets.only(bottom: 4),
                  child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    const Padding(
                      padding: EdgeInsets.only(top: 2, right: 8),
                      child: Icon(Icons.info_outline, size: 18, color: Kolory.secondary, semanticLabel: 'Uwaga'),
                    ),
                    Expanded(child: Text(u, style: t.bodyMedium)),
                  ]),
                ),
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

class _Znacznik extends StatelessWidget {
  const _Znacznik({required this.kolor, required this.tlo, required this.ikona, required this.napis});
  final Color kolor;
  final Color tlo;
  final IconData ikona;
  final String napis;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(color: tlo, borderRadius: BorderRadius.circular(12)),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(ikona, color: kolor, size: 18, semanticLabel: napis),
          const SizedBox(width: 6),
          Flexible(child: Text(napis, style: TextStyle(color: kolor, fontWeight: FontWeight.w700, fontSize: 15))),
        ]),
      );
}

/// Okres i kwota – „tabela” jako wiersze etykieta: wartość (na telefonie też czytelne).
class _OkresIKwota extends StatelessWidget {
  const _OkresIKwota({required this.wynik});
  final WynikSwiadczenia wynik;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final o = wynik.okres;
    final k = wynik.kwota;
    final wiersze = <(String, String)>[
      if (o != null)
        ('Okres', '${formatujDate(o.odDnia)} – ${formatujDate(o.doDnia)}${o.dlugoscTekst == null ? '' : ' (${o.dlugoscTekst})'}'),
      if (k != null) ...[
        ('Miesięcznie', '${formatujKwote(k.miesieczna)} brutto'),
        ('Za cały okres', '${formatujKwote(k.zaOkres)} brutto'),
        ('Stawka', k.stawka == null
            ? 'różna w częściach okresu (zależnie od kodu zwolnienia)'
            : '${formatujProcent(k.stawka!)} podstawy${k.stawkaDzienna == null ? '' : ' · ${formatujKwote(k.stawkaDzienna!)} dziennie'}'),
        ('Podstawa wymiaru', formatujKwote(k.podstawaWymiaru)),
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
          if (k == null) Text('Kwoty jeszcze nie możemy policzyć – zobacz, czego brakuje.', style: t.bodyMedium),
        ],
      ),
    );
  }
}

class _Lista extends StatelessWidget {
  const _Lista({required this.tytul, required this.teksty, this.ikona = Icons.circle});
  final String tytul;
  final List<String> teksty;
  final IconData ikona;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final kropka = ikona == Icons.circle;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(tytul, style: t.titleMedium),
        const SizedBox(height: 4),
        for (final x in teksty)
          Padding(
            padding: const EdgeInsets.only(bottom: 4),
            child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Padding(
                padding: EdgeInsets.only(top: kropka ? 9 : 2, right: 10, left: kropka ? 4 : 0),
                child: Icon(ikona, size: kropka ? 6 : 18, color: Kolory.tekstDrugorzedny),
              ),
              Expanded(child: Text(x, style: t.bodyLarge)),
            ]),
          ),
      ],
    );
  }
}

/// Lista pytań (braki albo pola do potwierdzenia) + opcjonalnie „Uzupełnij” → `/dane?pytanie=<pierwsze ID>`.
class _Pytania extends StatelessWidget {
  const _Pytania({required this.tytul, required this.pytania, required this.przycisk});
  final String tytul;
  final List<BrakujacePole> pytania;
  final String? przycisk;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(color: Kolory.ostrzezenieTlo, borderRadius: BorderRadius.circular(6)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(tytul, style: t.titleMedium),
          const SizedBox(height: 6),
          for (final b in pytania)
            Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${b.tresc} (${b.pytanieId})', style: t.bodyLarge),
                if (b.gdzieZnalezc != null) Text('Znajdziesz to: ${b.gdzieZnalezc}', style: t.bodyMedium),
              ]),
            ),
          if (przycisk != null) ...[
            const SizedBox(height: 4),
            FilledButton.icon(
              onPressed: () =>
                  context.go(Uri(path: '/dane', queryParameters: {'pytanie': pytania.first.pytanieId}).toString()),
              icon: const Icon(Icons.edit),
              label: Text(przycisk!),
            ),
          ],
        ],
      ),
    );
  }
}
