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

/// `1 234,56 zł` (spacja nierozdzielająca między tysiącami). Przyjmuje tekst z API (`"1234.56"`) albo liczbę.
String formatujKwote(Object kwota) {
  final tekst = kwota is num ? kwota.toStringAsFixed(2) : '$kwota';
  final znak = tekst.startsWith('-') ? '-' : '';
  final czesci = tekst.replaceFirst('-', '').split('.');
  final zl = czesci[0];
  final gr = (czesci.length > 1 ? czesci[1] : '').padRight(2, '0').substring(0, 2);
  final buf = StringBuffer();
  for (var i = 0; i < zl.length; i++) {
    if (i > 0 && (zl.length - i) % 3 == 0) buf.write(' ');
    buf.write(zl[i]);
  }
  return '$znak$buf,$gr zł';
}

/// `"0.815"` → `81,5%`
String formatujProcent(String ulamek) {
  final p = double.parse(ulamek) * 100;
  final tekst = p == p.roundToDouble() ? p.round().toString() : p.toStringAsFixed(1).replaceAll('.', ',');
  return '$tekst%';
}

/// Liczba z przecinkiem dziesiętnym: `0.5` / `"0.50"` → `0,5`.
String formatujLiczbe(Object n) {
  final v = n is num ? n : num.tryParse('$n');
  if (v == null) return '$n';
  return (v == v.roundToDouble() ? v.round().toString() : v.toString()).replaceAll('.', ',');
}

/// Jedna odpowiedź (bez pól „na tytuł”) zamieniona na tekst dla człowieka.
String _opisJednej(PytanieDrzewa p, Object? w) {
  String etykieta(Object? v) =>
      p.opcje.firstWhere((o) => o.wartosc == v, orElse: () => OpcjaPytania(wartosc: v, etykieta: '$v')).etykieta;
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
      return w == null ? '' : formatujKwote(w);
    case TypPytania.liczba:
      return w == null ? '' : formatujLiczbe(w);
    case TypPytania.okresy:
      if (w is! List || w.isEmpty) return 'Brak';
      return w.map((e) {
        if (e is! Map) return '$e';
        final koniec = e['do'] == null ? 'nadal' : formatujDateIso('${e['do']}');
        final zakres = '${formatujDateIso('${e['od']}')} – $koniec';
        if (e['platnik'] != null) return '${e['platnik']}: $zakres';
        final kod = e['kod'] == null ? '' : ' (kod ${e['kod']})';
        return '$zakres$kod';
      }).join('\n');
    case TypPytania.miesiace:
      if (w is! List || w.isEmpty) return 'Brak';
      return w.map((e) {
        if (e is! Map) return '$e';
        final zmienne = num.tryParse('${e['skladniki_zmienne']}') ?? 0;
        final kwota = zmienne == 0
            ? formatujKwote(e['skladniki_stale'] ?? '0')
            : '${formatujKwote(e['skladniki_stale'] ?? '0')} + ${formatujKwote(e['skladniki_zmienne'])}';
        final dni = (e['dni_obowiazujace'] ?? 0) == 0 ? '' : ' (${e['dni_przepracowane']} z ${e['dni_obowiazujace']} dni)';
        return '${e['miesiac']}: $kwota$dni';
      }).join('\n');
    case TypPytania.zasilek:
      if (w is! Map) return 'Brak';
      return 'Do ${formatujDateIso('${w['data_do']}')}, podstawa ${formatujKwote(w['podstawa'] ?? '0')}';
  }
}

/// Aktywna odpowiedź na pytanie jako tekst (etykiety opcji, daty, kwoty; pola „na tytuł” – wiersz na tytuł).
String opisWartosci(PytanieDrzewa p) {
  final w = p.wartosc?.wartosc;
  if (w == null) return '';
  if (p.naTytul && w is Map) {
    String tytul(Object? k) =>
        p.klucze.firstWhere((o) => o.wartosc == k, orElse: () => OpcjaPytania(wartosc: k, etykieta: '$k')).etykieta;
    return w.entries.map((e) => '${tytul(e.key)}: ${_opisJednej(p, e.value)}').join('\n');
  }
  return _opisJednej(p, w);
}

/// „Skąd to wiemy”: gotowy opis źródła z backendu, np. „Konto w ZUS”, „Z-3, str. 7”, „Twoja odpowiedź”.
String opisZrodla(PytanieDrzewa p, WartoscPola w) =>
    p.wyborAktywnej == 'uzytkownik' && w.kanal != 'kreator' ? '${w.zrodloOpis} (wybrane przez Ciebie)' : w.zrodloOpis;
