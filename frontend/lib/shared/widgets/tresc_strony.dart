import 'package:flutter/material.dart';

import '../../core/responsive.dart';
import 'stopka.dart';

/// Przewijana treść ekranu: wyśrodkowana, z ograniczoną szerokością i stopką na dole.
/// Użyj `maxSzerokosc: Responsive.maxFormularz` dla formularzy i kreatora.
class TrescStrony extends StatelessWidget {
  const TrescStrony({super.key, required this.children, this.maxSzerokosc = Responsive.maxTresc});

  final List<Widget> children;
  final double maxSzerokosc;

  @override
  Widget build(BuildContext context) {
    final m = Responsive.margines(context);
    return LayoutBuilder(
      builder: (context, ograniczenia) => SingleChildScrollView(
        child: ConstrainedBox(
          constraints: BoxConstraints(minHeight: ograniczenia.maxHeight),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Center(
                child: ConstrainedBox(
                  constraints: BoxConstraints(maxWidth: maxSzerokosc),
                  child: Padding(
                    padding: EdgeInsets.fromLTRB(m, m, m, 48),
                    child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: children),
                  ),
                ),
              ),
              const Stopka(),
            ],
          ),
        ),
      ),
    );
  }
}
