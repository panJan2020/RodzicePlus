import 'package:flutter/material.dart';

/// Mała etykieta z ikoną i tekstem (status nigdy tylko kolorem).
class Znacznik extends StatelessWidget {
  const Znacznik({super.key, required this.kolor, required this.tlo, required this.ikona, required this.napis});

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
