import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

/// „Wstecz” nad tytułem ekranu: wraca do poprzedniego ekranu, a gdy go nie ma (np. po odświeżeniu strony) –
/// na ekran `domyslna`.
class PrzyciskWstecz extends StatelessWidget {
  const PrzyciskWstecz({super.key, this.domyslna = '/'});

  final String domyslna;

  @override
  Widget build(BuildContext context) => Align(
        alignment: Alignment.centerLeft,
        child: Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: TextButton.icon(
            onPressed: () => context.canPop() ? context.pop() : context.go(domyslna),
            icon: const Icon(Icons.arrow_back),
            label: const Text('Wstecz'),
          ),
        ),
      );
}
