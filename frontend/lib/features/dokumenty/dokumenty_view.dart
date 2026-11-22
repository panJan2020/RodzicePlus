import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../core/theme.dart';
import '../../data/models/modele.dart';
import '../../data/models/plik_do_wgrania.dart';
import '../../shared/widgets/przycisk_wstecz.dart';
import '../../shared/widgets/stan_ladowania.dart';
import '../../shared/widgets/tresc_strony.dart';
import '../../shared/widgets/znacznik.dart';
import '../moje_swiadczenia/moje_swiadczenia_view.dart' show wygladStatusu;
import 'dokumenty_viewmodel.dart';

/// „Dokumenty”: wgranie skanów PDF, rozpoznane dokumenty, odczytane dane i porównanie z decyzją ZUS.
class DokumentyView extends StatelessWidget {
  const DokumentyView({super.key});

  @override
  Widget build(BuildContext context) =>
      ChangeNotifierProvider(create: (c) => DokumentyViewModel(c.read()), child: const _Tresc());
}

String _rozmiar(int bajty) => bajty >= 1024 * 1024
    ? '${(bajty / (1024 * 1024)).toStringAsFixed(1).replaceAll('.', ',')} MB'
    : '${(bajty / 1024).ceil()} KB';

/// `[5, 6, 7, 8]` → „str. 5–8”, `[1, 3]` → „str. 1, 3”.
String _strony(List<int> s) {
  if (s.isEmpty) return '';
  if (s.length == 1) return 'str. ${s.first}';
  final ciagle = [for (var i = 1; i < s.length; i++) s[i] == s[i - 1] + 1].every((x) => x);
  return ciagle ? 'str. ${s.first}–${s.last}' : 'str. ${s.join(', ')}';
}

String _osoba(OsobaSkrot o) {
  final rola = switch (o.rola) {
    RolaOsoby.matka => 'Matka',
    RolaOsoby.ojciec => 'Ojciec',
    RolaOsoby.drugiRodzic => 'Drugi rodzic',
    RolaOsoby.dziecko => 'Dziecko',
  };
  final imie = o.imie;
  return (imie == null || imie.isEmpty || imie == rola) ? rola : '$rola ($imie)';
}

class _Tresc extends StatelessWidget {
  const _Tresc();

  Future<void> _wybierz(BuildContext context) async {
    final vm = context.read<DokumentyViewModel>();
    try {
      final wybrane = await FilePicker.pickFiles(type: FileType.custom, allowedExtensions: ['pdf']);
      final pliki = [for (final f in wybrane) PlikDoWgrania(nazwa: f.name, bajty: await f.readAsBytes())];
      if (pliki.isNotEmpty) vm.dodajPliki(pliki);
    } catch (_) {
      // Użytkownik zamknął okno albo przeglądarka odmówiła dostępu – nic się nie dzieje.
    }
  }

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<DokumentyViewModel>();
    final t = Theme.of(context).textTheme;
    return TrescStrony(
      children: [
        const PrzyciskWstecz(),
        Semantics(header: true, child: Text('Dokumenty', style: t.headlineMedium)),
        const SizedBox(height: 8),
        Text('Wgraj skany dokumentów (PDF) – rozpoznamy je, odczytamy z nich dane i sprawdzimy, jakie świadczenia Ci '
            'przysługują.', style: t.bodyLarge),
        const SizedBox(height: 24),
        _Wgrywanie(onWybierz: () => _wybierz(context)),
        const SizedBox(height: 24),
        StanLadowania(
          laduje: vm.laduje && !vm.wgrywa,
          blad: vm.blad,
          onPonow: vm.zaladuj,
          tresc: (_) => vm.maWynik ? const _Wyniki() : const _Pusto(),
        ),
      ],
    );
  }
}

class _Pusto extends StatelessWidget {
  const _Pusto();

  @override
  Widget build(BuildContext context) => Card(
        margin: EdgeInsets.zero,
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(children: [
            const Icon(Icons.description_outlined, size: 40, color: Kolory.tekstDrugorzedny,
                semanticLabel: 'Brak dokumentów'),
            const SizedBox(height: 12),
            Text('Nie wgrano jeszcze żadnych dokumentów.', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 4),
            Text('Wybierz plik PDF powyżej – na przykład zaświadczenie Z-3 albo wniosek ZAS-53.',
                textAlign: TextAlign.center, style: Theme.of(context).textTheme.bodyLarge),
          ]),
        ),
      );
}

class _Wgrywanie extends StatelessWidget {
  const _Wgrywanie({required this.onWybierz});
  final VoidCallback onWybierz;

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<DokumentyViewModel>();
    final t = Theme.of(context).textTheme;
    return Card(
      margin: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Semantics(header: true, child: Text('Wgraj dokumenty', style: t.titleLarge)),
          const SizedBox(height: 12),
          if (vm.wgrywa)
            const _Postep()
          else ...[
            Align(
              alignment: Alignment.centerLeft,
              child: OutlinedButton.icon(
                onPressed: onWybierz,
                icon: const Icon(Icons.upload_file),
                label: const Text('Wybierz pliki PDF'),
              ),
            ),
            for (final p in vm.wybrane) _WybranyPlik(plik: p),
            if (vm.uwagaOPlikach != null) ...[
              const SizedBox(height: 8),
              _Komunikat(tekst: vm.uwagaOPlikach!, ikona: Icons.info_outline),
            ],
            if (vm.bladWgrania != null) ...[
              const SizedBox(height: 8),
              _Komunikat(tekst: vm.bladWgrania!, ikona: Icons.error_outline, blad: true),
            ],
            if (vm.wybrane.isNotEmpty) ...[
              const SizedBox(height: 16),
              Align(
                alignment: Alignment.centerLeft,
                child: FilledButton.icon(
                  onPressed: vm.mozeWgrac ? vm.wgraj : null,
                  icon: Icon(vm.bladWgrania != null ? Icons.refresh : Icons.analytics_outlined),
                  label: Text(vm.bladWgrania != null ? 'Spróbuj ponownie' : 'Wgraj i przeanalizuj'),
                ),
              ),
            ],
          ],
        ]),
      ),
    );
  }
}

class _WybranyPlik extends StatelessWidget {
  const _WybranyPlik({required this.plik});
  final PlikDoWgrania plik;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(top: 8),
        child: Row(children: [
          const Icon(Icons.picture_as_pdf_outlined, color: Kolory.secondary, semanticLabel: 'Plik PDF'),
          const SizedBox(width: 8),
          Expanded(child: Text(plik.nazwa, overflow: TextOverflow.ellipsis)),
          const SizedBox(width: 8),
          Text(_rozmiar(plik.rozmiar), style: const TextStyle(color: Kolory.tekstDrugorzedny)),
          IconButton(
            tooltip: 'Usuń z listy ${plik.nazwa}',
            icon: const Icon(Icons.close),
            onPressed: () => context.read<DokumentyViewModel>().usunWybrany(plik),
          ),
        ]),
      );
}

class _Postep extends StatelessWidget {
  const _Postep();

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<DokumentyViewModel>();
    final t = Theme.of(context).textTheme;
    final z = vm.zadanie;
    return Semantics(
      liveRegion: true,
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Text(vm.komunikatEtapu, style: t.titleMedium),
        const SizedBox(height: 12),
        LinearProgressIndicator(
          value: (z == null || z.postep <= 0) ? null : z.postep.clamp(0, 1).toDouble(),
          minHeight: 8,
          semanticsLabel: 'Postęp analizy dokumentów',
        ),
        const SizedBox(height: 12),
        Text('Analiza nowych dokumentów może potrwać do 2 minut. Nie zamykaj tej strony.', style: t.bodyMedium),
      ]),
    );
  }
}

class _Komunikat extends StatelessWidget {
  const _Komunikat({required this.tekst, required this.ikona, this.blad = false});
  final String tekst;
  final IconData ikona;
  final bool blad;

  @override
  Widget build(BuildContext context) {
    final kolor = blad ? Kolory.blad : Kolory.ostrzezenie;
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: blad ? Kolory.bladTlo : Kolory.ostrzezenieTlo,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Icon(ikona, color: kolor, semanticLabel: blad ? 'Błąd' : 'Uwaga'),
        const SizedBox(width: 8),
        Expanded(child: Text(tekst)),
      ]),
    );
  }
}

// ---------------------------------------------------------------------------------------------

class _Wyniki extends StatelessWidget {
  const _Wyniki();

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<DokumentyViewModel>();
    final t = Theme.of(context).textTheme;
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Semantics(header: true, child: Text('Rozpoznane dokumenty', style: t.titleLarge)),
      const SizedBox(height: 12),
      if (vm.bladUsuwania != null) ...[
        _Komunikat(tekst: vm.bladUsuwania!, ikona: Icons.error_outline, blad: true),
        const SizedBox(height: 12),
      ],
      for (final d in vm.dokumenty) ...[_KartaDokumentu(dokument: d), const SizedBox(height: 12)],
      const SizedBox(height: 12),
      Semantics(header: true, child: Text('Odczytane dane', style: t.titleLarge)),
      const SizedBox(height: 4),
      Text('Sprawdź, czy odczyt się zgadza. Dane oznaczone jako „do sprawdzenia” odczytaliśmy niepewnie.',
          style: t.bodyMedium),
      const SizedBox(height: 12),
      if (vm.odczytane.isEmpty)
        Text('Z tych dokumentów nie odczytaliśmy jeszcze żadnych danych.', style: t.bodyLarge)
      else
        const _OdczytaneDane(),
      if (vm.porownanie != null) ...[
        const SizedBox(height: 24),
        Semantics(header: true, child: Text('Porównanie z decyzją ZUS', style: t.titleLarge)),
        const SizedBox(height: 12),
        _KartaPorownania(porownanie: vm.porownanie!),
      ],
      const SizedBox(height: 24),
      Align(
        alignment: Alignment.centerLeft,
        child: FilledButton.icon(
          onPressed: () => context.push('/swiadczenia'),
          icon: const Icon(Icons.arrow_forward),
          label: const Text('Zobacz moje świadczenia'),
        ),
      ),
    ]);
  }
}

class _KartaDokumentu extends StatelessWidget {
  const _KartaDokumentu({required this.dokument});
  final Dokument dokument;

  Future<void> _usun(BuildContext context) async {
    final vm = context.read<DokumentyViewModel>();
    final tak = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Usunąć dokument?'),
        content: Text('Usuniemy „${dokument.typOpis}” (${dokument.plik}) i dane z niego odczytane. '
            'Wyniki zostaną przeliczone.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Anuluj')),
          FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Usuń')),
        ],
      ),
    );
    if (tak == true) await vm.usun(dokument);
  }

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<DokumentyViewModel>();
    final t = Theme.of(context).textTheme;
    final d = dokument;
    final usuwa = vm.usuwanyId == d.id;
    final wariant = switch (d.wariant) {
      'pierwszorazowy' => 'pierwszorazowy',
      'w_kontynuacji' => 'w kontynuacji',
      _ => null,
    };
    return Card(
      margin: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 16, 8, 16),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(d.typOpis, style: t.titleMedium),
              const SizedBox(height: 4),
              Text([d.plik, if (d.strony.isNotEmpty) _strony(d.strony), ?wariant].join(' · '),
                  style: t.bodyMedium?.copyWith(color: Kolory.tekstDrugorzedny)),
              const SizedBox(height: 8),
              Wrap(spacing: 8, runSpacing: 8, children: [
                if (d.rola == 'decyzja_zus')
                  const Znacznik(kolor: Kolory.secondary, tlo: Kolory.warunkowoTlo, ikona: Icons.gavel,
                      napis: 'Decyzja ZUS – tylko do porównania'),
                if (d.archiwalny)
                  const Znacznik(kolor: Kolory.secondary, tlo: Kolory.warunkowoTlo, ikona: Icons.history,
                      napis: 'Formularz wycofany – nadal go czytamy'),
                if (d.rola == 'dane')
                  Znacznik(kolor: Kolory.primary, tlo: Kolory.primaryLight, ikona: Icons.check_circle,
                      napis: '${d.liczbaPol} odczytanych pól'),
                if (d.doSprawdzenia > 0)
                  Znacznik(kolor: Kolory.ostrzezenie, tlo: Kolory.ostrzezenieTlo, ikona: Icons.warning_amber,
                      napis: '${d.doSprawdzenia} do sprawdzenia'),
              ]),
              if (d.informacja.isNotEmpty) ...[
                const SizedBox(height: 8),
                for (final i in d.informacja) Text('• $i', style: t.bodyMedium),
              ],
            ]),
          ),
          usuwa
              ? const Padding(
                  padding: EdgeInsets.all(12),
                  child: SizedBox(
                      width: 24,
                      height: 24,
                      child: CircularProgressIndicator(strokeWidth: 3, semanticsLabel: 'Usuwanie dokumentu')),
                )
              : IconButton(
                  tooltip: 'Usuń dokument ${d.typOpis}',
                  icon: const Icon(Icons.delete_outline),
                  onPressed: vm.usuwanyId == null ? () => _usun(context) : null,
                ),
        ]),
      ),
    );
  }
}

class _OdczytaneDane extends StatelessWidget {
  const _OdczytaneDane();

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<DokumentyViewModel>();
    final t = Theme.of(context).textTheme;
    final poOsobach = <String, List<OdczytanePole>>{};
    final osoby = <String, OsobaSkrot>{};
    for (final p in vm.odczytane) {
      poOsobach.putIfAbsent(p.osoba.id, () => []).add(p);
      osoby[p.osoba.id] = p.osoba;
    }
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      for (final e in poOsobach.entries) ...[
        Semantics(header: true, child: Text(_osoba(osoby[e.key]!), style: t.titleMedium)),
        const SizedBox(height: 8),
        for (final p in e.value) ...[_Pole(pole: p), const SizedBox(height: 8)],
        const SizedBox(height: 8),
      ],
    ]);
  }
}

class _Pole extends StatelessWidget {
  const _Pole({required this.pole});
  final OdczytanePole pole;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final niepewne = pole.doSprawdzenia;
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: niepewne ? Kolory.ostrzezenieTlo : Kolory.powierzchnia,
        border: Border.all(color: niepewne ? Kolory.ostrzezenie : Kolory.ramka),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(pole.pytanie.tresc, style: t.bodyMedium?.copyWith(color: Kolory.tekstDrugorzedny)),
        const SizedBox(height: 4),
        Text(pole.opis.isEmpty ? '—' : pole.opis, style: t.bodyLarge?.copyWith(fontWeight: FontWeight.w600)),
        const SizedBox(height: 4),
        Text('Skąd to wiemy: ${pole.wartosc.zrodloOpis}', style: t.bodyMedium),
        if (niepewne) ...[
          const SizedBox(height: 8),
          const Znacznik(kolor: Kolory.ostrzezenie, tlo: Kolory.ostrzezenieTlo, ikona: Icons.warning_amber,
              napis: 'Do sprawdzenia – niepewny odczyt'),
        ],
      ]),
    );
  }
}

class _KartaPorownania extends StatelessWidget {
  const _KartaPorownania({required this.porownanie});
  final Porownanie porownanie;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final p = porownanie;
    final (kolor, tlo, ikona, napis, zdanie) = switch (p.zgodnosc) {
      Zgodnosc.zgodne => (Kolory.primary, Kolory.primaryLight, Icons.check_circle, 'Zgodne',
          'Nasz wynik zgadza się z decyzją ZUS.'),
      Zgodnosc.rozne => (Kolory.blad, Kolory.bladTlo, Icons.cancel, 'Niezgodne',
          'Nasz wynik różni się od decyzji ZUS – sprawdź odczytane dane.'),
      Zgodnosc.nieDoPorownania => (Kolory.ostrzezenie, Kolory.ostrzezenieTlo, Icons.help, 'Nie do porównania',
          'Nie możemy jeszcze porównać wyniku z decyzją ZUS – brakuje danych albo wynik jest warunkowy.'),
    };
    final wynik = p.wynikAplikacji;
    return Card(
      margin: EdgeInsets.zero,
      clipBehavior: Clip.antiAlias,
      child: Container(
        decoration: BoxDecoration(border: Border(left: BorderSide(color: kolor, width: 4))),
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Znacznik(kolor: kolor, tlo: tlo, ikona: ikona, napis: napis),
          const SizedBox(height: 12),
          Text(zdanie, style: t.bodyLarge?.copyWith(fontWeight: FontWeight.w600)),
          const SizedBox(height: 12),
          Text('Decyzja ZUS: ${p.decyzjaZus.tekst}', style: t.bodyMedium),
          if (wynik != null) ...[
            const SizedBox(height: 4),
            Text('Wynik aplikacji: ${wygladStatusu(wynik.status).$4}', style: t.bodyMedium),
          ],
          for (final u in p.uwagi) ...[const SizedBox(height: 4), Text('• $u', style: t.bodyMedium)],
        ]),
      ),
    );
  }
}
