import 'package:flutter/material.dart';

import '../../core/theme.dart';

/// Stopka w kolorze granatowym (CLAUDE.md, sekcja 7). Zawiera wymaganą informację o prototypie.
class Stopka extends StatelessWidget {
  const Stopka({super.key});

  // Adresy pokazujemy jako tekst do zaznaczenia. Klikalne linki wymagają pakietu
  // url_launcher – do decyzji zespołu (FR-27).
  static const _linki = [
    ('ZUS', 'www.zus.pl'),
    ('Urlop rodzicielski', 'www.gov.pl/web/rodzina'),
    ('Państwowa Inspekcja Pracy', 'www.pip.gov.pl'),
  ];

  @override
  Widget build(BuildContext context) {
    const jasny = TextStyle(color: Colors.white, fontSize: 14, height: 1.5);
    final przygaszony = jasny.copyWith(color: Colors.white.withValues(alpha: 0.85));
    return Semantics(
      container: true,
      label: 'Stopka',
      child: Container(
        width: double.infinity,
        color: Kolory.secondary,
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 28),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Wrap(
              spacing: 32,
              runSpacing: 12,
              children: [
                for (final (nazwa, adres) in _linki)
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(nazwa, style: jasny.copyWith(fontWeight: FontWeight.w600)),
                      SelectableText(adres, style: przygaszony),
                    ],
                  ),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Dostępność', style: jasny.copyWith(fontWeight: FontWeight.w600)),
                    Text('Deklaracja dostępności (szkic)', style: przygaszony),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 20),
            Divider(color: Colors.white.withValues(alpha: 0.3)),
            const SizedBox(height: 12),
            Text('Prototyp HackNation 2026 – nie jest oficjalnym serwisem ZUS.', style: jasny),
            Text('Wszystkie dane w tej wersji są fikcyjne.', style: przygaszony),
          ],
        ),
      ),
    );
  }
}
