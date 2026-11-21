import 'package:flutter/material.dart';

import '../../core/theme.dart';

/// Trzy stany ekranu z danymi: ładowanie / błąd z „Spróbuj ponownie” / treść.
class StanLadowania extends StatelessWidget {
  const StanLadowania({
    super.key,
    required this.laduje,
    required this.blad,
    required this.onPonow,
    required this.tresc,
  });

  final bool laduje;
  final String? blad;
  final VoidCallback onPonow;
  final WidgetBuilder tresc;

  @override
  Widget build(BuildContext context) {
    if (laduje) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 48),
        child: Center(child: CircularProgressIndicator(semanticsLabel: 'Ładowanie danych')),
      );
    }
    if (blad != null) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            children: [
              const Icon(Icons.error_outline, color: Kolory.blad, size: 40, semanticLabel: 'Błąd'),
              const SizedBox(height: 12),
              Text(blad!, textAlign: TextAlign.center, style: Theme.of(context).textTheme.bodyLarge),
              const SizedBox(height: 16),
              FilledButton.icon(
                onPressed: onPonow,
                icon: const Icon(Icons.refresh),
                label: const Text('Spróbuj ponownie'),
              ),
            ],
          ),
        ),
      );
    }
    return tresc(context);
  }
}
