import 'dart:typed_data';

/// Plik wybrany przez użytkownika, gotowy do wysłania. Bajty zamiast ścieżki (`dart:io` nie działa w przeglądarce).
class PlikDoWgrania {
  const PlikDoWgrania({required this.nazwa, required this.bajty});

  final String nazwa;
  final Uint8List bajty;

  int get rozmiar => bajty.length;

  /// Po stronie klienta odsiewamy wszystko poza PDF-em (serwer i tak sprawdza to jeszcze raz).
  bool get toPdf => nazwa.toLowerCase().endsWith('.pdf');
}
