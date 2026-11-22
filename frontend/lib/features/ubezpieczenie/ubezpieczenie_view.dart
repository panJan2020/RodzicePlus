import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/responsive.dart';
import '../../core/theme.dart';
import '../../data/models/modele.dart';
import '../../shared/formatowanie.dart';
import '../../shared/widgets/stan_ladowania.dart';
import '../../shared/widgets/tresc_strony.dart';
import 'ubezpieczenie_viewmodel.dart';

/// „Moje ubezpieczenie” – stan ubezpieczenia z danych sprawy (symulowane konto w ZUS, docs/opis_aplikacji.md, rozdz. 9).
class UbezpieczenieView extends StatelessWidget {
  const UbezpieczenieView({super.key});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (c) => UbezpieczenieViewModel(c.read()),
      child: const _Tresc(),
    );
  }
}

class _Tresc extends StatelessWidget {
  const _Tresc();

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<UbezpieczenieViewModel>();
    final t = Theme.of(context).textTheme;

    return TrescStrony(
      children: [
        Semantics(header: true, child: Text('Twoje ubezpieczenie w ZUS', style: t.headlineMedium)),
        const SizedBox(height: 8),
        Text(
          'Sprawdziliśmy w ZUS, czy podlegasz ubezpieczeniu chorobowemu. '
          'Od tego zależy prawo do zasiłku macierzyńskiego i chorobowego.',
          style: t.bodyLarge,
        ),
        const SizedBox(height: 24),
        StanLadowania(
          laduje: vm.laduje,
          blad: vm.blad,
          onPonow: vm.zaladuj,
          tresc: (_) => _Wynik(dane: vm.dane!),
        ),
      ],
    );
  }
}

class _Wynik extends StatelessWidget {
  const _Wynik({required this.dane});
  final DaneUbezpieczenia dane;

  @override
  Widget build(BuildContext context) {
    final podsumowanie = Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _Status(dane: dane),
        const SizedBox(height: 16),
        const _ZapiszWSprawie(),
      ],
    );
    final okresy = _ListaOkresow(okresy: dane.okresy);

    if (Responsive.uklad(context) == Uklad.komputer) {
      return Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(child: podsumowanie),
          const SizedBox(width: 24),
          Expanded(child: okresy),
        ],
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [podsumowanie, const SizedBox(height: 32), okresy],
    );
  }
}

/// Wyraźny wynik: kolor + ikona + tekst (status nigdy tylko kolorem).
class _Status extends StatelessWidget {
  const _Status({required this.dane});
  final DaneUbezpieczenia dane;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final ok = dane.ubezpieczonyChorobowo;
    final kolor = ok ? Kolory.primary : Kolory.ostrzezenie;
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: ok ? Kolory.primaryLight : Kolory.ostrzezenieTlo,
        borderRadius: BorderRadius.circular(6),
        border: Border(left: BorderSide(color: kolor, width: 4)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(
                ok ? Icons.verified_user : Icons.warning_amber_rounded,
                color: kolor,
                size: 28,
                semanticLabel: ok ? 'Ubezpieczony' : 'Brak ubezpieczenia',
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Semantics(
                  liveRegion: true,
                  child: Text(dane.podsumowanie, style: t.titleLarge?.copyWith(color: Kolory.tekst)),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          for (final w in dane.wyjasnienia)
            Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Padding(
                    padding: EdgeInsets.only(top: 9, right: 10, left: 4),
                    child: Icon(Icons.circle, size: 6, color: Kolory.tekstDrugorzedny),
                  ),
                  Expanded(child: Text(w, style: t.bodyLarge)),
                ],
              ),
            ),
          const SizedBox(height: 8),
          Text(
            'Źródło: konto ubezpieczonego w ZUS (symulacja), stan na ${formatujDate(dane.stanNa)}.',
            style: t.bodyMedium,
          ),
        ],
      ),
    );
  }
}

class _ZapiszWSprawie extends StatelessWidget {
  const _ZapiszWSprawie();

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<UbezpieczenieViewModel>();
    final t = Theme.of(context).textTheme;
    final pobrano = vm.pobrano;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Semantics(
              liveRegion: true,
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(Icons.check_circle, color: Kolory.primary, semanticLabel: 'Zapisano'),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Dane z ZUS są zapisane w Twojej sprawie – nie zapytamy Cię o nie drugi raz.'
                      '${pobrano != null && pobrano.noweKonflikty > 0 ? ' Część z nich różni się od Twoich '
                          'wcześniejszych odpowiedzi – obie wersje znajdziesz w „Moich danych”.' : ''}',
                      style: t.bodyLarge,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            OutlinedButton.icon(
              onPressed: vm.pobiera ? null : vm.pobierzPonownie,
              icon: vm.pobiera
                  ? const SizedBox.square(dimension: 18, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Icon(Icons.refresh),
              label: const Text('Pobierz ponownie z ZUS'),
            ),
            if (vm.bladPobrania != null) ...[
              const SizedBox(height: 12),
              Text(vm.bladPobrania!, style: const TextStyle(color: Kolory.blad, fontSize: 16)),
            ],
          ],
        ),
      ),
    );
  }
}

class _ListaOkresow extends StatelessWidget {
  const _ListaOkresow({required this.okresy});
  final List<OkresUbezpieczenia> okresy;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Semantics(header: true, child: Text('Okresy ubezpieczenia', style: t.titleLarge)),
        const SizedBox(height: 12),
        if (okresy.isEmpty)
          Text('ZUS nie ma informacji o żadnym tytule ubezpieczenia.', style: t.bodyLarge),
        for (final o in okresy) ...[_KartaOkresu(okres: o), const SizedBox(height: 12)],
      ],
    );
  }
}

class _KartaOkresu extends StatelessWidget {
  const _KartaOkresu({required this.okres});
  final OkresUbezpieczenia okres;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final o = okres;
    final koniec = o.doDnia == null ? 'nadal' : formatujDate(o.doDnia!);
    final chorobowe = !o.chorobowe
        ? 'brak'
        : o.chorobowoDobrowolne
            ? 'dobrowolne'
            : 'obowiązkowe';

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(child: Text(o.tytulOpis, style: t.titleMedium)),
                _Etykieta(tekst: o.aktywny ? 'trwa' : 'zakończony', aktywna: o.aktywny),
              ],
            ),
            const SizedBox(height: 4),
            Text(o.platnik, style: t.bodyMedium),
            const SizedBox(height: 12),
            _Wiersz(ikona: Icons.date_range, tekst: '${formatujDate(o.odDnia)} – $koniec'),
            _Wiersz(
              ikona: o.chorobowe ? Icons.health_and_safety_outlined : Icons.remove_circle_outline,
              kolor: o.chorobowe ? Kolory.primary : Kolory.tekstDrugorzedny,
              tekst: 'Ubezpieczenie chorobowe: $chorobowe',
            ),
          ],
        ),
      ),
    );
  }
}

class _Etykieta extends StatelessWidget {
  const _Etykieta({required this.tekst, required this.aktywna});
  final String tekst;
  final bool aktywna;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: aktywna ? Kolory.primaryLight : Kolory.tlo,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: aktywna ? Kolory.primary : Kolory.ramka),
      ),
      child: Text(
        tekst,
        style: TextStyle(
          fontSize: 14,
          fontWeight: FontWeight.w600,
          color: aktywna ? Kolory.primaryDark : Kolory.tekstDrugorzedny,
        ),
      ),
    );
  }
}

class _Wiersz extends StatelessWidget {
  const _Wiersz({required this.ikona, required this.tekst, this.kolor = Kolory.tekstDrugorzedny});
  final IconData ikona;
  final String tekst;
  final Color kolor;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 4),
      child: Row(
        children: [
          Icon(ikona, size: 20, color: kolor),
          const SizedBox(width: 8),
          Expanded(child: Text(tekst, style: Theme.of(context).textTheme.bodyLarge)),
        ],
      ),
    );
  }
}
