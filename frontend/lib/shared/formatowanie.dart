/// Formatowanie do wyświetlania (bez logiki biznesowej).
library;

import '../data/models/modele.dart';

String _dwa(int n) => n.toString().padLeft(2, '0');

/// `10.07.2026`
String formatujDate(DateTime d) => '${_dwa(d.day)}.${_dwa(d.month)}.${d.year}';

/// `2026-07-10` → `10.07.2026` (bez zmian, gdy tekst nie jest datą).
String formatujDateIso(String iso) {
  final d = DateTime.tryParse(iso);
  return d == null ? iso : formatujDate(d);
}

/// Data do wysłania do API: `2026-07-10`.
String dataIso(DateTime d) => '${d.year}-${_dwa(d.month)}-${_dwa(d.day)}';

/// `1 234,56 zł` (spacja nierozdzielająca między tysiącami).
String formatujKwote(num kwota) {
  final grosze = (kwota * 100).round();
  final znak = grosze < 0 ? '-' : '';
  final abs = grosze.abs();
  final zl = (abs ~/ 100).toString();
  final buf = StringBuffer();
  for (var i = 0; i < zl.length; i++) {
    if (i > 0 && (zl.length - i) % 3 == 0) buf.write(' ');
    buf.write(zl[i]);
  }
  return '$znak$buf,${_dwa(abs % 100)} zł';
}

/// `0.815` → `81,5%`
String formatujProcent(double ulamek) {
  final p = ulamek * 100;
  final tekst = p == p.roundToDouble() ? p.round().toString() : p.toStringAsFixed(1).replaceAll('.', ',');
  return '$tekst%';
}

/// Liczba z przecinkiem dziesiętnym: `0.5` → `0,5`.
String formatujLiczbe(num n) => (n == n.roundToDouble() ? n.round().toString() : n.toString()).replaceAll('.', ',');

/// Odpowiedź na pytanie zamieniona na tekst dla człowieka (etykiety opcji, daty, kwoty).
String opisWartosci(PytanieDrzewa p) {
  final w = p.wartosc?.wartosc;
  if (w == null) return '';
  String etykieta(Object? v) => p.opcje.firstWhere((o) => o.wartosc == v, orElse: () => OpcjaPytania(wartosc: v, etykieta: '$v')).etykieta;
  switch (p.typ) {
    case TypPytania.wybor:
      return etykieta(w);
    case TypPytania.wielokrotny:
      return w is List ? w.map(etykieta).join(', ') : etykieta(w);
    case TypPytania.takNie:
      return w == true ? 'Tak' : 'Nie';
    case TypPytania.data:
      return formatujDateIso('$w');
    case TypPytania.kwota:
      return w is num ? formatujKwote(w) : '$w';
    case TypPytania.liczba:
      return w is num ? formatujLiczbe(w) : '$w';
    case TypPytania.okresy:
      if (w is! List || w.isEmpty) return 'Brak';
      return w.map((e) {
        if (e is! Map) return '$e';
        final kod = e['kod'] == null ? '' : ' (kod ${e['kod']})';
        return '${formatujDateIso('${e['od']}')} – ${formatujDateIso('${e['do']}')}$kod';
      }).join('\n');
  }
}

/// „Z ZUS”, „Z dokumentu ZAM, str. 7”, „Twoja odpowiedź”.
String opisZrodla(WartoscPola w) => switch (w.zrodlo) {
      ZrodloWartosci.uzytkownik => 'Twoja odpowiedź',
      ZrodloWartosci.zus => 'Z ZUS',
      ZrodloWartosci.wyliczone => 'Wyliczone',
      ZrodloWartosci.dokument => [
          'Z dokumentu',
          if (w.dokument != null) ' ${w.dokument}',
          if (w.strona != null) ', str. ${w.strona}',
        ].join(),
    };
